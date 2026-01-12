from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.api.core.db import get_db
from src.api.core.models import Project, ProjectStatus, Skill, User, UserRole
from src.api.deps import get_current_user, get_optional_user
from src.api.pagination import compute_page, count_total
from src.api.schemas import PaginatedResponse, ProjectCreate, ProjectOut, ProjectUpdate, SkillOut

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_out(project: Project) -> ProjectOut:
    skills_out = [SkillOut.model_validate(s, from_attributes=True) for s in (project.skills or [])]
    base = ProjectOut.model_validate(project, from_attributes=True)
    return base.model_copy(update={"skills": skills_out})


@router.get(
    "",
    response_model=PaginatedResponse[ProjectOut],
    summary="List projects (paginated)",
    description=(
        "List projects (paginated). If unauthenticated: returns only published projects. "
        "If authenticated as user: returns own projects + published projects. "
        "If authenticated as admin: returns all projects."
    ),
    operation_id="projects_list",
)
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_optional_user)] = None,
    status_filter: Optional[ProjectStatus] = Query(default=None, alias="status", description="Filter by project status"),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[ProjectOut]:
    """List projects with visibility rules and pagination."""
    base_stmt = select(Project).options(selectinload(Project.skills)).order_by(Project.created_at.desc())

    if status_filter is not None:
        base_stmt = base_stmt.where(Project.status == status_filter)

    if current_user is None:
        base_stmt = base_stmt.where(Project.status == ProjectStatus.published)
    else:
        if current_user.role != UserRole.admin:
            # own projects or published
            base_stmt = base_stmt.where((Project.owner_user_id == current_user.id) | (Project.status == ProjectStatus.published))

    total = count_total(db, base_stmt)
    p = compute_page(page=page, page_size=page_size)
    stmt = base_stmt.offset(p.offset).limit(p.limit)

    projects = db.execute(stmt).scalars().unique().all()
    return PaginatedResponse[ProjectOut](
        items=[_project_to_out(prj) for prj in projects],
        page=p.page,
        page_size=p.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create a project owned by the current user, optionally linking skills by id.",
    operation_id="projects_create",
)
def create_project(
    payload: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectOut:
    """Create a project for current user."""
    skills: list[Skill] = []
    if payload.skill_ids:
        skills = db.execute(select(Skill).where(Skill.id.in_(payload.skill_ids))).scalars().all()
        if len(skills) != len(set(payload.skill_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skill_ids are invalid")

    project = Project(
        owner_user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        repo_url=str(payload.repo_url) if payload.repo_url is not None else None,
        live_url=str(payload.live_url) if payload.live_url is not None else None,
        status=payload.status,
        skills=skills,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    # reload skills
    project = (
        db.execute(select(Project).where(Project.id == project.id).options(selectinload(Project.skills)))
        .scalars()
        .first()
    )
    return _project_to_out(project)


@router.get(
    "/{project_id}",
    response_model=ProjectOut,
    summary="Get project",
    description="Fetch a project by id. Unauthenticated users can only fetch published projects.",
    operation_id="projects_get",
)
def get_project(
    project_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_optional_user)] = None,
) -> ProjectOut:
    """Get a project by id with access control."""
    project = (
        db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.skills)))
        .scalars()
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if current_user is None:
        if project.status != ProjectStatus.published:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    else:
        if (
            current_user.role != UserRole.admin
            and project.owner_user_id != current_user.id
            and project.status != ProjectStatus.published
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this project")

    return _project_to_out(project)


@router.put(
    "/{project_id}",
    response_model=ProjectOut,
    summary="Update project",
    description="Update a project. Users can edit their own projects; admins can edit any project.",
    operation_id="projects_update",
)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ProjectOut:
    """Update a project with ownership/admin enforcement."""
    project = (
        db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.skills)))
        .scalars()
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if current_user.role != UserRole.admin and project.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this project")

    data = payload.model_dump(exclude_unset=True)
    skill_ids = data.pop("skill_ids", None)

    # Handle URL types possibly being HttpUrl
    if "repo_url" in data and data["repo_url"] is not None:
        data["repo_url"] = str(data["repo_url"])
    if "live_url" in data and data["live_url"] is not None:
        data["live_url"] = str(data["live_url"])

    for field, value in data.items():
        setattr(project, field, value)

    if skill_ids is not None:
        skills = db.execute(select(Skill).where(Skill.id.in_(skill_ids))).scalars().all() if skill_ids else []
        if skill_ids and len(skills) != len(set(skill_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more skill_ids are invalid")
        project.skills = skills

    db.commit()
    db.refresh(project)
    project = (
        db.execute(select(Project).where(Project.id == project_id).options(selectinload(Project.skills)))
        .scalars()
        .first()
    )
    return _project_to_out(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Delete a project. Users can delete their own; admins can delete any.",
    operation_id="projects_delete",
)
def delete_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete project by id."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if current_user.role != UserRole.admin and project.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this project")

    db.delete(project)
    db.commit()
    return None
