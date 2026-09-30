import json
import logging
import urllib.parse
from datetime import timedelta
from typing import Union

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
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

logger = logging.getLogger("emploreralk.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── Google OAuth2 constants ─────────────────────────────────────────────────
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPE = "openid email profile"

# ─── LinkedIn OAuth2 constants ───────────────────────────────────────────────
LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_SCOPE = "openid profile email"


# ─── Helpers ─────────────────────────────────────────────────────────────────

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
        avatar_url=user.avatar_url,
        created_at=user.created_at,
    )


def _mint_token(user: User) -> str:
    """Create a JWT access token for the given user."""
    return create_access_token(
        subject=user.email,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


# ─── Standard email / password routes ────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.

    Accepts role-specific extra fields:
    - Job Seekers: current_role, target_role, skills
    - Recruiters:  company
    """
    clean_email = payload.email.strip().lower()

    # 1. Check if email is already registered
    existing = db.query(User).filter(User.email.ilike(clean_email)).first()
    if existing:
        if not existing.hashed_password:
            auth_provider = "Google" if existing.google_id else ("LinkedIn" if existing.linkedin_id else "a social provider")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with this email exists via {auth_provider}. Please sign in using {auth_provider}.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered. Please sign in instead.",
        )

    # 2. Hash the password
    hashed_pw = get_password_hash(payload.password)

    # 3. Create User record
    user = User(
        email=clean_email,
        hashed_password=hashed_pw,
        name=payload.name.strip(),
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
    access_token = _mint_token(user)

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
    clean_email = payload.email.strip().lower()

    # 1. Look up user by email (case-insensitive)
    user = db.query(User).filter(User.email.ilike(clean_email)).first()

    # 2. Validate credentials & account state
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. If you don't have an account, please sign up first.",
        )

    if not user.hashed_password:
        auth_provider = "Google" if user.google_id else ("LinkedIn" if user.linkedin_id else "a social account")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This account was created with {auth_provider}. Please sign in using {auth_provider}.",
        )

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact support.",
        )

    # 3. Generate JWT token
    access_token = _mint_token(user)

    return AuthResponse(
        user=_user_to_response(user),
        token=access_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return _user_to_response(current_user)


# ─── Google OAuth2 routes ─────────────────────────────────────────────────────

@router.get("/google/login", summary="Redirect user to Google OAuth2 consent screen")
def google_login():
    """
    Build the Google OAuth2 authorization URL and redirect the browser to it.
    The frontend simply calls window.location.href = '/api/auth/google/login'.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server.",
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPE,
        "access_type": "offline",
        "prompt": "select_account",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/google/callback", summary="Handle Google OAuth2 callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db),
):
    """
    Exchange the authorization code for tokens, fetch the user profile from
    Google, then create-or-login the local user and redirect the browser back
    to the frontend SPA with the JWT token embedded in the URL fragment.

    Frontend reads: window.location.hash → #token=...&user=...
    """
    # ── 1. Exchange auth code for access token ───────────────────────────────
    token_data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data=token_data)

    if token_resp.status_code != 200:
        logger.error("Google token exchange failed: %s", token_resp.text)
        error_redirect = f"{settings.FRONTEND_URL}/#google-error=token_exchange_failed"
        return RedirectResponse(url=error_redirect)

    token_json = token_resp.json()
    access_token_google = token_json.get("access_token")

    if not access_token_google:
        error_redirect = f"{settings.FRONTEND_URL}/#google-error=no_access_token"
        return RedirectResponse(url=error_redirect)

    # ── 2. Fetch user info from Google ───────────────────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_google}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error("Google userinfo fetch failed: %s", userinfo_resp.text)
        error_redirect = f"{settings.FRONTEND_URL}/#google-error=userinfo_failed"
        return RedirectResponse(url=error_redirect)

    google_user = userinfo_resp.json()
    google_id = google_user.get("sub")
    email = google_user.get("email", "")
    name = google_user.get("name", email.split("@")[0] if email else "Google User")
    avatar_url = google_user.get("picture")

    if not email or not google_id:
        error_redirect = f"{settings.FRONTEND_URL}/#google-error=missing_profile"
        return RedirectResponse(url=error_redirect)

    # ── 3. Find or create local user ─────────────────────────────────────────
    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        # Check if a password-based account with same email already exists
        user = db.query(User).filter(User.email == email).first()

    if user:
        # Update google_id / avatar if missing / changed
        changed = False
        if not user.google_id:
            user.google_id = google_id
            changed = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
    else:
        # Brand-new user — create with default "seeker" role
        user = User(
            email=email,
            name=name,
            hashed_password=None,  # OAuth-only account
            google_id=google_id,
            avatar_url=avatar_url,
            role="seeker",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new Google OAuth user: %s", email)

    if not user.is_active:
        error_redirect = f"{settings.FRONTEND_URL}/#google-error=account_disabled"
        return RedirectResponse(url=error_redirect)

    # ── 4. Mint our own JWT and redirect to frontend ──────────────────────────
    jwt_token = _mint_token(user)
    user_payload = _user_to_response(user).model_dump()
    # Serialize user payload as JSON then URL-encode it for the fragment
    user_json = urllib.parse.quote(json.dumps(user_payload, default=str))

    redirect_url = (
        f"{settings.FRONTEND_URL}/#google-auth"
        f"?token={jwt_token}"
        f"&user={user_json}"
    )
    return RedirectResponse(url=redirect_url)


# ─── LinkedIn OAuth2 routes ───────────────────────────────────────────────────

@router.get("/linkedin/login", summary="Redirect user to LinkedIn OAuth2 consent screen")
def linkedin_login():
    """
    Build the LinkedIn OAuth2 authorization URL and redirect the browser to it.
    The frontend simply calls window.location.href = '/api/auth/linkedin/login'.
    """
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LinkedIn OAuth is not configured on this server.",
        )

    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "scope": LINKEDIN_SCOPE,
    }
    auth_url = f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=auth_url)


@router.get("/linkedin/callback", summary="Handle LinkedIn OAuth2 callback")
async def linkedin_callback(
    code: str = Query(..., description="Authorization code from LinkedIn"),
    db: Session = Depends(get_db),
):
    """
    Exchange the authorization code for tokens, fetch the user profile from
    LinkedIn, then create-or-login the local user and redirect the browser back
    to the frontend SPA.
    """
    # ── 1. Exchange auth code for access token ───────────────────────────────
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(LINKEDIN_TOKEN_URL, data=token_data)

    if token_resp.status_code != 200:
        logger.error("LinkedIn token exchange failed: %s", token_resp.text)
        error_redirect = f"{settings.FRONTEND_URL}/#linkedin-error=token_exchange_failed"
        return RedirectResponse(url=error_redirect)

    token_json = token_resp.json()
    access_token_linkedin = token_json.get("access_token")

    if not access_token_linkedin:
        error_redirect = f"{settings.FRONTEND_URL}/#linkedin-error=no_access_token"
        return RedirectResponse(url=error_redirect)

    # ── 2. Fetch user info from LinkedIn ─────────────────────────────────────
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token_linkedin}"},
        )

    if userinfo_resp.status_code != 200:
        logger.error("LinkedIn userinfo fetch failed: %s", userinfo_resp.text)
        error_redirect = f"{settings.FRONTEND_URL}/#linkedin-error=userinfo_failed"
        return RedirectResponse(url=error_redirect)

    linkedin_user = userinfo_resp.json()
    linkedin_id = linkedin_user.get("sub")
    email = linkedin_user.get("email")
    name = linkedin_user.get("name", email.split("@")[0] if email else "LinkedIn User")
    avatar_url = linkedin_user.get("picture")

    if not email or not linkedin_id:
        error_redirect = f"{settings.FRONTEND_URL}/#linkedin-error=missing_profile"
        return RedirectResponse(url=error_redirect)

    # ── 3. Find or create local user ─────────────────────────────────────────
    user = db.query(User).filter(User.linkedin_id == linkedin_id).first()

    if not user:
        # Check if an account with same email already exists
        user = db.query(User).filter(User.email == email).first()

    if user:
        # Update linkedin_id / avatar if missing / changed
        changed = False
        if not user.linkedin_id:
            user.linkedin_id = linkedin_id
            changed = True
        if avatar_url and user.avatar_url != avatar_url:
            user.avatar_url = avatar_url
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
    else:
        # Brand-new user
        user = User(
            email=email,
            name=name,
            hashed_password=None,
            linkedin_id=linkedin_id,
            avatar_url=avatar_url,
            role="seeker",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created new LinkedIn OAuth user: %s", email)

    if not user.is_active:
        error_redirect = f"{settings.FRONTEND_URL}/#linkedin-error=account_disabled"
        return RedirectResponse(url=error_redirect)

    # ── 4. Mint our own JWT and redirect to frontend ──────────────────────────
    jwt_token = _mint_token(user)
    user_payload = _user_to_response(user).model_dump()
    user_json = urllib.parse.quote(json.dumps(user_payload, default=str))

    redirect_url = (
        f"{settings.FRONTEND_URL}/#linkedin-auth"
        f"?token={jwt_token}"
        f"&user={user_json}"
    )
    return RedirectResponse(url=redirect_url)
