from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UserRole(str, enum.Enum):
    """Enum mirroring PostgreSQL user_role type."""

    user = "user"
    admin = "admin"


class ProjectStatus(str, enum.Enum):
    """Enum mirroring PostgreSQL project_status type."""

    draft = "draft"
    published = "published"


class ContactMessageStatus(str, enum.Enum):
    """Enum mirroring PostgreSQL contact_message_status type."""

    new = "new"
    read = "read"
    archived = "archived"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""


# Association table for many-to-many projects <-> skills
project_skills = Table(
    "project_skills",
    Base.metadata,
    mapped_column("project_id", BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    mapped_column("skill_id", BigInteger, ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User account model backed by `users` table."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_key"),
        UniqueConstraint("username", name="users_username_key"),
        Index("idx_users_email", "email"),
        Index("idx_users_username", "username"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    profile: Mapped[Optional["Profile"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Profile(Base):
    """Profile model backed by `profiles` table (1:1 with User)."""

    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id", name="profiles_user_id_key"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSONB in PostgreSQL; SQLAlchemy JSON maps fine for psycopg2.
    socials: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="profile")


class Project(Base):
    """Project model backed by `projects` table."""

    __tablename__ = "projects"
    __table_args__ = (Index("idx_projects_owner_user_id", "owner_user_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.draft,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    owner: Mapped["User"] = relationship(back_populates="projects")
    skills: Mapped[List["Skill"]] = relationship(
        secondary=project_skills,
        back_populates="projects",
    )


class Skill(Base):
    """Skill model backed by `skills` table."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("name", name="skills_name_key"),
        CheckConstraint("level BETWEEN 1 AND 5", name="skills_level_check"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    projects: Mapped[List["Project"]] = relationship(
        secondary=project_skills,
        back_populates="skills",
    )


class ContactMessage(Base):
    """Contact message model backed by `contact_messages` table."""

    __tablename__ = "contact_messages"
    __table_args__ = (
        Index("idx_contact_messages_sender_email", "sender_email"),
        Index("idx_contact_messages_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sender_name: Mapped[str] = mapped_column(Text, nullable=False)
    sender_email: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ContactMessageStatus] = mapped_column(
        Enum(ContactMessageStatus, name="contact_message_status"),
        nullable=False,
        default=ContactMessageStatus.new,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
