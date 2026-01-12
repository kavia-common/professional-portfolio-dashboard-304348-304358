from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import User, UserRole
from src.api.core.security import create_access_token, hash_password, verify_password
from src.api.schemas import LoginRequest, TokenResponse, UserCreate, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Role defaults to `user`.",
    operation_id="auth_register",
)
def register_user(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> UserPublic:
    """
    Register a new user.

    - Enforces unique email + username (per DB constraints).
    - Stores bcrypt password hash.
    """
    # Pre-checks for friendlier errors before DB unique constraint kicks in
    existing = db.execute(select(User).where((User.email == payload.email) | (User.username == payload.username))).scalars().first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists")

    user = User(
        email=str(payload.email),
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user, from_attributes=True)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with username and password and receive a JWT access token.",
    operation_id="auth_login",
)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Login endpoint returning a Bearer JWT."""
    user = db.execute(select(User).where(User.username == payload.username)).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(subject=str(user.id), additional_claims={"role": user.role.value})
    return TokenResponse(access_token=token)
