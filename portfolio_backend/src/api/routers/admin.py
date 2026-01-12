from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import User
from src.api.deps import require_admin
from src.api.schemas import UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=List[UserPublic],
    summary="List users (admin)",
    description="List all users. Requires admin.",
    operation_id="admin_list_users",
)
def list_users(
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> List[UserPublic]:
    """Admin-only user list."""
    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [UserPublic.model_validate(u, from_attributes=True) for u in users]
