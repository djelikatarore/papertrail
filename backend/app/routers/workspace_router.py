import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import FRONTEND_URL, VALID_REVIEW_TYPES
from app.database import get_db
from app.models.models import Paper
from app.models.project import Project
from app.models.project_access_restriction import ProjectAccessRestriction
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_invitation import WorkspaceInvitation
from app.models.workspace_member import WorkspaceMember
from app.routers.project_router import cascade_delete_project_contents
from app.services.email_service import send_workspace_invitation_email
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateWorkspaceRequest(BaseModel):
    name: str | None = None
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


class WorkspaceSummaryResponse(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: str | None
    role: str


class WorkspaceMemberDetailResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: str
    role: str
    joined_at: str | None


class InviteLinkResponse(BaseModel):
    invite_token: str
    invite_link: str


class InviteUserRequest(BaseModel):
    email: EmailStr


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: str
    joined_at: str | None

    class Config:
        from_attributes = True


class InviteResponse(BaseModel):
    """Always "invited" now — a real invitation email is always sent, and
    there's never an immediate membership, whether or not the email matches
    an existing account (see invite_user_by_email). member_id/role are kept
    on the response shape but stay unpopulated."""

    status: str
    email: str
    member_id: int | None = None
    role: str | None = None


class InvitationPreviewResponse(BaseModel):
    workspace_name: str
    email: str
    account_exists: bool


class AcceptInvitationResponse(BaseModel):
    workspace_id: int
    workspace_name: str


class PaperSearchResultResponse(BaseModel):
    id: int
    project_id: int | None
    filename: str
    title: str | None
    keywords: str | None
    review_type: str | None
    read_status: str
    detected_paper_type: str | None

    class Config:
        from_attributes = True


class ProjectSearchResultResponse(BaseModel):
    id: int
    title: str
    topic: str

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    papers: list[PaperSearchResultResponse]
    projects: list[ProjectSearchResultResponse]


def _ensure_workspace_name_available(db: Session, owner_id: int, name: str, exclude_workspace_id: int | None = None):
    # Unique per owner, not globally — two different users are free to both
    # name a workspace "Research", but the same owner can't have two.
    query = db.query(Workspace).filter(
        Workspace.owner_id == owner_id,
        func.lower(Workspace.name) == name.lower(),
    )
    if exclude_workspace_id is not None:
        query = query.filter(Workspace.id != exclude_workspace_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a workspace with this name",
        )


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty")

    _ensure_workspace_name_available(db, current_user.id, payload.name.strip())

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


@router.get("", response_model=list[WorkspaceSummaryResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Workspaces the current user belongs to, owner or member alike — there was
    previously no way to discover a user's own workspaces at all, only to create
    one or join by invite link/email."""
    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).all()
    workspaces_by_id = {
        w.id: w
        for w in db.query(Workspace).filter(Workspace.id.in_([m.workspace_id for m in memberships])).all()
    }

    return [
        WorkspaceSummaryResponse(
            id=w.id,
            name=w.name,
            description=w.description,
            owner_id=w.owner_id,
            created_at=w.created_at,
            role=m.role,
        )
        for m in memberships
        if (w := workspaces_by_id.get(m.workspace_id)) is not None
    ]


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    payload: UpdateWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can rename this workspace",
        )

    if payload.name is not None:
        if not payload.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workspace name cannot be empty")
        _ensure_workspace_name_available(db, workspace.owner_id, payload.name.strip(), exclude_workspace_id=workspace.id)
        workspace.name = payload.name.strip()
    if payload.description is not None:
        workspace.description = payload.description

    db.commit()
    db.refresh(workspace)

    return workspace


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes a workspace and everything in it: every project (cascaded the
    same way as a standalone project delete — see
    cascade_delete_project_contents — papers, drafts, chat history, files on
    disk), then the projects themselves, then every workspace membership,
    then the workspace row itself."""
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete this workspace",
        )

    project_ids = [pid for (pid,) in db.query(Project.id).filter(Project.workspace_id == workspace_id).all()]
    for project_id in project_ids:
        cascade_delete_project_contents(db, project_id)
    if project_ids:
        db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)

    db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).delete(synchronize_session=False)

    db.delete(workspace)
    db.commit()


@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberDetailResponse])
def list_workspace_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Any member can view the roster (matches list_projects' access scoping) —
    only mutating a project's per-member access is restricted to the owner,
    via the existing PATCH .../projects/{id}/access."""
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    memberships = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    users_by_id = {u.id: u for u in db.query(User).filter(User.id.in_([m.user_id for m in memberships])).all()}

    return [
        WorkspaceMemberDetailResponse(
            id=m.id,
            user_id=m.user_id,
            full_name=user.full_name,
            email=user.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in memberships
        if (user := users_by_id.get(m.user_id)) is not None
    ]


@router.delete("/{workspace_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_workspace_member(
    workspace_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Owner-only. Only cuts the member's future access — their past
    contributions (papers they uploaded, review comments they wrote) stay
    exactly where they are, still attributed to them, same as an
    access-restricted (but not removed) member's contributions already do
    (see update_project_access). Their per-project access restrictions are
    cleaned up since a removed member has no access to clean up anymore."""
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can remove a member",
        )

    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.id == member_id, WorkspaceMember.workspace_id == workspace_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")

    if membership.user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot remove yourself")

    db.query(ProjectAccessRestriction).filter(
        ProjectAccessRestriction.workspace_member_id == member_id
    ).delete(synchronize_session=False)
    db.delete(membership)
    db.commit()


@router.post(
    "/{workspace_id}/invite",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_user_by_email(
    workspace_id: int,
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Always sends a real invitation email with a token — never adds an
    existing account directly/silently. What happens after the link is
    clicked depends on whether the email matches an account (see
    get_invitation_preview's account_exists and POST .../accept): a new
    account auto-joins on signup (unchanged, see auth_router.signup), an
    existing account only joins after an explicit Accept."""
    workspace = get_workspace_or_404(workspace_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can invite users",
        )

    invited_user = db.query(User).filter(User.email == payload.email).first()

    if invited_user:
        existing_membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == invited_user.id,
            )
            .first()
        )
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User is already a member of this workspace"
            )

    # Reuse a still-pending invitation's token if this exact email was
    # already invited to this exact workspace (re-inviting becomes "resend"
    # rather than minting a second, orphaned token), otherwise create a new one.
    invitation = (
        db.query(WorkspaceInvitation)
        .filter(WorkspaceInvitation.workspace_id == workspace.id, WorkspaceInvitation.email == payload.email)
        .first()
    )
    if not invitation:
        invitation = WorkspaceInvitation(
            workspace_id=workspace.id,
            email=payload.email,
            token=secrets.token_urlsafe(24),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(invitation)
        db.commit()
        db.refresh(invitation)

    join_link = f"{FRONTEND_URL}/signup?invite={invitation.token}"
    try:
        send_workspace_invitation_email(payload.email, workspace.name, join_link)
    except Exception as exc:
        safe_log(f"[workspace_router] Failed to send invitation email to {payload.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the invitation email. Please try again.",
        )

    return InviteResponse(status="invited", email=payload.email)


@router.get("/invitations/{token}", response_model=InvitationPreviewResponse)
def get_invitation_preview(token: str, db: Session = Depends(get_db)):
    """Public (no auth) — powers "You've been invited to join <workspace>"
    on the signup page before the visitor has an account to authenticate
    with."""
    invitation = db.query(WorkspaceInvitation).filter(WorkspaceInvitation.token == token).first()
    if not invitation or invitation.accepted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or already-used invitation")

    workspace = db.query(Workspace).filter(Workspace.id == invitation.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation")

    account_exists = db.query(User).filter(User.email == invitation.email).first() is not None

    return InvitationPreviewResponse(
        workspace_name=workspace.name, email=invitation.email, account_exists=account_exists
    )


@router.post("/invitations/{token}/accept", response_model=AcceptInvitationResponse)
def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """For an EXISTING account only — a new account auto-joins at signup
    instead (see auth_router.signup) and never reaches this endpoint.
    Requires the logged-in user's email to match the invitation's, so
    someone logged in as the wrong account can't accept someone else's
    invitation — the invitation itself is left untouched in that case,
    still valid for whoever it was actually sent to."""
    invitation = db.query(WorkspaceInvitation).filter(WorkspaceInvitation.token == token).first()
    if not invitation or invitation.accepted_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used invitation"
        )

    if invitation.email.lower() != current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address.",
        )

    existing_membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == invitation.workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
        .first()
    )
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="You are already a member of this workspace"
        )

    workspace = db.query(Workspace).filter(Workspace.id == invitation.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation")

    db.add(
        WorkspaceMember(
            workspace_id=invitation.workspace_id,
            user_id=current_user.id,
            role="MEMBER",
            joined_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    invitation.accepted_at = datetime.now(timezone.utc).isoformat()
    db.commit()

    return AcceptInvitationResponse(workspace_id=workspace.id, workspace_name=workspace.name)


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


@router.get("/{workspace_id}/search", response_model=SearchResponse)
def search_workspace(
    workspace_id: int,
    q: str = Query(min_length=1, description="Keyword to search for"),
    review_type: str | None = Query(default=None, description="Filter papers by review type"),
    read_status: str | None = Query(default=None, description="Filter papers by read status"),
    detected_paper_type: str | None = Query(default=None, description="Filter papers by detected paper type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Keyword search across this workspace's projects (title/topic) and papers
    (title/keywords). Papers and projects are returned as two separate lists
    rather than merged — they lead to different views client-side and there's no
    shared relevance score to rank them together by. Scoped to projects the
    current member has access to (restricted projects, and their papers, are
    excluded — same rule as project listing).

    review_type/read_status/detected_paper_type narrow the papers list only —
    projects have no equivalent fields, so the projects list is unaffected and
    still returned based on `q` alone."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)

    if review_type is not None and review_type not in VALID_REVIEW_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"review_type must be one of: {', '.join(sorted(VALID_REVIEW_TYPES))}",
        )

    accessible_project_ids = [
        pid for (pid,) in db.query(Project.id).filter(Project.workspace_id == workspace_id).all()
    ]
    if membership.role != "OWNER":
        restricted_ids = {
            r.project_id
            for r in db.query(ProjectAccessRestriction)
            .filter(ProjectAccessRestriction.workspace_member_id == membership.id)
            .all()
        }
        accessible_project_ids = [pid for pid in accessible_project_ids if pid not in restricted_ids]

    pattern = f"%{q.strip().lower()}%"

    projects = (
        db.query(Project)
        .filter(
            Project.id.in_(accessible_project_ids),
            or_(func.lower(Project.title).like(pattern), func.lower(Project.topic).like(pattern)),
        )
        .all()
    )

    paper_filters = [
        Paper.project_id.in_(accessible_project_ids),
        or_(func.lower(Paper.title).like(pattern), func.lower(Paper.keywords).like(pattern)),
    ]
    if review_type is not None:
        paper_filters.append(Paper.review_type == review_type)
    if read_status is not None:
        paper_filters.append(func.lower(Paper.read_status) == read_status.strip().lower())
    if detected_paper_type is not None:
        paper_filters.append(func.lower(Paper.detected_paper_type) == detected_paper_type.strip().lower())

    papers = db.query(Paper).filter(*paper_filters).all()

    return SearchResponse(papers=papers, projects=projects)


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
    try:
        db.commit()
    except IntegrityError:
        # Same non-atomic-precheck race as invite_user_by_email above (e.g. a
        # double-fired join request) — the unique constraint is the real
        # guard, this just keeps the error response clean.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member of this workspace")

    return workspace
