from sqlalchemy import Column, Integer, String, ForeignKey
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

    created_at = Column(
        String,
        nullable=True
    )

    updated_at = Column(
        String,
        nullable=True
    )