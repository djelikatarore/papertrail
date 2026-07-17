from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    description = Column(String, nullable=True)

    created_at = Column(String, nullable=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    members = relationship(
        "WorkspaceMember",
        back_populates="workspace"
    )

    projects = relationship(
        "Project",
        back_populates="workspace"
    )