from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project_access_restriction import ProjectAccessRestriction
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


def get_workspace_or_404(workspace_id: int, db: Session) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def require_member(workspace_id: int, user_id: int, db: Session) -> WorkspaceMember:
    membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )
    return membership


def require_project_access(project_id: int, membership: WorkspaceMember, db: Session) -> None:
    """Raises 404 (not 403) if the owner has restricted this member from this
    project — from the member's point of view the project should be
    indistinguishable from one that doesn't exist, per spec ("n'apparaît pas du
    tout"). The workspace owner is never restricted (only they can set
    restrictions, and doing so on themselves would be a self-lockout footgun)."""
    if membership.role == "OWNER":
        return

    restricted = (
        db.query(ProjectAccessRestriction)
        .filter(
            ProjectAccessRestriction.project_id == project_id,
            ProjectAccessRestriction.workspace_member_id == membership.id,
        )
        .first()
    )
    if restricted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
