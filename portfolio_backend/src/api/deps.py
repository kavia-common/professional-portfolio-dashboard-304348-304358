from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from src.api.core.db import get_db
from src.api.core.models import User, UserRole
from src.api.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user_from_bearer(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: Session,
) -> Optional[User]:
    """
    Internal helper to resolve a user from optional bearer credentials.

    Returns:
        User if token is present and valid; otherwise None.

    Raises:
        HTTPException(401) only for malformed/invalid tokens (present but invalid),
        and for token that references a missing user.
    """
    if credentials is None or not credentials.scheme.lower() == "bearer":
        return None

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    try:
        user_id = int(sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


# PUBLIC_INTERFACE
def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Resolve and return the currently authenticated user from a Bearer JWT.

    Raises:
        401 if missing/invalid token or user not found.
    """
    user = _resolve_user_from_bearer(credentials, db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


# PUBLIC_INTERFACE
def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> Optional[User]:
    """
    Resolve the current user if a valid Bearer JWT is provided, else return None.

    This is used for endpoints that support both authenticated and unauthenticated access.

    Raises:
        401 only if an Authorization header is present but invalid.
    """
    return _resolve_user_from_bearer(credentials, db)


# PUBLIC_INTERFACE
def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Enforce admin-only access.

    Returns:
        current_user if admin.

    Raises:
        403 if not admin.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
