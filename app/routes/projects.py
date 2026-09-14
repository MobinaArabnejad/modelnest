from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access import can_manage_project, can_view_project
from app.dependencies import get_current_user, get_db
from app.models import ModelGrant, ModelProject, ModelVersion, User
from app.schemas import (
    GrantRequest,
    GrantResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    VersionResponse,
)

router = APIRouter(prefix="/api/models", tags=["models"])
VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
ALLOWED_EXTENSIONS = {".json": "linear-json", ".onnx": "onnx", ".safetensors": "safetensors"}


def require_project(project_id: str, db: Session) -> ModelProject:
    project = db.get(ModelProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    return project


def validate_linear_json(path: Path) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        weights = payload["weights"]
        bias = payload.get("bias", 0.0)
        if not isinstance(weights, list) or not 1 <= len(weights) <= 4096:
            raise ValueError
        if not all(
            isinstance(item, int | float)
            and not isinstance(item, bool)
            and math.isfinite(float(item))
            for item in weights
        ):
            raise ValueError
        if (
            not isinstance(bias, int | float)
            or isinstance(bias, bool)
            or not math.isfinite(float(bias))
        ):
            raise ValueError
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="JSON models require numeric 'weights' and optional numeric 'bias'",
        ) from None


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelProject:
    project = ModelProject(owner_id=user.id, **payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ModelProject]:
    statement = (
        select(ModelProject)
        .outerjoin(ModelGrant)
        .where(
            or_(
                ModelProject.visibility == "public",
                ModelProject.owner_id == user.id,
                ModelGrant.user_id == user.id,
                user.role == "admin",
            )
        )
        .distinct()
        .order_by(ModelProject.created_at.desc())
    )
    return list(db.scalars(statement))


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelProject:
    project = require_project(project_id, db)
    if not can_view_project(project, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelProject:
    project = require_project(project_id, db)
    if not can_manage_project(project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner role required")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    project = require_project(project_id, db)
    if not can_manage_project(project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner role required")
    storage_dir: Path = db.info["settings"].storage_dir
    stored_files = [storage_dir / item.stored_filename for item in project.versions]
    db.delete(project)
    db.commit()
    for path in stored_files:
        path.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/share", response_model=GrantResponse)
def share_project(
    project_id: str,
    payload: GrantRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GrantResponse:
    project = require_project(project_id, db)
    if not can_manage_project(project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner role required")
    target = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if target.id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="owner already has access"
        )
    grant = db.scalar(
        select(ModelGrant).where(
            ModelGrant.project_id == project.id, ModelGrant.user_id == target.id
        )
    )
    if grant is None:
        grant = ModelGrant(project_id=project.id, user_id=target.id)
        db.add(grant)
    grant.can_infer = payload.can_infer
    db.commit()
    return GrantResponse(username=target.username, can_infer=grant.can_infer)


@router.delete("/{project_id}/share/{username}", status_code=status.HTTP_204_NO_CONTENT)
def remove_share(
    project_id: str,
    username: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    project = require_project(project_id, db)
    if not can_manage_project(project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner role required")
    target = db.scalar(select(User).where(User.username == username.strip().lower()))
    grant = None
    if target:
        grant = db.scalar(
            select(ModelGrant).where(
                ModelGrant.project_id == project.id, ModelGrant.user_id == target.id
            )
        )
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="share not found")
    db.delete(grant)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED
)
async def upload_version(
    project_id: str,
    version: str = Form(...),
    artifact: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ModelVersion:
    project = require_project(project_id, db)
    if not can_manage_project(project, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner role required")
    if not VERSION_PATTERN.fullmatch(version):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid version"
        )
    original_name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(artifact.filename or "").name)[:200]
    extension = Path(original_name).suffix.lower()
    if not original_name or extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="supported artifacts: .json, .onnx, .safetensors",
        )

    settings = db.info["settings"]
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = settings.storage_dir / stored_name
    digest = hashlib.sha256()
    size = 0
    try:
        with destination.open("xb") as output:
            while chunk := await artifact.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="artifact exceeds upload limit",
                    )
                digest.update(chunk)
                output.write(chunk)
        if extension == ".json":
            validate_linear_json(destination)
        record = ModelVersion(
            project_id=project.id,
            version=version,
            original_filename=original_name,
            stored_filename=stored_name,
            artifact_format=ALLOWED_EXTENSIONS[extension],
            sha256=digest.hexdigest(),
            size_bytes=size,
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="version already exists"
            ) from None
        db.refresh(record)
        return record
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await artifact.close()


@router.get("/{project_id}/versions", response_model=list[VersionResponse])
def list_versions(
    project_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ModelVersion]:
    project = require_project(project_id, db)
    if not can_view_project(project, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    return list(
        db.scalars(
            select(ModelVersion)
            .where(ModelVersion.project_id == project.id)
            .order_by(ModelVersion.created_at.desc())
        )
    )


@router.get("/{project_id}/versions/{version}/artifact")
def download_artifact(
    project_id: str,
    version: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    project = require_project(project_id, db)
    if not can_view_project(project, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    record = db.scalar(
        select(ModelVersion).where(
            ModelVersion.project_id == project.id, ModelVersion.version == version
        )
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
    path = db.info["settings"].storage_dir / record.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="artifact unavailable")
    return FileResponse(
        path, filename=record.original_filename, media_type="application/octet-stream"
    )
