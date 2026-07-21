import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.settings import MAX_PAPERS_PER_PROJECT, MAX_UPLOAD_SIZE_BYTES, UPLOAD_DIR, VALID_REVIEW_TYPES
from app.database import get_db
from app.models.models import Paper
from app.models.project import Project
from app.models.user import User
from app.services.pdf_service import PdfExtractionError, extract_text
from app.utils.auth_dependency import get_current_user
from app.utils.workspace_access import get_workspace_or_404, require_member

router = APIRouter(prefix="/papers", tags=["papers"])


class PaperResponse(BaseModel):
    id: int
    project_id: int | None
    filename: str
    status: str
    review_type: str | None
    file_size_bytes: int | None
    page_count: int | None
    upload_date: str | None
    uploaded_by: int | None
    raw_text: str | None
    error_message: str | None

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

    if membership.role != "OWNER" and membership.upload_credits <= 0:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No upload credits remaining")

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

    if membership.role != "OWNER":
        membership.upload_credits -= 1

    try:
        raw_text, page_count = extract_text(file_path)
        paper.raw_text = raw_text
        paper.page_count = page_count
        paper.status = "READY"
        paper.error_message = None
    except PdfExtractionError as exc:
        paper.status = "ERROR"
        paper.error_message = str(exc)

    db.commit()
    db.refresh(paper)

    return paper
