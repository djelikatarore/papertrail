import asyncio
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
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
from app.database import SessionLocal, get_db
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.models import Paper, TextBlock, VisualElement
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.services.chat_service import get_history_grouped_by_date, get_or_create_paper_session, save_exchange
from app.services.chunking_service import chunk_text
from app.services.embedding_service import average_embedding, cosine_similarity, get_embedding, get_paper_embedding_source
from app.services.keyword_service import extract_keywords
from app.services.llm_service import LlmError, call_vision_llm
from app.services.paper_type_service import detect_paper_type
from app.services.pdf_service import PdfExtractionError, extract_text, extract_title
from app.services.qa_service import generate_grounded_answer, retrieve_relevant_chunks_pgvector
from app.services.summary_service import generate_summary
from app.services.visual_extraction_service import extract_visual_elements
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member, require_project_access

router = APIRouter(prefix="/papers", tags=["papers"])

VISION_CONCURRENCY_LIMIT = 3

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
    visual_elements_total: int | None
    visual_elements_processed: int | None
    visual_elements: list[VisualElementResponse] = []

    class Config:
        from_attributes = True


@router.post("/upload", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: int = Form(...),
    project_id: int | None = Form(None),
    new_project_name: str | None = Form(None),
    new_project_topic: str | None = Form(None),
    review_type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns as soon as the file is validated and saved to disk (status=PROCESSING)
    — text extraction, chunking, summary/keywords/paper-type, embeddings, and visual
    element description all run afterward in a background task (see
    _process_paper_background), so the client doesn't wait for the full AI pipeline.
    Poll GET /papers/{id} to see status progress to READY (or ERROR)."""
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

    background_tasks.add_task(_process_paper_background, paper.id, file_path, project.id)

    return paper


def _paper_still_exists(db: Session, paper_id: int) -> bool:
    """Re-checks the actual DB state (not the session's identity map) — used to
    detect a paper deleted by a concurrent request while this background task
    was mid-flight (e.g. still waiting on an LLM call)."""
    return db.query(Paper.id).filter(Paper.id == paper_id).first() is not None


async def _process_paper_background(paper_id: int, file_path: str, project_id: int) -> None:
    """Runs after the upload response has already been sent to the client (FastAPI
    BackgroundTasks execute post-response). Opens its own DB session — the
    request-scoped one injected via Depends(get_db) is already closed by the time
    this runs. Guarantees the paper never stays stuck on PROCESSING: any exception
    that escapes the per-step guards below is caught by the outer try/except,
    which marks the paper ERROR with a clear message rather than leaving it
    silently unfinished."""
    db = SessionLocal()
    try:
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            safe_log(f"[paper_router] Background processing: paper {paper_id} no longer exists, skipping")
            return
        project = db.query(Project).filter(Project.id == project_id).first()

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
                    chunk_embedding = get_embedding(chunk_body)
                    text_block.embedding = json.dumps(chunk_embedding)
                    # Dual-write for the pgvector migration (Ask AI reads this
                    # column now — see retrieve_relevant_chunks_pgvector).
                    text_block.embedding_vector = chunk_embedding
                except Exception as exc:
                    safe_log(f"[embedding_service] Failed to embed chunk '{section_reference}' for paper {paper.id}: {exc}")
                db.add(text_block)

            # Summary, keywords, and paper-type detection are three independent LLM
            # calls over the same chunks — none depends on another's output, so
            # running them concurrently instead of one-after-another cuts this
            # part of the pipeline down to the slowest single call instead of the
            # sum of all three. return_exceptions=True keeps each call's failure
            # isolated (matches the original per-call try/except behavior) rather
            # than one failure cancelling the other two in-flight calls.
            summary_result, keywords_result, paper_type_result = await asyncio.gather(
                generate_summary(chunks),
                extract_keywords(chunks),
                detect_paper_type(chunks),
                return_exceptions=True,
            )

            if isinstance(summary_result, LlmError):
                safe_log(f"[summary_service] Failed to generate summary for paper {paper.id}: {summary_result}")
            elif isinstance(summary_result, BaseException):
                raise summary_result
            else:
                summary, flagged_fields = summary_result
                paper.contribution = summary["contribution"]
                paper.methodology = summary["methodology"]
                paper.key_results = summary["key_results"]
                paper.limitations = summary["limitations"]
                paper.summary_flagged_fields = ", ".join(flagged_fields) if flagged_fields else None

            if isinstance(keywords_result, LlmError):
                safe_log(f"[keyword_service] Failed to extract keywords for paper {paper.id}: {keywords_result}")
            elif isinstance(keywords_result, BaseException):
                raise keywords_result
            else:
                paper.keywords = ", ".join(keywords_result) if keywords_result else None

            if isinstance(paper_type_result, LlmError):
                safe_log(f"[paper_type_service] Failed to detect paper type for paper {paper.id}: {paper_type_result}")
            elif isinstance(paper_type_result, BaseException):
                raise paper_type_result
            else:
                paper.detected_paper_type, paper.content_warning = paper_type_result

            if not _paper_still_exists(db, paper_id):
                safe_log(f"[paper_router] Paper {paper_id} was deleted during background processing; stopping before saving embeddings/results")
                db.rollback()
                return

            try:
                embedding_source = get_paper_embedding_source(paper.raw_text, chunks)
                paper_embedding = get_embedding(embedding_source)
                paper.embedding = json.dumps(paper_embedding)
                # Dual-write for the pgvector migration (Similar Papers reads this
                # column now — see get_project_similarity). `embedding` above
                # remains the source of truth for every other feature until they
                # migrate too.
                paper.embedding_vector = paper_embedding

                if project and project.topic_embedding:
                    topic_vector = json.loads(project.topic_embedding)
                    similarity = cosine_similarity(paper_embedding, topic_vector)
                    paper.topic_similarity_score = similarity
                    paper.is_off_topic = similarity < OFF_TOPIC_SIMILARITY_THRESHOLD

                if project:
                    other_embeddings = [
                        json.loads(p.embedding)
                        for p in db.query(Paper).filter(Paper.project_id == project.id, Paper.embedding.isnot(None)).all()
                        if p.id != paper.id
                    ]
                    project.topic_embedding = json.dumps(average_embedding(other_embeddings + [paper_embedding]))
            except Exception as exc:
                safe_log(f"[embedding_service] Failed to generate embedding for paper {paper.id}: {exc}")

        if not _paper_still_exists(db, paper_id):
            safe_log(f"[paper_router] Paper {paper_id} was deleted during background processing; stopping before visual element extraction")
            db.rollback()
            return

        try:
            os.makedirs(VISUAL_ELEMENTS_DIR, exist_ok=True)
            visual_elements = []
            for index, (page_number, image_bytes, ext) in enumerate(extract_visual_elements(file_path)):
                image_filename = f"{paper.id}_{page_number}_{index}.{ext}"
                image_disk_path = os.path.join(VISUAL_ELEMENTS_DIR, image_filename)
                with open(image_disk_path, "wb") as f:
                    f.write(image_bytes)

                visual_elements.append(
                    VisualElement(
                        paper_id=paper.id,
                        element_type="image",
                        image_path=image_disk_path,
                        page_number=page_number,
                    )
                )

            if visual_elements:
                for ve in visual_elements:
                    db.add(ve)
                paper.visual_elements_total = len(visual_elements)
                paper.visual_elements_processed = 0
                db.commit()

                # One vision call per figure, all independent — but bounded to
                # VISION_CONCURRENCY_LIMIT at a time rather than all at once.
                # Firing every figure simultaneously (confirmed with a real
                # 83-figure paper) blows through Groq's per-minute token budget
                # for the vision model in one burst, so most calls fail instead
                # of just queuing — a small concurrency cap gets most of the
                # parallelization benefit for typical papers (a handful of
                # figures) while staying under the rate limit for image-heavy
                # ones. call_vision_llm's own rate-limit-aware retry (see
                # llm_service.py) handles the rest: no image is given up on,
                # it just may take a while for a very image-heavy paper.
                semaphore = asyncio.Semaphore(VISION_CONCURRENCY_LIMIT)

                async def _describe_and_track(ve: VisualElement) -> None:
                    async with semaphore:
                        try:
                            ve.ai_description = await call_vision_llm(VISUAL_DESCRIPTION_PROMPT, ve.image_path)
                        except LlmError as exc:
                            safe_log(f"[llm_service] Failed to describe image {ve.image_path}: {exc}")
                        paper.visual_elements_processed = (paper.visual_elements_processed or 0) + 1
                        db.commit()

                await asyncio.gather(*(_describe_and_track(ve) for ve in visual_elements))
        except Exception as exc:
            safe_log(f"[visual_extraction_service] Failed to extract visual elements for paper {paper.id}: {exc}")

        db.commit()
    except Exception as exc:
        safe_log(f"[paper_router] Background processing crashed unexpectedly for paper {paper_id}: {exc}")
        db.rollback()
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if paper:
                paper.status = "ERROR"
                paper.error_message = f"Processing failed unexpectedly: {exc}"
                db.commit()
        except Exception as inner_exc:
            safe_log(f"[paper_router] Failed to mark paper {paper_id} as ERROR after crash: {inner_exc}")
    finally:
        db.close()


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


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Single-paper detail view — same access control as every other paper
    endpoint (ask, download, chat-history)."""
    return _get_paper_with_access(paper_id, db, current_user)


def _delete_file_if_exists(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as exc:
            safe_log(f"[paper_router] Failed to delete file {path}: {exc}")


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Deletes a single paper and everything scoped to it: text_blocks,
    visual_elements (+ their image files on disk), this paper's chat session
    and messages, and the uploaded PDF file. Same cascade pattern and
    owner-only restriction as DELETE /projects/{id} and DELETE .../drafts/{id}.
    Drafts and project-level (comparative) chat history are untouched — neither
    has a direct foreign key to a single paper."""
    paper = _get_paper_with_access(paper_id, db, current_user)
    project = db.query(Project).filter(Project.id == paper.project_id).first()
    workspace = db.query(Workspace).filter(Workspace.id == project.workspace_id).first()

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete a paper",
        )

    visual_element_paths = [
        path for (path,) in db.query(VisualElement.image_path).filter(VisualElement.paper_id == paper_id).all()
    ]
    for path in visual_element_paths:
        _delete_file_if_exists(path)
    db.query(VisualElement).filter(VisualElement.paper_id == paper_id).delete(synchronize_session=False)
    db.query(TextBlock).filter(TextBlock.paper_id == paper_id).delete(synchronize_session=False)

    chat_session_ids = [
        sid for (sid,) in db.query(ChatSession.id).filter(ChatSession.paper_id == paper_id).all()
    ]
    if chat_session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(chat_session_ids)).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.id.in_(chat_session_ids)).delete(synchronize_session=False)

    _delete_file_if_exists(os.path.join(UPLOAD_DIR, f"{paper_id}.pdf"))

    db.delete(paper)
    db.commit()


@router.get("/{paper_id}/download")
def download_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the original uploaded PDF as an attachment. The file is stored on
    disk regardless of processing outcome (it's written before text extraction is
    attempted), so this works even for papers stuck in ERROR status."""
    paper = _get_paper_with_access(paper_id, db, current_user)

    file_path = os.path.join(UPLOAD_DIR, f"{paper_id}.pdf")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original PDF file not found on disk")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=paper.filename or f"{paper_id}.pdf",
    )


@router.get("/{paper_id}/visual-elements/{visual_element_id}/image")
def download_visual_element_image(
    paper_id: int,
    visual_element_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serves the actual image bytes for a figure extracted at upload time.
    VisualElement only ever stored a server-side disk path (image_path) — there
    was no way for a client to actually fetch the image itself."""
    _get_paper_with_access(paper_id, db, current_user)

    visual_element = (
        db.query(VisualElement)
        .filter(VisualElement.id == visual_element_id, VisualElement.paper_id == paper_id)
        .first()
    )
    if not visual_element:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visual element not found")

    if not visual_element.image_path or not os.path.exists(visual_element.image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found on disk")

    ext = visual_element.image_path.rsplit(".", 1)[-1].lower()
    media_type = "image/png" if ext == "png" else "image/jpeg"
    return FileResponse(visual_element.image_path, media_type=media_type)


@router.post("/{paper_id}/ask", response_model=AskQuestionResponse)
async def ask_question(
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

    if paper.status == "PROCESSING":
        response = AskQuestionResponse(
            answer="This paper is still being processed. Please try again in a moment.",
            cited_section=None,
            refused=True,
        )
        session = get_or_create_paper_session(paper_id, paper.title or paper.filename, db)
        save_exchange(session.id, payload.question, response.answer, db)
        return response

    if paper.status == "ERROR":
        response = AskQuestionResponse(
            answer=f"This paper failed to process and has no content to answer questions from ({paper.error_message or 'unknown error'}).",
            cited_section=None,
            refused=True,
        )
        session = get_or_create_paper_session(paper_id, paper.title or paper.filename, db)
        save_exchange(session.id, payload.question, response.answer, db)
        return response

    chunks = retrieve_relevant_chunks_pgvector(payload.question, paper_id, db)
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
            answer, cited_section, refused = await generate_grounded_answer(payload.question, chunks)
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
