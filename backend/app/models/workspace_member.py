from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    role = Column(
        String,
        nullable=False,
        default="MEMBER"
    )

    joined_at = Column(
        String,
        nullable=True
    )