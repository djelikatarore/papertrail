from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class ProjectAccessRestriction(Base):
    """Presence of a row means the given workspace member is DENIED access to the
    given project. Absence means access is granted — the default is that every
    workspace member can see every project, so this table only stores exceptions
    rather than requiring a grant row to be backfilled for every member/project pair."""

    __tablename__ = "project_access_restrictions"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    workspace_member_id = Column(
        Integer,
        ForeignKey("workspace_members.id"),
        nullable=False
    )

    created_at = Column(
        String,
        nullable=True
    )
