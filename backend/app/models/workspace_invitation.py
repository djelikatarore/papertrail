from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from app.database import Base


class WorkspaceInvitation(Base):
    """A pending email invitation for someone who doesn't have a PaperTrail
    account yet — see workspace_router.invite_user_by_email. Distinct from
    Workspace.invite_link_token (a single, generic, reusable link that
    already assumes the visitor has an account): this is per-email, consumed
    once at signup (auth_router.signup, via invite_token), and locked to the
    exact email it was sent to — a signup with a different email cannot use
    it. No expiry, matching the generic invite link's own lack of one."""

    __tablename__ = "workspace_invitations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_workspace_invitation_workspace_email"),
    )

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    email = Column(String, nullable=False, index=True)

    token = Column(String, unique=True, nullable=False, index=True)

    created_at = Column(String, nullable=True)

    accepted_at = Column(String, nullable=True)
