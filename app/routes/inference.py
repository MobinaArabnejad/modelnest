from __future__ import annotations

import json
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import can_infer_project
from app.dependencies import get_db, get_inference_user
from app.models import ModelProject, ModelVersion, User
from app.schemas import InferenceRequest, InferenceResponse

router = APIRouter(prefix="/api/models", tags=["inference"])


@router.post("/{project_id}/versions/{version}/infer", response_model=InferenceResponse)
def infer(
    project_id: str,
    version: str,
    payload: InferenceRequest,
    user: User = Depends(get_inference_user),
    db: Session = Depends(get_db),
) -> InferenceResponse:
    project = db.get(ModelProject, project_id)
    if project is None or not can_infer_project(project, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="model not found")
    record = db.scalar(
        select(ModelVersion).where(
            ModelVersion.project_id == project.id, ModelVersion.version == version
        )
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="version not found")
    if record.artifact_format != "linear-json":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="inference is currently available only for linear JSON models",
        )
    path = db.info["settings"].storage_dir / record.stored_filename
    try:
        model = json.loads(path.read_text(encoding="utf-8"))
        weights = model["weights"]
        bias = float(model.get("bias", 0.0))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="invalid artifact"
        ) from None
    if len(payload.features) != len(weights):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"expected {len(weights)} features",
        )
    if not all(math.isfinite(feature) for feature in payload.features):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="features must be finite numbers",
        )
    output = (
        sum(
            float(weight) * feature
            for weight, feature in zip(weights, payload.features, strict=True)
        )
        + bias
    )
    return InferenceResponse(project_id=project.id, version=record.version, output=output)
