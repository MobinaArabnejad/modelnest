from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    username = payload.username.strip().lower()
    first_user = db.scalar(select(func.count(User.id))) == 0
    settings = db.info["settings"]
    if first_user and settings.environment.lower() == "production":
        expected = settings.bootstrap_token or ""
        supplied = payload.bootstrap_token or ""
        if not secrets.compare_digest(supplied, expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="valid bootstrap token required for the first administrator",
            )
    user = User(
        username=username,
        password_hash=hash_password(payload.password),
        role="admin" if first_user else "user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="username already exists"
        ) from None
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.username == payload.username.strip().lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    settings = db.info["settings"]
    token = create_access_token(user.id, settings.secret_key, settings.access_token_minutes)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user
