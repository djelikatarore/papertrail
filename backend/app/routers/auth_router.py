import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config.settings import (
    FRONTEND_URL,
    GOOGLE_CLIENT_ID,
    RESET_TOKEN_EXPIRE_MINUTES,
    VERIFICATION_TOKEN_EXPIRE_MINUTES,
)
from app.database import get_db
from app.models.user import User
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import WorkspaceMember
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.services.email_service import send_reset_password_email, send_verification_email
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.password_validation import validate_password_strength

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    invite_token: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleSignInRequest(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    created_at: str | None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class UpdateProfileRequest(BaseModel):
    full_name: str


class SignupResponse(UserResponse):
    email_verified: bool


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if not payload.full_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name cannot be empty")

    password_error = validate_password_strength(payload.password)
    if password_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # A token that doesn't resolve to a still-pending invitation is treated
    # as stale/invalid and simply ignored (signup still succeeds, just
    # without auto-join) — but a token that DOES resolve and was sent to a
    # different email is rejected outright, since silently joining the
    # signer-upper to someone else's invited workspace would be wrong.
    invitation = None
    if payload.invite_token:
        invitation = (
            db.query(WorkspaceInvitation)
            .filter(WorkspaceInvitation.token == payload.invite_token, WorkspaceInvitation.accepted_at.is_(None))
            .first()
        )
        if invitation and invitation.email.lower() != payload.email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation was sent to a different email address.",
            )

    user = User(
        full_name=payload.full_name.strip(),
        email=payload.email,
        password_hash=hash_password(payload.password),
        email_verified=False,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    verification_token = secrets.token_urlsafe(32)
    user.verification_token = verification_token
    user.verification_token_expires_at = (
        datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_TOKEN_EXPIRE_MINUTES)
    ).isoformat()
    db.commit()

    verify_link = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    try:
        send_verification_email(user.email, verify_link)
    except Exception as exc:
        # Can't confirm this address is reachable at all (e.g. a nonexistent
        # domain) — the account is unusable without a working confirmation
        # link, so it's deleted rather than left as a dead, unverifiable row.
        # This only catches an immediate SMTP rejection, not a genuine
        # async bounce on an otherwise-valid domain — see send_verification_email.
        safe_log(f"[auth_router] Verification email failed for {user.email}, rolling back signup: {exc}")
        db.delete(user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not send a confirmation email to this address. Please check that it's valid and try again.",
        )

    if invitation:
        db.add(
            WorkspaceMember(
                workspace_id=invitation.workspace_id,
                user_id=user.id,
                role="MEMBER",
                joined_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        invitation.accepted_at = datetime.now(timezone.utc).isoformat()
        db.commit()

    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    # Checked only after credentials are confirmed correct — an unverified
    # account shouldn't reveal its verification status to someone who
    # doesn't actually know the password.
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email before logging in. Check your inbox for the confirmation link.",
        )

    token, expires_at = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.post("/google", response_model=TokenResponse)
def login_with_google(payload: GoogleSignInRequest, db: Session = Depends(get_db)):
    """Verifies a real Google ID token (from Google Identity Services on the
    frontend) against Google's own public keys — this is what makes it
    impossible to fake, unlike a plain email-format check. Logs in an
    existing Google-linked account, links Google onto a matching
    email/password account on first use, or creates a brand-new
    password-less account if neither exists."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google sign-in is not configured on this server")

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.id_token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google sign-in token")

    # Google's own confirmation that this email belongs to the account —
    # required before trusting it enough to link onto an existing user below.
    if not claims.get("email_verified"):
        raise HTTPException(status_code=401, detail="Google account email is not verified")

    google_id = claims["sub"]
    email = claims["email"]
    full_name = claims.get("name") or email.split("@")[0]

    user = db.query(User).filter(User.google_id == google_id).first()

    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Google independently confirmed this email belongs to this
            # account (email_verified check above) — a stronger guarantee
            # than our own click-the-link flow, so linking also verifies it.
            user.google_id = google_id
            user.email_verified = True
            db.commit()
        else:
            user = User(
                full_name=full_name,
                email=email,
                password_hash=None,
                google_id=google_id,
                email_verified=True,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token, expires_at = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_at=expires_at)


@router.get("/verify-email", response_model=MessageResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    """Clearing verification_token on success also makes an already-used
    link correctly fail as "invalid" on a second click — there's nothing
    left to match against, so no separate "already used" state is needed."""
    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid, expired, or already-used verification link.",
    )

    user = db.query(User).filter(User.verification_token == token).first()
    if not user or not user.verification_token_expires_at:
        raise invalid_token

    expires_at = datetime.fromisoformat(user.verification_token_expires_at)
    if datetime.now(timezone.utc) > expires_at:
        raise invalid_token

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    db.commit()

    return MessageResponse(message="Email verified successfully. You can now log in.")


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.full_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Full name cannot be empty")

    current_user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = MessageResponse(
        message="If an account with that email exists, a reset link has been sent."
    )

    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        return generic_response

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)

    user.reset_token = token
    user.reset_token_expires_at = expires_at.isoformat()
    db.commit()

    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    try:
        send_reset_password_email(user.email, reset_link)
    except Exception as exc:
        safe_log(f"[email_service] Failed to send reset email to {user.email}: {exc}")

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    password_error = validate_password_strength(payload.new_password)
    if password_error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=password_error)

    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token",
    )

    user = db.query(User).filter(User.reset_token == payload.token).first()
    if not user or not user.reset_token_expires_at:
        raise invalid_token

    expires_at = datetime.fromisoformat(user.reset_token_expires_at)
    if datetime.now(timezone.utc) > expires_at:
        raise invalid_token

    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()

    return MessageResponse(message="Password has been reset successfully.")
