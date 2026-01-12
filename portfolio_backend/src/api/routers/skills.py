from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import Skill
from src.api.deps import require_admin
from src.api.pagination import compute_page, count_total
from src.api.schemas import PaginatedResponse, SkillCreate, SkillOut, SkillUpdate

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get(
    "",
    response_model=PaginatedResponse[SkillOut],
    summary="List skills (paginated)",
    description="List all skills (public) with pagination.",
    operation_id="skills_list",
)
def list_skills(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=50, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[SkillOut]:
    """List all skills with pagination."""
    base_stmt = select(Skill).order_by(Skill.name.asc())
    total = count_total(db, base_stmt)
    p = compute_page(page=page, page_size=page_size)
    stmt = base_stmt.offset(p.offset).limit(p.limit)

    skills = db.execute(stmt).scalars().all()
    return PaginatedResponse[SkillOut](
        items=[SkillOut.model_validate(s, from_attributes=True) for s in skills],
        page=p.page,
        page_size=p.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=SkillOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create skill (admin)",
    description="Create a new skill. Requires admin.",
    operation_id="skills_create",
)
def create_skill(
    payload: SkillCreate,
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SkillOut:
    """Create a new skill (admin only)."""
    skill = Skill(name=payload.name, category=payload.category, level=payload.level)
    db.add(skill)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Skill already exists or invalid data")
    db.refresh(skill)
    return SkillOut.model_validate(skill, from_attributes=True)


@router.put(
    "/{skill_id}",
    response_model=SkillOut,
    summary="Update skill (admin)",
    description="Update an existing skill. Requires admin.",
    operation_id="skills_update",
)
def update_skill(
    skill_id: int,
    payload: SkillUpdate,
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> SkillOut:
    """Update a skill (admin only)."""
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict updating skill")
    db.refresh(skill)
    return SkillOut.model_validate(skill, from_attributes=True)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete skill (admin)",
    description="Delete a skill. Requires admin.",
    operation_id="skills_delete",
)
def delete_skill(
    skill_id: int,
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a skill (admin only)."""
    skill = db.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    db.delete(skill)
    db.commit()
    return None
