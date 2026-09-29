from datetime import timedelta
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    UserResponse,
    AuthResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_to_response(user: User) -> UserResponse:
    """Convert a User ORM object to a UserResponse dict/schema."""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        current_role=user.current_role,
        target_role=user.target_role,
        skills=user.get_skills_list(),
        company=user.company,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.

    Accepts role-specific extra fields:
    - Job Seekers: current_role, target_role, skills
    - Recruiters:  company
    """
    # 1. Check if email is already registered
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 2. Hash the password
    hashed_pw = get_password_hash(payload.password)

    # 3. Create User record
    user = User(
        email=payload.email,
        hashed_password=hashed_pw,
        name=payload.name,
        role=payload.role if payload.role in ("seeker", "recruiter", "admin") else "seeker",
        current_role=payload.current_role,
        target_role=payload.target_role,
        company=payload.company,
        is_active=True,
    )

    # 4. Handle skills normalization
    if payload.skills is not None:
        user.set_skills_list(payload.skills)

    db.add(user)
    db.commit()
    db.refresh(user)

    # 5. Generate JWT token
    access_token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return AuthResponse(
        user=_user_to_response(user),
        token=access_token,
        token_type="bearer",
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate an existing user with email and password.
    Returns the user object and a JWT access token.
    """
    # 1. Look up user by email
    user = db.query(User).filter(User.email == payload.email).first()

    # 2. Validate credentials (same error for both missing user and wrong password — avoids email enumeration)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact support.",
        )

    # 3. Generate JWT token
    access_token = create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return AuthResponse(
        user=_user_to_response(user),
        token=access_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return _user_to_response(current_user)

