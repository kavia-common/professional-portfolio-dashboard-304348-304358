from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import User
from src.api.deps import require_admin
from src.api.pagination import compute_page, count_total
from src.api.schemas import PaginatedResponse, UserPublic

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=PaginatedResponse[UserPublic],
    summary="List users (admin, paginated)",
    description="List all users with pagination. Requires admin.",
    operation_id="admin_list_users",
)
def list_users(
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[UserPublic]:
    """Admin-only user list with pagination."""
    base_stmt = select(User).order_by(User.created_at.desc())
    total = count_total(db, base_stmt)
    p = compute_page(page=page, page_size=page_size)
    stmt = base_stmt.offset(p.offset).limit(p.limit)

    users = db.execute(stmt).scalars().all()
    return PaginatedResponse[UserPublic](
        items=[UserPublic.model_validate(u, from_attributes=True) for u in users],
        page=p.page,
        page_size=p.page_size,
        total=total,
    )
