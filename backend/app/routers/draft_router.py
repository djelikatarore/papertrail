import os
import tempfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.settings import DRAFT_PDF_DIR, VALID_DOCUMENT_TYPES
from app.database import get_db
from app.models.draft_document import DraftDocument
from app.models.models import Paper
from app.models.project import Project
from app.models.review_comment import ReviewComment
from app.models.user import User
from app.services.draft_generation_service import generate_draft_content
from app.services.draft_pdf_service import generate_pdf_from_text
from app.services.feedback_service import generate_review_suggestions
from app.services.llm_service import LlmError
from app.services.pdf_service import PdfExtractionError, extract_text
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member, require_project_access

router = APIRouter(prefix="/workspaces/{workspace_id}/projects/{project_id}/drafts", tags=["drafts"])


class CreateDraftRequest(BaseModel):
    title: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    content: str | None = None


class UpdateDraftRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    content: str | None = None
    document_type: str | None = Field(default=None, min_length=1)
    status: str | None = None


class DraftResponse(BaseModel):
    id: int
    project_id: int
    title: str
    content: str | None
    document_type: str
    version: int
    status: str
    created_at: str | None
    updated_at: str | None
    pdf_path: str | None

    class Config:
        from_attributes = True


class CreateReviewCommentRequest(BaseModel):
    content: str = Field(min_length=1)


class UpdateReviewCommentRequest(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    status: str | None = None


class ReviewCommentResponse(BaseModel):
    id: int
    draft_document_id: int
    user_id: int
    content: str
    status: str
    created_at: str | None

    class Config:
        from_attributes = True


class GenerateDraftRequest(BaseModel):
    document_type: str = Field(min_length=1)
    paper_ids: list[int] = Field(min_length=1)


class GenerateDraftResponse(BaseModel):
    draft: DraftResponse | None
    generated: bool
    error: str | None = None


def _validate_document_type(document_type: str) -> None:
    if document_type not in VALID_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"document_type must be one of: {', '.join(sorted(VALID_DOCUMENT_TYPES))}",
        )


def _get_project_or_404(workspace_id: int, project_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.workspace_id == workspace_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _get_draft_or_404(project_id: int, draft_id: int, db: Session) -> DraftDocument:
    draft = (
        db.query(DraftDocument)
        .filter(DraftDocument.id == draft_id, DraftDocument.project_id == project_id)
        .first()
    )
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return draft


def _get_comment_or_404(draft_id: int, comment_id: int, db: Session) -> ReviewComment:
    comment = (
        db.query(ReviewComment)
        .filter(ReviewComment.id == comment_id, ReviewComment.draft_document_id == draft_id)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


def _regenerate_draft_pdf(draft: DraftDocument) -> None:
    """Auto-converts a plain-text draft (no PDF upload) into a basic PDF with a
    footer marking it as generated, so it can be stored/served like any other
    file. Best-effort: a PDF generation failure shouldn't block saving the draft
    itself, since the text content is the source of truth."""
    if not draft.content:
        return
    try:
        os.makedirs(DRAFT_PDF_DIR, exist_ok=True)
        pdf_path = os.path.join(DRAFT_PDF_DIR, f"{draft.id}.pdf")
        generate_pdf_from_text(draft.title, draft.content, pdf_path)
        draft.pdf_path = pdf_path
    except Exception as exc:
        safe_log(f"[draft_pdf_service] Failed to generate PDF for draft {draft.id}: {exc}")


@router.post("", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
def create_draft(
    workspace_id: int,
    project_id: int,
    payload: CreateDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _validate_document_type(payload.document_type)

    now = datetime.now(timezone.utc).isoformat()
    draft = DraftDocument(
        project_id=project_id,
        title=payload.title,
        document_type=payload.document_type,
        content=payload.content,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    _regenerate_draft_pdf(draft)
    db.commit()
    db.refresh(draft)

    return draft


@router.get("", response_model=list[DraftResponse])
def list_drafts(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    return db.query(DraftDocument).filter(DraftDocument.project_id == project_id).all()


@router.get("/{draft_id}", response_model=DraftResponse)
def get_draft(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    return _get_draft_or_404(project_id, draft_id, db)


@router.get("/{draft_id}/download")
def download_draft(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the auto-generated PDF for this draft as an attachment, mirroring
    GET /papers/{paper_id}/download. pdf_path is only ever a server-side disk
    path (set by _regenerate_draft_pdf) — there was no way for a client to
    actually fetch the file itself before this endpoint."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    draft = _get_draft_or_404(project_id, draft_id, db)

    if not draft.pdf_path or not os.path.exists(draft.pdf_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found on disk")

    return FileResponse(
        draft.pdf_path,
        media_type="application/pdf",
        filename=f"{draft.title}.pdf",
    )


@router.put("/{draft_id}", response_model=DraftResponse)
def update_draft(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    payload: UpdateDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Content edits bump the version counter (no version history table — by
    design, confirmed with the user)."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    draft = _get_draft_or_404(project_id, draft_id, db)

    if payload.document_type is not None:
        _validate_document_type(payload.document_type)

    updates = payload.model_dump(exclude_unset=True)
    content_changed = "content" in updates and updates["content"] != draft.content
    if content_changed:
        draft.version = (draft.version or 1) + 1

    for field, value in updates.items():
        setattr(draft, field, value)
    draft.updated_at = datetime.now(timezone.utc).isoformat()

    if content_changed or "title" in updates:
        _regenerate_draft_pdf(draft)

    db.commit()
    db.refresh(draft)

    return draft


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    draft = _get_draft_or_404(project_id, draft_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete a draft",
        )

    db.query(ReviewComment).filter(ReviewComment.draft_document_id == draft_id).delete()
    db.delete(draft)
    db.commit()


@router.post("/{draft_id}/comments", response_model=ReviewCommentResponse, status_code=status.HTTP_201_CREATED)
def create_review_comment(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    payload: CreateReviewCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _get_draft_or_404(project_id, draft_id, db)

    comment = ReviewComment(
        draft_document_id=draft_id,
        user_id=current_user.id,
        content=payload.content,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return comment


@router.get("/{draft_id}/comments", response_model=list[ReviewCommentResponse])
def list_review_comments(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _get_draft_or_404(project_id, draft_id, db)

    return db.query(ReviewComment).filter(ReviewComment.draft_document_id == draft_id).all()


@router.put("/{draft_id}/comments/{comment_id}", response_model=ReviewCommentResponse)
def update_review_comment(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    comment_id: int,
    payload: UpdateReviewCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Editing content is restricted to the comment's author; changing status
    (e.g. resolving) is allowed for any member, since resolution is a shared
    reviewing decision rather than ownership of the comment text itself. Open
    question to confirm with the user."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _get_draft_or_404(project_id, draft_id, db)
    comment = _get_comment_or_404(draft_id, comment_id, db)

    updates = payload.model_dump(exclude_unset=True)
    if "content" in updates and comment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment's author can edit its content",
        )

    for field, value in updates.items():
        setattr(comment, field, value)

    db.commit()
    db.refresh(comment)

    return comment


@router.delete("/{draft_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review_comment(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _get_draft_or_404(project_id, draft_id, db)
    comment = _get_comment_or_404(draft_id, comment_id, db)

    if comment.user_id != current_user.id and workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the comment's author or the workspace owner can delete it",
        )

    db.delete(comment)
    db.commit()


@router.post("/generate", response_model=GenerateDraftResponse)
async def generate_draft(
    workspace_id: int,
    project_id: int,
    payload: GenerateDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates a structured draft from the selected papers' existing summaries
    (contribution/methodology/key_results/limitations, already anti-hallucination
    verified at upload time), rather than resending raw chunk text — keeps the
    prompt small across multiple papers and stays well under Groq's per-minute
    token limit. Every claim about a specific paper must cite it; a citation
    referencing a paper outside the selection discards the whole draft rather
    than persisting an unverifiable one."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    _validate_document_type(payload.document_type)

    papers = db.query(Paper).filter(Paper.id.in_(payload.paper_ids), Paper.project_id == project_id).all()
    found_ids = {p.id for p in papers}
    missing_ids = set(payload.paper_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper(s) not found in this project: {sorted(missing_ids)}",
        )

    not_ready = {p.id: p.status for p in papers if p.status != "READY"}
    if not_ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Paper(s) not ready for draft generation yet: {not_ready}",
        )

    papers_for_prompt = [
        {
            "title": paper.title or paper.filename,
            "contribution": paper.contribution,
            "methodology": paper.methodology,
            "key_results": paper.key_results,
            "limitations": paper.limitations,
            "keywords": paper.keywords,
        }
        for paper in papers
    ]

    try:
        content, generated, error = await generate_draft_content(payload.document_type, papers_for_prompt)
    except LlmError as exc:
        safe_log(f"[draft_generation_service] Failed to generate draft for project {project_id}: {exc}")
        return GenerateDraftResponse(draft=None, generated=False, error="The draft generation service is temporarily unavailable.")

    if not generated:
        return GenerateDraftResponse(draft=None, generated=False, error=error)

    now = datetime.now(timezone.utc).isoformat()
    label = payload.document_type.replace("_", " ").title()
    draft = DraftDocument(
        project_id=project_id,
        title=f"{label} - {', '.join(p['title'] for p in papers_for_prompt)}"[:255],
        document_type=payload.document_type,
        content=content,
        created_at=now,
        updated_at=now,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    _regenerate_draft_pdf(draft)
    db.commit()
    db.refresh(draft)

    return GenerateDraftResponse(draft=draft, generated=True, error=None)


class GenerateReviewSuggestionsResponse(BaseModel):
    comments: list[ReviewCommentResponse]
    discarded_count: int


@router.post("/{draft_id}/feedback", response_model=GenerateReviewSuggestionsResponse, status_code=status.HTTP_201_CREATED)
async def submit_draft_feedback(
    workspace_id: int,
    project_id: int,
    draft_id: int,
    feedback_text: str | None = Form(default=None),
    feedback_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accepts reviewer feedback (pasted text OR an uploaded file — exactly
    one) about an existing draft, and turns it into correction suggestions
    saved as ReviewComments. Every suggestion must quote a real snippet of
    the submitted feedback as justification; a suggestion whose quote
    doesn't literally appear in the feedback is discarded rather than saved
    (reported via discarded_count), same anti-hallucination principle used
    elsewhere in the app. Suggestions are attributed to the user who
    submitted the feedback (no dedicated "AI" user account exists in the
    schema). Uploaded files: plain UTF-8 .txt, or .pdf (text extracted via
    the same pdf_service used for paper uploads, including its OCR
    fallback for scanned pages) — Word/.docx is not supported (would need a
    new dependency; not added without a specific need for it)."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)
    draft = _get_draft_or_404(project_id, draft_id, db)

    if bool(feedback_text) == bool(feedback_file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of feedback_text or feedback_file",
        )

    if feedback_file:
        raw_bytes = await feedback_file.read()
        filename = (feedback_file.filename or "").lower()

        if filename.endswith(".pdf"):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(raw_bytes)
                tmp_path = tmp.name
            try:
                feedback_text, _ = extract_text(tmp_path)
            except PdfExtractionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Could not extract text from this PDF: {exc}",
                )
            finally:
                os.remove(tmp_path)
        else:
            try:
                feedback_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="feedback_file must be a plain UTF-8 .txt file or a .pdf file",
                )

    if not feedback_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback text cannot be empty")

    if not draft.content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This draft has no content to review")

    try:
        suggestions, discarded_count = await generate_review_suggestions(draft.content, feedback_text)
    except LlmError as exc:
        safe_log(f"[feedback_service] Failed to generate review suggestions for draft {draft_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The feedback review service is temporarily unavailable.",
        )

    now = datetime.now(timezone.utc).isoformat()
    comments = [
        ReviewComment(draft_document_id=draft_id, user_id=current_user.id, content=suggestion, created_at=now)
        for suggestion in suggestions
    ]
    db.add_all(comments)
    db.commit()
    for comment in comments:
        db.refresh(comment)

    return GenerateReviewSuggestionsResponse(comments=comments, discarded_count=discarded_count)
