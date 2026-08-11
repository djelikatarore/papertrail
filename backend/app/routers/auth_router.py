import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.config.settings import FRONTEND_URL, RESET_TOKEN_EXPIRE_MINUTES
from app.database import get_db
from app.models.user import User
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import WorkspaceMember
from app.services.auth_service import create_access_token, hash_password, verify_password
from app.services.email_service import send_reset_password_email
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


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

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

    token, expires_at = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_at=expires_at)


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
