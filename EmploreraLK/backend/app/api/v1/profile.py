from io import BytesIO
import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.notification import Notification
from app.models.candidate_cv import CandidateCV
from app.models.user import User
from app.schemas.auth import ProfileUpdateRequest, UserResponse
from app.components.matching.services.cv_parser import parse_cv
from app.components.matching.services.cv_storage import storage

router = APIRouter(prefix="/profile", tags=["Profile"])
logger = logging.getLogger("emploreralk.components.matching")


def _delete_stored_cv(storage_key: str) -> None:
    """Best-effort removal of a replaced/deleted CV file; the DB is the source of truth."""
    try:
        storage.delete(storage_key)
    except Exception as error:
        logger.warning("Could not delete stored CV object %s: %s", storage_key, error)


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

    db.add(Notification(
        user_id=user.id,
        type="profile",
        title="Profile updated",
        body="Your career profile and job recommendations will use your latest information.",
    ))
    db.commit()
    db.refresh(user)

    return {"user": _user_to_response(user)}


@router.post("/upload-cv")
async def upload_cv(
    email: str,
    cv: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Parse a CV and merge its discovered skills into the existing profile."""
    if current_user.email.lower() != email.strip().lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You may only upload your own CV")
    user = current_user
    if not cv.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CV filename is required")

    content = await cv.read()
    try:
        storage.validate_upload(cv.filename, cv.content_type or "", content)
        parsed_cv = await run_in_threadpool(parse_cv, cv.filename, content)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    try:
        # Blocking network upload (Google Drive) runs off the event loop.
        storage_key, digest = await run_in_threadpool(
            storage.store, user.id, cv.filename, cv.content_type or "", content
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        logger.error("CV storage upload failed for user %s: %s", user.id, error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CV storage is unavailable. Please try again later.",
        ) from error

    merged_skills = list(dict.fromkeys(user.get_skills_list() + parsed_cv.get("skills", [])))
    user.set_skills_list(merged_skills)
    existing_cv = db.query(CandidateCV).filter(CandidateCV.user_id == user.id).first()
    old_storage_key = existing_cv.storage_key if existing_cv else None
    record = existing_cv or CandidateCV(user_id=user.id)
    record.storage_key = storage_key
    record.original_filename = cv.filename
    record.content_type = cv.content_type or "application/octet-stream"
    record.size_bytes = len(content)
    record.sha256 = digest
    record.set_parsed_data(parsed_cv)
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _delete_stored_cv(storage_key)  # do not leave an orphaned file behind
        raise
    db.refresh(user)
    if old_storage_key and old_storage_key != storage_key:
        await run_in_threadpool(_delete_stored_cv, old_storage_key)
    return {
        "filename": cv.filename,
        "cv": parsed_cv,
        "cv_id": record.id,
        "download_url": "/api/profile/cv/download",
        "user": _user_to_response(user),
    }


@router.get("/cv")
def get_cv_metadata(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's persisted CV metadata and parsed details."""
    record = db.query(CandidateCV).filter(CandidateCV.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CV has been uploaded")
    return {
        "cv_id": record.id,
        "filename": record.original_filename,
        "content_type": record.content_type,
        "size_bytes": record.size_bytes,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "cv": record.get_parsed_data(),
        "download_url": "/api/profile/cv/download",
    }


@router.get("/cv/download")
def download_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download only the authenticated user's private CV object."""
    record = db.query(CandidateCV).filter(CandidateCV.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CV has been uploaded")
    try:
        content = storage.read(record.storage_key)
    except (FileNotFoundError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV object is unavailable") from error
    safe_filename = record.original_filename.replace('"', "")
    return StreamingResponse(
        BytesIO(content),
        media_type=record.content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.delete("/cv")
def delete_cv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the authenticated user's CV object and metadata."""
    record = db.query(CandidateCV).filter(CandidateCV.user_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No CV has been uploaded")
    storage_key = record.storage_key
    db.delete(record)
    db.commit()
    _delete_stored_cv(storage_key)
    return {"deleted": True}
