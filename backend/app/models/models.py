from sqlalchemy import Boolean, Column, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=True
    )

    uploaded_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    filename = Column(String, nullable=False)

    title = Column(String, nullable=True)

    upload_date = Column(String, nullable=True)

    page_count = Column(Integer, nullable=True)

    file_size_bytes = Column(Integer, nullable=True)

    raw_text = Column(String, nullable=True)

    error_message = Column(String, nullable=True)

    status = Column(
        String,
        default="PROCESSING"
    )

    read_status = Column(
        String,
        default="UNREAD"
    )

    review_type = Column(
        String,
        nullable=True
    )

    contribution = Column(
        String,
        nullable=True
    )

    methodology = Column(
        String,
        nullable=True
    )

    key_results = Column(
        String,
        nullable=True
    )

    limitations = Column(
        String,
        nullable=True
    )

    summary_flagged_fields = Column(
        String,
        nullable=True
    )

    keywords = Column(
        String,
        nullable=True
    )

    embedding = Column(
        String,
        nullable=True
    )

    is_off_topic = Column(
        Boolean,
        nullable=False,
        default=False
    )

    topic_similarity_score = Column(
        Float,
        nullable=True
    )

    detected_paper_type = Column(
        String,
        nullable=True
    )

    content_warning = Column(
        String,
        nullable=True
    )

    project = relationship(
        "Project",
        back_populates="papers"
    )

    text_blocks = relationship(
        "TextBlock",
        back_populates="paper"
    )

    visual_elements = relationship(
        "VisualElement",
        back_populates="paper"
    )


class TextBlock(Base):
    __tablename__ = "text_blocks"

    id = Column(Integer, primary_key=True, index=True)

    paper_id = Column(
        Integer,
        ForeignKey("papers.id")
    )

    text = Column(
        String,
        nullable=False
    )

    section_reference = Column(
        String,
        nullable=True
    )

    embedding = Column(
        String,
        nullable=True
    )

    paper = relationship(
        "Paper",
        back_populates="text_blocks"
    )


class VisualElement(Base):
    __tablename__ = "visual_elements"

    id = Column(Integer, primary_key=True, index=True)

    paper_id = Column(
        Integer,
        ForeignKey("papers.id")
    )

    element_type = Column(
        String,
        nullable=True
    )

    content = Column(
        String,
        nullable=True
    )

    image_path = Column(
        String,
        nullable=True
    )

    page_number = Column(
        Integer,
        nullable=True
    )

    ai_description = Column(
        String,
        nullable=True
    )

    paper = relationship(
        "Paper",
        back_populates="visual_elements"
    )