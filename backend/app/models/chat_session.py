from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=True
    )

    paper_id = Column(
        Integer,
        ForeignKey("papers.id"),
        nullable=True
    )

    created_at = Column(
        String,
        nullable=True
    )

    project = relationship(
        "Project",
        back_populates="chat_sessions"
    )

    messages = relationship(
        "ChatMessage",
        back_populates="chat_session"
    )