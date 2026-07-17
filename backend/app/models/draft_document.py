from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class DraftDocument(Base):
    __tablename__ = "draft_documents"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False
    )

    title = Column(
        String,
        nullable=False
    )

    content = Column(
        String,
        nullable=True
    )

    document_type = Column(
        String,
        nullable=False
    )

    version = Column(
        Integer,
        default=1
    )

    status = Column(
        String,
        default="DRAFT"
    )

    project = relationship(
        "Project"
    )

    review_comments = relationship(
        "ReviewComment",
        back_populates="draft_document"
    )