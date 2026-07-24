import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.settings import OFF_TOPIC_SIMILARITY_THRESHOLD
from app.database import get_db
from app.models.models import Paper
from app.models.project import Project
from app.models.user import User
from app.services.arxiv_service import ArxivSearchError, search_arxiv
from app.services.embedding_service import cosine_similarity
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member

DUPLICATE_TITLE_SIMILARITY_THRESHOLD = 0.75

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str | None = None


class UpdateProjectRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    topic: str | None = Field(default=None, min_length=1)
    description: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: int
    workspace_id: int
    title: str
    topic: str
    description: str | None
    status: str
    created_at: str | None

    class Config:
        from_attributes = True


class SimilarPaperResponse(BaseModel):
    paper_id: int
    filename: str
    similarity: float


class PaperSimilarityResponse(BaseModel):
    paper_id: int
    filename: str
    similar_papers: list[SimilarPaperResponse]


class SuggestedPaperResponse(BaseModel):
    title: str
    authors: list[str]
    abstract: str
    pdf_link: str | None
    published_date: str


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _is_likely_duplicate(candidate_title: str, existing_papers: list[Paper]) -> bool:
    """Compares the arXiv candidate's title against each existing paper's extracted
    title (falling back to the filename for older papers uploaded before title
    extraction existed). A fuzzy ratio catches near-duplicates (e.g. a v2 arXiv
    revision with a slightly reworded title)."""
    normalized_candidate = _normalize_title(candidate_title)

    for paper in existing_papers:
        reference = paper.title or re.sub(r"\.pdf$", "", paper.filename, flags=re.IGNORECASE)
        normalized_reference = _normalize_title(reference)
        if SequenceMatcher(None, normalized_candidate, normalized_reference).ratio() >= DUPLICATE_TITLE_SIMILARITY_THRESHOLD:
            return True

    return False


class CitationGraphNode(BaseModel):
    paper_id: int
    title: str
    citation_count: int = 0


class CitationGraphLink(BaseModel):
    source: int
    target: int
    weight: float


class CitationGraphResponse(BaseModel):
    nodes: list[CitationGraphNode]
    links: list[CitationGraphLink]


def _get_project_or_404(workspace_id: int, project_id: int, db: Session) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.workspace_id == workspace_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    workspace_id: int,
    payload: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    project = Project(
        workspace_id=workspace_id,
        title=payload.title,
        topic=payload.topic,
        description=payload.description,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    return db.query(Project).filter(Project.workspace_id == workspace_id).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)

    return _get_project_or_404(workspace_id, project_id, db)


@router.get("/{project_id}/similarity", response_model=list[PaperSimilarityResponse])
def get_project_similarity(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """For each paper in the project that has an embedding, returns the other papers
    in the same project ranked by cosine similarity (descending). Computed directly
    from stored embeddings rather than via the FAISS index, since FAISS is indexed
    globally across all projects and the per-project paper cap (8) makes an O(n^2)
    comparison trivial and naturally scoped."""
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)

    papers = db.query(Paper).filter(Paper.project_id == project_id, Paper.embedding.isnot(None)).all()
    embeddings = {p.id: json.loads(p.embedding) for p in papers}

    results = []
    for paper in papers:
        similarities = [
            SimilarPaperResponse(
                paper_id=other.id,
                filename=other.filename,
                similarity=cosine_similarity(embeddings[paper.id], embeddings[other.id]),
            )
            for other in papers
            if other.id != paper.id
        ]
        similarities.sort(key=lambda s: s.similarity, reverse=True)
        results.append(PaperSimilarityResponse(paper_id=paper.id, filename=paper.filename, similar_papers=similarities))

    return results


@router.get("/{project_id}/suggest-papers", response_model=list[SuggestedPaperResponse])
def suggest_papers(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggests up to 5 arXiv papers relevant to the project's topic, excluding any
    whose title closely matches a paper already uploaded to this project."""
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)

    try:
        candidates = search_arxiv(project.topic, max_results=10)
    except ArxivSearchError as exc:
        safe_log(f"[arxiv_service] Search failed for project {project_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach the arXiv API. Please try again later.",
        )

    existing_papers = db.query(Paper).filter(Paper.project_id == project_id).all()

    suggestions = [c for c in candidates if not _is_likely_duplicate(c["title"], existing_papers)]

    return suggestions[:5]


@router.get("/{project_id}/citation-graph", response_model=CitationGraphResponse)
def get_citation_graph(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns nodes/links data for visualizing relationships between papers in a
    project, based on content similarity (NOT real bibliographic citations, since
    we don't parse reference lists). citation_count is always 0 for now, kept in
    the schema so the frontend can render it once/if real citation counts exist.
    Links are only included above OFF_TOPIC_SIMILARITY_THRESHOLD, the same cutoff
    already used to decide whether two papers are meaningfully related, so the
    graph doesn't end up fully connected with noise-level edges."""
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)

    papers = db.query(Paper).filter(Paper.project_id == project_id, Paper.embedding.isnot(None)).all()
    embeddings = {p.id: json.loads(p.embedding) for p in papers}

    nodes = [
        CitationGraphNode(paper_id=p.id, title=p.title or p.filename, citation_count=0)
        for p in papers
    ]

    links = []
    for i, paper_a in enumerate(papers):
        for paper_b in papers[i + 1:]:
            weight = cosine_similarity(embeddings[paper_a.id], embeddings[paper_b.id])
            if weight >= OFF_TOPIC_SIMILARITY_THRESHOLD:
                links.append(CitationGraphLink(source=paper_a.id, target=paper_b.id, weight=weight))

    return CitationGraphResponse(nodes=nodes, links=links)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    workspace_id: int,
    project_id: int,
    payload: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    workspace = get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can delete a project",
        )

    db.delete(project)
    db.commit()
