import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.settings import FRONTEND_URL, VALID_REVIEW_TYPES
from app.database import get_db
from app.models.models import Paper
from app.models.project import Project
from app.models.project_access_restriction import ProjectAccessRestriction
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.utils.auth_dependency import get_current_user
from app.utils.workspace_access import get_workspace_or_404, require_member

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
    )
    db.add(membership)
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
    db.commit()

    return workspace
