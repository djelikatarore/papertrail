import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from difflib import SequenceMatcher
from itertools import zip_longest
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.settings import OFF_TOPIC_SIMILARITY_THRESHOLD
from app.database import get_db
from app.models.chat_session import ChatSession
from app.models.models import Paper
from app.models.project import Project
from app.models.project_access_restriction import ProjectAccessRestriction
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.routers.paper_router import PaperResponse
from app.services.arxiv_service import ArxivSearchError, search_arxiv
from app.services.chat_service import get_history_grouped_by_date, get_or_create_project_session, save_exchange
from app.services.core_service import CoreSearchError, search_core
from app.services.embedding_service import cosine_similarity
from app.services.llm_service import LlmError
from app.services.pubmed_service import PubmedSearchError, search_pubmed
from app.services.qa_service import generate_comparative_answer, retrieve_relevant_chunks_multi
from app.utils.auth_dependency import get_current_user
from app.utils.logging_utils import safe_log
from app.utils.workspace_access import get_workspace_or_404, require_member, require_project_access

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


class PaginatedProjectsResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedPapersResponse(BaseModel):
    items: list[PaperResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class SimilarPaperResponse(BaseModel):
    paper_id: int
    filename: str
    title: str | None
    similarity: float


class PaperSimilarityResponse(BaseModel):
    paper_id: int
    filename: str
    title: str | None
    similar_papers: list[SimilarPaperResponse]


class SuggestedPaperResponse(BaseModel):
    title: str
    authors: list[str]
    abstract: str
    pdf_link: str | None
    published_date: str
    source: str
    access_type: str | None


def _normalize_title(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _access_type(source: str, pdf_link: str | None) -> str | None:
    """PubMed's link is always a landing page (most indexed journals aren't
    open-access, so there's often no free PDF at all) — arXiv and CORE links are
    direct PDFs when present. None means no link was returned at all."""
    if not pdf_link:
        return None
    return "landing_page" if source == "pubmed" else "direct_pdf"


def _is_duplicate_title(candidate_title: str, reference_titles: list[str]) -> bool:
    normalized_candidate = _normalize_title(candidate_title)
    for reference in reference_titles:
        normalized_reference = _normalize_title(reference)
        if SequenceMatcher(None, normalized_candidate, normalized_reference).ratio() >= DUPLICATE_TITLE_SIMILARITY_THRESHOLD:
            return True
    return False


def _is_likely_duplicate(candidate_title: str, existing_papers: list[Paper]) -> bool:
    """Compares a candidate's title against each existing paper's extracted title
    (falling back to the filename for older papers uploaded before title
    extraction existed). A fuzzy ratio catches near-duplicates (e.g. a v2 arXiv
    revision with a slightly reworded title, or the same paper indexed by both
    arXiv and CORE)."""
    reference_titles = [
        paper.title or re.sub(r"\.pdf$", "", paper.filename, flags=re.IGNORECASE)
        for paper in existing_papers
    ]
    return _is_duplicate_title(candidate_title, reference_titles)


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


class ComparativeAskRequest(BaseModel):
    question: str
    paper_ids: list[int] = Field(min_length=1)


class ComparativePaperCitation(BaseModel):
    paper_id: int
    title: str
    cited_section: str | None


class ComparativeAnswerResponse(BaseModel):
    answer: str | None
    citations: list[ComparativePaperCitation]
    refused: bool


class UpdateProjectAccessRequest(BaseModel):
    allowed_member_ids: list[int] | None = None
    revoke_member_id: int | None = None


class ProjectAccessResponse(BaseModel):
    project_id: int
    restricted_member_ids: list[int]


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


@router.get("", response_model=PaginatedProjectsResponse)
def list_projects(
    workspace_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)

    query = db.query(Project).filter(Project.workspace_id == workspace_id)
    if membership.role != "OWNER":
        restricted_ids = {
            r.project_id
            for r in db.query(ProjectAccessRestriction)
            .filter(ProjectAccessRestriction.workspace_member_id == membership.id)
            .all()
        }
        if restricted_ids:
            query = query.filter(~Project.id.in_(restricted_ids))

    total = query.count()
    items = query.order_by(Project.id).offset((page - 1) * limit).limit(limit).all()

    return PaginatedProjectsResponse(
        items=items, total=total, page=page, limit=limit, total_pages=ceil(total / limit) if total else 0,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    return project


@router.get("/{project_id}/papers", response_model=PaginatedPapersResponse)
def list_project_papers(
    workspace_id: int,
    project_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The Paper Library listing for a project — there was previously no way to
    list a project's papers at all (only individual actions like upload/ask/
    download existed). Reuses the full PaperResponse shape (same as the upload
    endpoint) since there's also no dedicated single-paper GET endpoint yet —
    this is currently the only way to retrieve a paper's summary/keywords/status
    after upload without re-uploading it."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    query = db.query(Paper).filter(Paper.project_id == project_id)
    total = query.count()
    items = query.order_by(Paper.id).offset((page - 1) * limit).limit(limit).all()

    return PaginatedPapersResponse(
        items=items, total=total, page=page, limit=limit, total_pages=ceil(total / limit) if total else 0,
    )


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
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    papers = db.query(Paper).filter(Paper.project_id == project_id, Paper.embedding.isnot(None)).all()
    embeddings = {p.id: json.loads(p.embedding) for p in papers}

    results = []
    for paper in papers:
        similarities = [
            SimilarPaperResponse(
                paper_id=other.id,
                filename=other.filename,
                title=other.title,
                similarity=cosine_similarity(embeddings[paper.id], embeddings[other.id]),
            )
            for other in papers
            if other.id != paper.id
        ]
        similarities.sort(key=lambda s: s.similarity, reverse=True)
        results.append(
            PaperSimilarityResponse(
                paper_id=paper.id, filename=paper.filename, title=paper.title, similar_papers=similarities
            )
        )

    return results


@router.get("/{project_id}/suggest-papers", response_model=list[SuggestedPaperResponse])
def suggest_papers(
    workspace_id: int,
    project_id: int,
    date_from: int | None = Query(default=None, description="Earliest publication year (inclusive)"),
    date_to: int | None = Query(default=None, description="Latest publication year (inclusive)"),
    category: str | None = Query(default=None, description="arXiv category, e.g. cs.CL, cs.CV"),
    author: str | None = Query(default=None, description="Author name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggests up to 5 papers relevant to the project's topic, merged from arXiv,
    CORE, and PubMed, excluding any whose title closely matches a paper already
    uploaded to this project OR a suggestion already picked from another source
    (the same paper is often indexed by more than one of these). All filter
    params are optional — omitting them keeps the original unfiltered behavior.

    Each result's `access_type` tells the caller what `pdf_link` actually points
    to: "direct_pdf" for arXiv/CORE, "landing_page" for PubMed (most indexed
    journals aren't open-access, so there's rarely a free PDF), or null if no
    link was returned at all.

    `category` only applies to arXiv (cs.CL, cs.CV, ...) — CORE and PubMed have no
    equivalent taxonomy (PubMed uses MeSH terms, a differently-structured
    vocabulary), so it's a no-op for those two sources. The three sources are
    queried concurrently since each is an independent, slow-ish external call
    (CORE in particular can take 15-25s) — sequential calls would make this
    endpoint unpleasantly slow. If a source fails, its results are just omitted
    (logged, not fatal) — only failing all three raises an error."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    errors: list[str] = []

    def fetch_arxiv() -> list[dict]:
        try:
            results = search_arxiv(
                project.topic, max_results=10, category=category, author=author,
                date_from=date_from, date_to=date_to,
            )
        except ArxivSearchError as exc:
            safe_log(f"[arxiv_service] Search failed for project {project_id}: {exc}")
            errors.append(f"arXiv: {exc}")
            return []
        return [{**r, "source": "arxiv", "access_type": _access_type("arxiv", r.get("pdf_link"))} for r in results]

    def fetch_core() -> list[dict]:
        try:
            results = search_core(
                project.topic, max_results=10, author=author, date_from=date_from, date_to=date_to,
            )
        except CoreSearchError as exc:
            safe_log(f"[core_service] Search failed for project {project_id}: {exc}")
            errors.append(f"CORE: {exc}")
            return []
        return [{**r, "source": "core", "access_type": _access_type("core", r.get("pdf_link"))} for r in results]

    def fetch_pubmed() -> list[dict]:
        try:
            results = search_pubmed(
                project.topic, max_results=10, author=author, date_from=date_from, date_to=date_to,
            )
        except PubmedSearchError as exc:
            safe_log(f"[pubmed_service] Search failed for project {project_id}: {exc}")
            errors.append(f"PubMed: {exc}")
            return []
        return [{**r, "source": "pubmed", "access_type": _access_type("pubmed", r.get("pdf_link"))} for r in results]

    with ThreadPoolExecutor(max_workers=3) as executor:
        arxiv_future = executor.submit(fetch_arxiv)
        core_future = executor.submit(fetch_core)
        pubmed_future = executor.submit(fetch_pubmed)
        # Round-robin interleave (not a straight concatenation) so one source
        # (arXiv is usually fastest/most relevance-dense) doesn't monopolize the
        # final top-5 just by appearing first in the list.
        all_candidates = [
            candidate
            for group in zip_longest(arxiv_future.result(), core_future.result(), pubmed_future.result())
            for candidate in group
            if candidate is not None
        ]

    if len(errors) == 3:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach all external paper sources: {'; '.join(errors)}",
        )

    existing_papers = db.query(Paper).filter(Paper.project_id == project_id).all()

    suggestions = []
    seen_titles: list[str] = []
    for candidate in all_candidates:
        if not candidate.get("title"):
            continue
        if _is_likely_duplicate(candidate["title"], existing_papers):
            continue
        if _is_duplicate_title(candidate["title"], seen_titles):
            continue
        suggestions.append(candidate)
        seen_titles.append(candidate["title"])

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
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

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


@router.post("/{project_id}/ask-comparative", response_model=ComparativeAnswerResponse)
async def ask_comparative(
    workspace_id: int,
    project_id: int,
    payload: ComparativeAskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sprint 6 Tasks 6+7+8: retrieves the top-3 most relevant chunks per paper, then
    asks the LLM to synthesize a comparative answer that cites every paper
    individually. A missing or unverifiable citation for any single paper discards
    the whole answer (refused=True) rather than showing a partially-grounded one.
    Every exchange (including refusals) is saved to this project's chat history."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

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
            detail=f"Paper(s) not ready for questions yet: {not_ready}",
        )

    chunks_by_paper = retrieve_relevant_chunks_multi(payload.question, payload.paper_ids, db)
    papers_with_chunks = [
        {"paper_id": paper.id, "title": paper.title or paper.filename, "chunks": chunks_by_paper[paper.id]}
        for paper in papers
    ]

    try:
        answer, citations_by_paper, refused = await generate_comparative_answer(payload.question, papers_with_chunks)
    except LlmError as exc:
        safe_log(f"[qa_service] Failed to generate comparative answer for project {project_id}: {exc}")
        answer, citations_by_paper, refused = "The question answering service is temporarily unavailable.", {}, True

    citations = [
        ComparativePaperCitation(
            paper_id=paper.id,
            title=paper.title or paper.filename,
            cited_section=None if refused else citations_by_paper.get(paper.id),
        )
        for paper in papers
    ]

    response = ComparativeAnswerResponse(answer=answer, citations=citations, refused=refused)

    session = get_or_create_project_session(project_id, project.title, db)
    save_exchange(session.id, payload.question, response.answer, db)

    return response


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: str | None


class ChatHistoryDateGroup(BaseModel):
    date: str
    messages: list[ChatMessageResponse]


@router.get("/{project_id}/chat-history", response_model=list[ChatHistoryDateGroup])
def get_project_chat_history(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sprint 6 Task 8: returns this project's comparative Q&A history, grouped by date."""
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

    session = (
        db.query(ChatSession)
        .filter(ChatSession.project_id == project_id, ChatSession.paper_id.is_(None))
        .first()
    )
    if not session:
        return []

    return get_history_grouped_by_date(session, db)


@router.get("/{project_id}/access", response_model=ProjectAccessResponse)
def get_project_access(
    workspace_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Read-only counterpart to the PATCH below — needed so a client can render
    current per-member toggle state without having to mutate it first (the
    PATCH always requires exactly one of allowed_member_ids/revoke_member_id,
    so it can't double as a way to just read the current state)."""
    get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)

    restricted_member_ids = [
        r.workspace_member_id
        for r in db.query(ProjectAccessRestriction).filter(ProjectAccessRestriction.project_id == project_id).all()
    ]
    return ProjectAccessResponse(project_id=project_id, restricted_member_ids=restricted_member_ids)


@router.patch("/{project_id}/access", response_model=ProjectAccessResponse)
def update_project_access(
    workspace_id: int,
    project_id: int,
    payload: UpdateProjectAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Owner-only. Exactly one of allowed_member_ids (sets the full allow-list —
    every other workspace member becomes restricted from this project) or
    revoke_member_id (restricts just that one member, leaving everyone else's
    access unchanged) must be provided. Restrictions only affect future visibility
    — papers/drafts/comments a member already contributed stay in the project."""
    workspace = get_workspace_or_404(workspace_id, db)
    require_member(workspace_id, current_user.id, db)
    _get_project_or_404(workspace_id, project_id, db)

    if workspace.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the workspace owner can manage project access",
        )

    if (payload.allowed_member_ids is None) == (payload.revoke_member_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one of allowed_member_ids or revoke_member_id",
        )

    workspace_members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    member_ids = {m.id for m in workspace_members}
    owner_member_ids = {m.id for m in workspace_members if m.role == "OWNER"}

    if payload.revoke_member_id is not None:
        if payload.revoke_member_id not in member_ids:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found")
        if payload.revoke_member_id in owner_member_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot restrict the workspace owner")

        existing = (
            db.query(ProjectAccessRestriction)
            .filter(
                ProjectAccessRestriction.project_id == project_id,
                ProjectAccessRestriction.workspace_member_id == payload.revoke_member_id,
            )
            .first()
        )
        if not existing:
            db.add(
                ProjectAccessRestriction(
                    project_id=project_id,
                    workspace_member_id=payload.revoke_member_id,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
            db.commit()
    else:
        allowed_ids = set(payload.allowed_member_ids)
        unknown_ids = allowed_ids - member_ids
        if unknown_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member(s) not found in this workspace: {sorted(unknown_ids)}",
            )

        to_restrict = member_ids - allowed_ids - owner_member_ids
        to_unrestrict = allowed_ids

        db.query(ProjectAccessRestriction).filter(
            ProjectAccessRestriction.project_id == project_id,
            ProjectAccessRestriction.workspace_member_id.in_(to_unrestrict),
        ).delete(synchronize_session=False)

        already_restricted_ids = {
            r.workspace_member_id
            for r in db.query(ProjectAccessRestriction)
            .filter(ProjectAccessRestriction.project_id == project_id)
            .all()
        }
        for member_id in to_restrict - already_restricted_ids:
            db.add(
                ProjectAccessRestriction(
                    project_id=project_id,
                    workspace_member_id=member_id,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        db.commit()

    restricted_member_ids = [
        r.workspace_member_id
        for r in db.query(ProjectAccessRestriction)
        .filter(ProjectAccessRestriction.project_id == project_id)
        .all()
    ]

    return ProjectAccessResponse(project_id=project_id, restricted_member_ids=restricted_member_ids)


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    workspace_id: int,
    project_id: int,
    payload: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_workspace_or_404(workspace_id, db)
    membership = require_member(workspace_id, current_user.id, db)
    project = _get_project_or_404(workspace_id, project_id, db)
    require_project_access(project_id, membership, db)

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
