"""
Authentication routes for login and user info.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import LoginRequest, LoginResponse, UserInfo
from app.core.deps import get_current_user, get_db
from app.core.security import create_access_token, verify_password
from app.db.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    """
    Authenticate user and return JWT access token.

    Args:
        request: Login credentials
        db: Database session

    Returns:
        JWT token and user role

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by username
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "INVALID_CREDENTIALS",
                    "message": "Invalid username or password",
                }
            },
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.user_id, "role": user.role})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
    )


@router.get("/me", response_model=UserInfo)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserInfo:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user

    Returns:
        User information
    """
    return UserInfo(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
    )
