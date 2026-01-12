from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Page:
    """Computed pagination values derived from query params."""

    page: int
    page_size: int
    offset: int
    limit: int


# PUBLIC_INTERFACE
def compute_page(*, page: int, page_size: int) -> Page:
    """Compute offset/limit for 1-based pagination.

    Args:
        page: 1-based page number (must be >= 1).
        page_size: number of items per page.

    Returns:
        Page object with offset/limit.
    """
    offset = (page - 1) * page_size
    return Page(page=page, page_size=page_size, offset=offset, limit=page_size)


# PUBLIC_INTERFACE
def count_total(db: Session, stmt: Select) -> int:
    """Count total rows for a given SELECT statement.

    Notes:
        This implementation drops ordering to avoid unnecessary work.
        It counts from a subquery of the statement, which is generally safe and portable.

    Args:
        db: SQLAlchemy session.
        stmt: SQLAlchemy Select for the items query.

    Returns:
        Total number of rows matching the statement.
    """
    subq = stmt.order_by(None).subquery()
    total = db.execute(select(func.count()).select_from(subq)).scalar_one()
    return int(total)
