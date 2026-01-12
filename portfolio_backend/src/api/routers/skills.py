from __future__ import annotations

from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import Skill
from src.api.deps import require_admin
from src.api.schemas import SkillCreate, SkillOut, SkillUpdate

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get(
    "",
    response_model=List[SkillOut],
    summary="List skills",
    description="List all skills (public).",
    operation_id="skills_list",
)
def list_skills(db: Annotated[Session, Depends(get_db)]) -> List[SkillOut]:
    """List all skills."""
    skills = db.execute(select(Skill).order_by(Skill.name.asc())).scalars().all()
    return [SkillOut.model_validate(s, from_attributes=True) for s in skills]


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
