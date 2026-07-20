from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    topic = Column(String, nullable=False)

    topic_embedding = Column(String, nullable=True)

    description = Column(String, nullable=True)

    status = Column(
        String,
        nullable=False,
        default="ACTIVE"
    )

    workspace_id = Column(
        Integer,
        ForeignKey("workspaces.id"),
        nullable=False
    )

    created_at = Column(
        String,
        nullable=True
    )

    workspace = relationship(
        "Workspace",
        back_populates="projects"
    )

    papers = relationship(
        "Paper",
        back_populates="project"
    )

    chat_sessions = relationship(
        "ChatSession",
        back_populates="project"
    )