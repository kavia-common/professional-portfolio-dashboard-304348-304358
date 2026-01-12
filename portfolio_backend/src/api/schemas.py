from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from src.api.core.models import ContactMessageStatus, ProjectStatus, UserRole

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Common pagination query params."""

    page: int = Field(
        default=1,
        ge=1,
        description="1-based page number (must be >= 1).",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Items per page (1..100).",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated list response shape."""

    items: List[T] = Field(..., description="Items for the current page.")
    page: int = Field(..., description="Current page (1-based).")
    page_size: int = Field(..., description="Current page size.")
    total: int = Field(..., ge=0, description="Total number of matching items.")


class TokenResponse(BaseModel):
    """JWT token response payload."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")


class UserPublic(BaseModel):
    """Public user fields."""

    id: int = Field(..., description="User ID")
    email: EmailStr = Field(..., description="User email")
    username: str = Field(..., description="Username")
    role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(..., description="Creation timestamp")


class UserCreate(BaseModel):
    """Request model to create a new user account."""

    email: EmailStr = Field(..., description="Email address")
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3..50 chars).",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plain password (8..128 chars; will be hashed).",
    )


class LoginRequest(BaseModel):
    """Request model for login."""

    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=1, max_length=128, description="Password")


class ProfileBase(BaseModel):
    """Shared profile fields."""

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Full name")
    bio: Optional[str] = Field(default=None, max_length=1000, description="Bio (max 1000 chars)")
    avatar_url: Optional[HttpUrl] = Field(default=None, description="Avatar URL (must be a valid URL)")
    location: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Location")
    website: Optional[HttpUrl] = Field(default=None, description="Website URL (must be a valid URL)")
    socials: Dict[str, Any] = Field(default_factory=dict, description="Social links object")


class ProfileUpdate(ProfileBase):
    """Request model to update a profile."""

    pass


class ProfileOut(ProfileBase):
    """Response model for profile."""

    id: int = Field(..., description="Profile ID")
    user_id: int = Field(..., description="User ID")
    updated_at: datetime = Field(..., description="Last updated timestamp")


class SkillBase(BaseModel):
    """Shared skill fields."""

    name: str = Field(..., min_length=1, max_length=100, description="Skill name")
    category: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Category (e.g. Backend)")
    level: int = Field(..., ge=1, le=5, description="Proficiency level from 1 to 5")


class SkillCreate(SkillBase):
    """Request model to create a skill."""

    pass


class SkillUpdate(BaseModel):
    """Request model to update a skill."""

    category: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Category (e.g. Backend)")
    level: Optional[int] = Field(default=None, ge=1, le=5, description="Proficiency level from 1 to 5")


class SkillOut(SkillBase):
    """Response model for a skill."""

    id: int = Field(..., description="Skill ID")
    created_at: datetime = Field(..., description="Creation timestamp")


class ProjectBase(BaseModel):
    """Shared project fields."""

    title: str = Field(..., min_length=1, max_length=200, description="Project title")
    description: Optional[str] = Field(default=None, max_length=5000, description="Project description (max 5000 chars)")
    repo_url: Optional[HttpUrl] = Field(default=None, description="Repository URL (must be a valid URL)")
    live_url: Optional[HttpUrl] = Field(default=None, description="Live demo URL (must be a valid URL)")
    status: ProjectStatus = Field(default=ProjectStatus.draft, description="Project status")


class ProjectCreate(ProjectBase):
    """Request model to create a project."""

    skill_ids: List[int] = Field(default_factory=list, description="List of skill IDs to associate")


class ProjectUpdate(BaseModel):
    """Request model to update a project."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Project title")
    description: Optional[str] = Field(default=None, max_length=5000, description="Project description (max 5000 chars)")
    repo_url: Optional[HttpUrl] = Field(default=None, description="Repository URL (must be a valid URL)")
    live_url: Optional[HttpUrl] = Field(default=None, description="Live demo URL (must be a valid URL)")
    status: Optional[ProjectStatus] = Field(default=None, description="Project status")
    skill_ids: Optional[List[int]] = Field(default=None, description="Replace skill associations with these IDs")


class ProjectOut(ProjectBase):
    """Response model for a project."""

    id: int = Field(..., description="Project ID")
    owner_user_id: int = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last updated timestamp")
    skills: List[SkillOut] = Field(default_factory=list, description="Associated skills")


class ContactMessageCreate(BaseModel):
    """Request model to submit a contact message."""

    sender_name: str = Field(..., min_length=1, max_length=100, description="Sender name")
    sender_email: EmailStr = Field(..., description="Sender email")
    subject: Optional[str] = Field(default=None, max_length=200, description="Subject (max 200 chars)")
    message: str = Field(..., min_length=10, max_length=5000, description="Message body (10..5000 chars)")


class ContactMessageUpdate(BaseModel):
    """Admin-only model to update message status."""

    status: ContactMessageStatus = Field(..., description="New status")


class ContactMessageOut(BaseModel):
    """Response model for contact messages."""

    id: int = Field(..., description="Message ID")
    sender_name: str = Field(..., description="Sender name")
    sender_email: EmailStr = Field(..., description="Sender email")
    subject: Optional[str] = Field(default=None, description="Subject")
    message: str = Field(..., description="Message body")
    status: ContactMessageStatus = Field(..., description="Status")
    created_at: datetime = Field(..., description="Creation timestamp")
