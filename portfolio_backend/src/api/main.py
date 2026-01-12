from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import settings
from src.api.core.db import engine
from src.api.core.models import Base
from src.api.routers import admin, auth, contact, profile, projects, skills

openapi_tags = [
    {"name": "auth", "description": "Authentication endpoints (JWT)."},
    {"name": "profile", "description": "Profile management for the authenticated user."},
    {"name": "projects", "description": "Project CRUD and publishing endpoints."},
    {"name": "skills", "description": "Skills listing and admin-managed CRUD."},
    {"name": "contact", "description": "Public contact form submission + admin inbox management."},
    {"name": "admin", "description": "Admin-only endpoints (RBAC)."},
]

app = FastAPI(
    title="Professional Portfolio Dashboard API",
    description=(
        "Backend API for a portfolio dashboard providing JWT authentication, role-based access control (RBAC), "
        "and CRUD endpoints for profiles, projects, skills, and contact messages."
    ),
    version="0.2.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    """
    Initialize application at startup.

    Notes:
    - Uses SQLAlchemy metadata create_all as a safe operation if tables already exist.
    - For production migrations, prefer Alembic (not included in this step).
    """
    Base.metadata.create_all(bind=engine)


@app.get(
    "/",
    summary="Health check",
    description="Simple health check endpoint.",
    operation_id="health_check",
)
def health_check():
    """Return a health check response."""
    return {"message": "Healthy"}


# Routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(skills.router)
app.include_router(projects.router)
app.include_router(contact.router)
app.include_router(admin.router)
