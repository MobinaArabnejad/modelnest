from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import ApiKey, User
from app.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from app.security import generate_api_key, hash_api_key

router = APIRouter(prefix="/api/keys", tags=["API keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_key(
    payload: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    raw_key = generate_api_key()
    record = ApiKey(
        user_id=user.id,
        name=payload.name.strip(),
        prefix=raw_key[:11],
        key_hash=hash_api_key(raw_key),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiKeyCreated(id=record.id, name=record.name, key=raw_key, prefix=record.prefix)


@router.get("", response_model=list[ApiKeyResponse])
def list_keys(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.user_id == user.id)))


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    record = db.get(ApiKey, key_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    record.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
