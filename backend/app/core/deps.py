"""
FastAPI dependency injection functions.
"""
from typing import Annotated, Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import SessionLocal

# Security scheme
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get a database session.
    Ensures proper session cleanup.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Could not validate credentials",
                }
            },
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token payload invalid",
                }
            },
        )

    user = db.query(User).filter(User.user_id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                }
            },
        )

    return user


def require_role(required_role: str):
    """
    Dependency factory to require a specific user role.

    Args:
        required_role: Role name required (e.g., "warehouse_manager")

    Returns:
        Dependency function that validates user role
    """

    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "INSUFFICIENT_PERMISSIONS",
                        "message": f"Role '{required_role}' required",
                        "meta": {"user_role": current_user.role},
                    }
                },
            )
        return current_user

    return role_checker
