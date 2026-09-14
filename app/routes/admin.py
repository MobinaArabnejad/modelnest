from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_admin_user, get_db
from app.models import User
from app.schemas import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/api/admin", tags=["administration"])


@router.get("/users", response_model=list[UserResponse])
def list_users(_: User = Depends(get_admin_user), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/users/{user_id}/role", response_model=UserResponse)
def change_role(
    user_id: int,
    payload: UserRoleUpdate,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    if user.id == admin.id and payload.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="administrators cannot demote themselves",
        )
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
