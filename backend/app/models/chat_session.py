from sqlalchemy import Column, Integer, String, ForeignKey
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