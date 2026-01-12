from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import Profile, User
from src.api.deps import get_current_user
from src.api.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get(
    "/me",
    response_model=ProfileOut,
    summary="Get my profile",
    description="Return the authenticated user's profile. Creates an empty profile if missing.",
    operation_id="profile_get_me",
)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProfileOut:
    """Get or create the current user's profile."""
    profile = db.execute(select(Profile).where(Profile.user_id == current_user.id)).scalars().first()
    if not profile:
        profile = Profile(user_id=current_user.id, socials={})
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return ProfileOut.model_validate(profile, from_attributes=True)


@router.put(
    "/me",
    response_model=ProfileOut,
    summary="Update my profile",
    description="Update the authenticated user's profile fields.",
    operation_id="profile_update_me",
)
def update_my_profile(
    payload: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProfileOut:
    """Update current user's profile, creating it if absent."""
    profile = db.execute(select(Profile).where(Profile.user_id == current_user.id)).scalars().first()
    if not profile:
        profile = Profile(user_id=current_user.id, socials={})
        db.add(profile)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return ProfileOut.model_validate(profile, from_attributes=True)
