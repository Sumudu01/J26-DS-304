from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.user import User
from app.schemas.auth import ProfileUpdateRequest, UserResponse

router = APIRouter(prefix="/profile", tags=["Profile"])


def _user_to_response(user: User) -> UserResponse:
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


@router.post("/update")
def update_profile(payload: ProfileUpdateRequest, db: Session = Depends(get_db)):
    """
    Update a seeker's skills and/or target_role.
    Called by SeekerDashboard.jsx /profile/update endpoint.
    Lookup is by email (no token required to match existing frontend usage).
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.skills is not None:
        user.set_skills_list(payload.skills)

    if payload.target_role is not None:
        user.target_role = payload.target_role

    db.commit()
    db.refresh(user)

    return {"user": _user_to_response(user)}

