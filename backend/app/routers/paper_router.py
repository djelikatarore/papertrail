import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.settings import (
    MAX_PAPERS_PER_PROJECT,
    MAX_UPLOAD_SIZE_BYTES,
    OFF_TOPIC_SIMILARITY_THRESHOLD,
    QA_OUT_OF_SCOPE_THRESHOLD,
    UPLOAD_DIR,
    VALID_REVIEW_TYPES,
    VISUAL_ELEMENTS_DIR,
)
from app.database import get_db
from app.models.chat_session import ChatSession
from app.models.models import Paper, TextBlock, VisualElement
from app.models.project import Project
from app.models.user import User
from app.services.chat_service import get_history_grouped_by_date, get_or_create_paper_session, save_exchange
from app.services.chunking_service import chunk_text
from app.services.embedding_service import average_embedding, cosine_similarity, get_embedding, get_paper_embedding_source
from app.services.faiss_service import add_paper_embedding
from app.services.keyword_service import extract_keywords
from app.services.llm_service import LlmError, call_vision_llm
from app.services.paper_type_service import detect_paper_type
from app.services.pdf_service import PdfExtractionError, extract_text, extract_title
from app.services.qa_service import generate_grounded_answer, retrieve_relevant_chunks
from app.services.summary_service import generate_summary
from app.services.visual_extraction_service import extract_visual_elements
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member, require_project_access

router = APIRouter(prefix="/papers", tags=["papers"])

VISUAL_DESCRIPTION_PROMPT = (
    "Describe this figure from an academic paper in 1-2 concise sentences. "
    "Focus on what it shows (e.g., architecture diagram, chart, plot, photo) and its key content."
)


class VisualElementResponse(BaseModel):
    id: int
    page_number: int | None
    image_path: str | None
    ai_description: str | None

    class Config:
        from_attributes = True


class AskQuestionRequest(BaseModel):
    question: str


class AskQuestionResponse(BaseModel):
    answer: str | None
    cited_section: str | None
    refused: bool


class PaperResponse(BaseModel):
    id: int
    project_id: int | None
    filename: str
    title: str | None
    status: str
    review_type: str | None
    file_size_bytes: int | None
    page_count: int | None
    upload_date: str | None
    uploaded_by: int | None
    raw_text: str | None
    error_message: str | None
    contribution: str | None
    methodology: str | None
    key_results: str | None
    limitations: str | None
    summary_flagged_fields: str | None
    keywords: str | None
    is_off_topic: bool
    topic_similarity_score: float | None
    detected_paper_type: str | None
    content_warning: str | None
    visual_elements: list[VisualElementResponse] = []

    class Config:
        from_attributes = True


@router.post("/upload", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile = File(...),
    workspace_id: int = Form(...),
    project_id: int | None = Form(None),
    new_project_name: str | None = Form(None),
    new_project_topic: str | None = Form(None),
    review_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if review_type not in VALID_REVIEW_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"review_type must be one of: {', '.join(sorted(VALID_REVIEW_TYPES))}",
        )

    if bool(project_id) == bool(new_project_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of project_id or new_project_name",
        )

    if new_project_name and not new_project_topic:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_project_topic is required when creating a new project",
        )

    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)

    if project_id:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.workspace_id == workspace_id)
            .first()
        )
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found in this workspace")
        require_project_access(project_id, membership, db)
    else:
        project = Project(
            workspace_id=workspace_id,
            title=new_project_name,
            topic=new_project_topic,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are allowed")

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only PDF files are allowed")

    content = await file.read()

    # Extension and Content-Type are both client-supplied and trivially spoofable
    # (e.g. renaming a .txt to .pdf). The %PDF- signature is the actual file format
    # marker and is what real validation must rely on.
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File does not appear to be a valid PDF (missing %PDF- signature)",
        )

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 25MB size limit",
        )

    paper_count = db.query(Paper).filter(Paper.project_id == project.id).count()
    if paper_count >= MAX_PAPERS_PER_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This project has reached the maximum of {MAX_PAPERS_PER_PROJECT} papers",
        )

    paper = Paper(
        project_id=project.id,
        uploaded_by=current_user.id,
        filename=file.filename,
        upload_date=datetime.now(timezone.utc).isoformat(),
        file_size_bytes=len(content),
        status="PROCESSING",
        review_type=review_type,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{paper.id}.pdf")
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        raw_text, page_count = extract_text(file_path)
        paper.raw_text = raw_text
        paper.page_count = page_count
        paper.title = extract_title(file_path, raw_text)
        paper.status = "READY"
        paper.error_message = None
    except PdfExtractionError as exc:
        paper.status = "ERROR"
        paper.error_message = str(exc)

    if paper.status == "READY":
        chunks = chunk_text(paper.raw_text)
        for section_reference, chunk_body in chunks:
            text_block = TextBlock(paper_id=paper.id, text=chunk_body, section_reference=section_reference)
            try:
                text_block.embedding = json.dumps(get_embedding(chunk_body))
            except Exception as exc:
                safe_log(f"[embedding_service] Failed to embed chunk '{section_reference}' for paper {paper.id}: {exc}")
            db.add(text_block)

        try:
            summary, flagged_fields = generate_summary(chunks)
            paper.contribution = summary["contribution"]
            paper.methodology = summary["methodology"]
            paper.key_results = summary["key_results"]
            paper.limitations = summary["limitations"]
            paper.summary_flagged_fields = ", ".join(flagged_fields) if flagged_fields else None
        except LlmError as exc:
            safe_log(f"[summary_service] Failed to generate summary for paper {paper.id}: {exc}")

        try:
            keywords = extract_keywords(chunks)
            paper.keywords = ", ".join(keywords) if keywords else None
        except LlmError as exc:
            safe_log(f"[keyword_service] Failed to extract keywords for paper {paper.id}: {exc}")

        try:
            paper.detected_paper_type, paper.content_warning = detect_paper_type(chunks)
        except LlmError as exc:
            safe_log(f"[paper_type_service] Failed to detect paper type for paper {paper.id}: {exc}")

        try:
            embedding_source = get_paper_embedding_source(paper.raw_text, chunks)
            paper_embedding = get_embedding(embedding_source)
            paper.embedding = json.dumps(paper_embedding)

            if project.topic_embedding:
                topic_vector = json.loads(project.topic_embedding)
                similarity = cosine_similarity(paper_embedding, topic_vector)
                paper.topic_similarity_score = similarity
                paper.is_off_topic = similarity < OFF_TOPIC_SIMILARITY_THRESHOLD

            other_embeddings = [
                json.loads(p.embedding)
                for p in db.query(Paper).filter(Paper.project_id == project.id, Paper.embedding.isnot(None)).all()
                if p.id != paper.id
            ]
            project.topic_embedding = json.dumps(average_embedding(other_embeddings + [paper_embedding]))

            add_paper_embedding(paper.id, paper_embedding)
        except Exception as exc:
            safe_log(f"[embedding_service] Failed to generate embedding for paper {paper.id}: {exc}")

    try:
        os.makedirs(VISUAL_ELEMENTS_DIR, exist_ok=True)
        for index, (page_number, image_bytes, ext) in enumerate(extract_visual_elements(file_path)):
            image_filename = f"{paper.id}_{page_number}_{index}.{ext}"
            image_disk_path = os.path.join(VISUAL_ELEMENTS_DIR, image_filename)
            with open(image_disk_path, "wb") as f:
                f.write(image_bytes)

            visual_element = VisualElement(
                paper_id=paper.id,
                element_type="image",
                image_path=image_disk_path,
                page_number=page_number,
            )

            try:
                visual_element.ai_description = call_vision_llm(VISUAL_DESCRIPTION_PROMPT, image_disk_path)
            except LlmError as exc:
                safe_log(f"[llm_service] Failed to describe image {image_disk_path}: {exc}")

            db.add(visual_element)
    except Exception as exc:
        safe_log(f"[visual_extraction_service] Failed to extract visual elements for paper {paper.id}: {exc}")

    db.commit()
    db.refresh(paper)

    return paper


def _get_paper_with_access(paper_id: int, db: Session, current_user: User) -> Paper:
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    project = db.query(Project).filter(Project.id == paper.project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper's project not found")

    membership = require_member(project.workspace_id, current_user.id, db)
    require_project_access(project.id, membership, db)
    return paper


@router.post("/{paper_id}/ask", response_model=AskQuestionResponse)
def ask_question(
    paper_id: int,
    payload: AskQuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sprint 6 Tasks 2-4+8: retrieves the paper's top-3 most relevant chunks for the
    question (cosine similarity against precomputed TextBlock embeddings). If the
    best chunk match is below QA_OUT_OF_SCOPE_THRESHOLD, the question is refused
    without ever calling the LLM (Task 4). Otherwise the LLM answers grounded in
    those chunks with a verifiable section citation (Task 3). Every exchange
    (including refusals) is saved to this paper's chat history (Task 8)."""
    paper = _get_paper_with_access(paper_id, db, current_user)

    chunks = retrieve_relevant_chunks(payload.question, paper_id, db)
    if not chunks:
        response = AskQuestionResponse(
            answer="This paper has no processed content to answer questions from yet.",
            cited_section=None,
            refused=True,
        )
    elif chunks[0]["score"] < QA_OUT_OF_SCOPE_THRESHOLD:
        response = AskQuestionResponse(
            answer="This question doesn't appear to be answerable from this paper's content.",
            cited_section=None,
            refused=True,
        )
    else:
        try:
            answer, cited_section, refused = generate_grounded_answer(payload.question, chunks)
        except LlmError as exc:
            safe_log(f"[qa_service] Failed to generate answer for paper {paper_id}: {exc}")
            answer, cited_section, refused = "The question answering service is temporarily unavailable.", None, True
        response = AskQuestionResponse(answer=answer, cited_section=cited_section, refused=refused)

    session = get_or_create_paper_session(paper_id, paper.title or paper.filename, db)
    save_exchange(session.id, payload.question, response.answer, db)

    return response


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str | None


class ChatHistoryDateGroup(BaseModel):
    date: str
    messages: list[ChatMessageResponse]


@router.get("/{paper_id}/chat-history", response_model=list[ChatHistoryDateGroup])
def get_paper_chat_history(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sprint 6 Task 8: returns this paper's Q&A history, grouped by date."""
    _get_paper_with_access(paper_id, db, current_user)

    session = (
        db.query(ChatSession)
        .filter(ChatSession.paper_id == paper_id, ChatSession.project_id.is_(None))
        .first()
    )
    if not session:
        return []

    return get_history_grouped_by_date(session, db)
