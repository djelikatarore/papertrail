from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.models import EMBEDDING_VECTOR_DIMENSIONS


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    topic = Column(String, nullable=False)

    topic_embedding = Column(String, nullable=True)

    # pgvector migration (Phase A, infrastructure only): see Paper.embedding_vector.
    topic_embedding_vector = Column(
        Vector(EMBEDDING_VECTOR_DIMENSIONS),
        nullable=True
    )

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