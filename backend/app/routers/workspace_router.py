import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config.settings import FRONTEND_URL
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.utils.auth_dependency import get_current_user
from app.utils.workspace_access import get_workspace_or_404

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str | None = None


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: str | None
    invite_link_token: str | None

    class Config:
        from_attributes = True


class InviteLinkResponse(BaseModel):
    invite_token: str
    invite_link: str


class InviteUserRequest(BaseModel):
    email: EmailStr
    credits: int = Field(default=0, ge=0, le=5)


class UpdateCreditsRequest(BaseModel):
    credits: int = Field(ge=0, le=5)


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    joined_at: str | None
    upload_credits: int

    class Config:
        from_attributes = True


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty")

    now = datetime.now(timezone.utc).isoformat()

    workspace = Workspace(
        name=payload.name.strip(),
        description=payload.description,
        owner_id=current_user.id,
        created_at=now,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="OWNER",
        joined_at=now,
    )
    db.add(membership)
    db.commit()

    return workspace


@router.post(
    "/{workspace_id}/invite",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_user_by_email(
    workspace_id: int,
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can invite users",
        )

    invited_user = db.query(User).filter(User.email == payload.email).first()
    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No user found with this email",
        )

    existing_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == invited_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this workspace")

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=invited_user.id,
        role="MEMBER",
        joined_at=datetime.now(timezone.utc).isoformat(),
        upload_credits=payload.credits,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


@router.patch("/{workspace_id}/members/{member_id}/credits", response_model=WorkspaceMemberResponse)
def update_member_credits(
    workspace_id: int,
    member_id: int,
    payload: UpdateCreditsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can modify upload credits",
        )

    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")

    membership.upload_credits = payload.credits
    db.commit()
    db.refresh(membership)

    return membership


@router.get("/{workspace_id}/invite-link", response_model=InviteLinkResponse)
def get_invite_link(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can generate an invite link",
        )

    if not workspace.invite_link_token:
        workspace.invite_link_token = secrets.token_urlsafe(16)
        db.commit()

    return InviteLinkResponse(
        invite_token=workspace.invite_link_token,
        invite_link=f"{FRONTEND_URL}/workspaces/join/{workspace.invite_link_token}",
    )


@router.post("/join/{token}", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def join_workspace_by_link(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = db.query(Workspace).filter(Workspace.invite_link_token == token).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite link")

    existing_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member of this workspace")

    membership = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="MEMBER",
        joined_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(membership)
    db.commit()

    return workspace
