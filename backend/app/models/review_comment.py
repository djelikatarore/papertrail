from sqlalchemy import Column, Integer, String, ForeignKey
from app.database import Base


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)

    draft_document_id = Column(
        Integer,
        ForeignKey("draft_documents.id"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    content = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        default="OPEN"
    )

    created_at = Column(
        String,
        nullable=True
    )