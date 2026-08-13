from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, Float, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

EMBEDDING_VECTOR_DIMENSIONS = 384


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

    # Non-fatal: set when the paper still reaches READY but one or more AI
    # steps (summary/keywords/paper-type detection, figure descriptions)
    # degraded gracefully after exhausting Groq retries — see
    # _build_processing_warning in paper_router.py. Distinct from
    # error_message, which is only ever set alongside status="ERROR".
    processing_warning = Column(String, nullable=True)

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

    # pgvector migration (Phase A, infrastructure only): parallel column,
    # backfilled from `embedding` but not yet read or written by any
    # feature — every read/write path still goes through `embedding` above.
    embedding_vector = Column(
        Vector(EMBEDDING_VECTOR_DIMENSIONS),
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

    visual_elements_total = Column(
        Integer,
        nullable=True
    )

    visual_elements_processed = Column(
        Integer,
        nullable=True
    )

    # Real academic citation count, looked up by title — None means either the
    # background lookup hasn't run yet or found no confident match, not "zero
    # citations". See citation_service.py.
    citation_count = Column(
        Integer,
        nullable=True
    )

    # Which provider citation_count actually came from: "semantic_scholar" or
    # "crossref", or None if never looked up. Exists specifically so a later
    # re-check (scripts/backfill_citation_counts.py) can tell a trustworthy
    # Semantic Scholar count apart from a less reliable CrossRef one and never
    # let the latter silently overwrite the former — see
    # citation_service.should_replace_citation.
    citation_count_source = Column(
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

    # pgvector migration (Phase A, infrastructure only): see Paper.embedding_vector.
    embedding_vector = Column(
        Vector(EMBEDDING_VECTOR_DIMENSIONS),
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

    # Best-effort "Figure 3"/"Table 2" caption label, matched by proximity to
    # the image on its page (see visual_extraction_service._find_figure_reference).
    # None when no matching caption was found nearby.
    figure_reference = Column(
        String,
        nullable=True
    )

    paper = relationship(
        "Paper",
        back_populates="visual_elements"
    )