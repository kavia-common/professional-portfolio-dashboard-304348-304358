from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import ContactMessage
from src.api.deps import require_admin
from src.api.pagination import compute_page, count_total
from src.api.schemas import (
    ContactMessageCreate,
    ContactMessageOut,
    ContactMessageUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "/messages",
    response_model=ContactMessageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit contact message",
    description="Public endpoint to submit a contact message.",
    operation_id="contact_submit_message",
)
def submit_contact_message(
    payload: ContactMessageCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ContactMessageOut:
    """Create a new contact message."""
    msg = ContactMessage(
        sender_name=payload.sender_name,
        sender_email=str(payload.sender_email),
        subject=payload.subject,
        message=payload.message,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return ContactMessageOut.model_validate(msg, from_attributes=True)


@router.get(
    "/messages",
    response_model=PaginatedResponse[ContactMessageOut],
    summary="List contact messages (admin, paginated)",
    description="List submitted contact messages with pagination. Requires admin.",
    operation_id="contact_list_messages",
)
def list_contact_messages(
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
) -> PaginatedResponse[ContactMessageOut]:
    """Admin-only list of contact messages with pagination."""
    base_stmt = select(ContactMessage).order_by(ContactMessage.created_at.desc())
    total = count_total(db, base_stmt)
    p = compute_page(page=page, page_size=page_size)
    stmt = base_stmt.offset(p.offset).limit(p.limit)

    msgs = db.execute(stmt).scalars().all()
    return PaginatedResponse[ContactMessageOut](
        items=[ContactMessageOut.model_validate(m, from_attributes=True) for m in msgs],
        page=p.page,
        page_size=p.page_size,
        total=total,
    )


@router.put(
    "/messages/{message_id}",
    response_model=ContactMessageOut,
    summary="Update contact message status (admin)",
    description="Update status for a contact message. Requires admin.",
    operation_id="contact_update_message",
)
def update_contact_message_status(
    message_id: int,
    payload: ContactMessageUpdate,
    _: Annotated[object, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ContactMessageOut:
    """Admin-only status update for contact messages."""
    msg = db.get(ContactMessage, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    msg.status = payload.status
    db.commit()
    db.refresh(msg)
    return ContactMessageOut.model_validate(msg, from_attributes=True)
