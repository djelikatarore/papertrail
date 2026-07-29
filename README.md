# PaperTrail

PaperTrail is an AI-assisted academic research assistant. It lets a research
team upload papers into shared workspaces, get AI-generated summaries,
keywords, and similarity/citation analysis, ask grounded questions about
individual or multiple papers, and generate structured literature review
drafts from the papers they've collected.

## Tech stack

Backend: FastAPI, SQLite (SQLAlchemy)

Authentication: JWT, Gmail SMTP for password reset emails

AI: Groq (text and vision models) for summarization, keyword extraction,
paper type detection, grounded Q&A, and draft generation. sentence-transformers
for embeddings, FAISS for similarity search.

PDF processing: PyMuPDF for text and figure extraction, Tesseract for OCR on
scanned pages.

External paper sources: arXiv, CORE, PubMed.

## Project status

The backend is functionally complete, covering Sprints 2 through 8. The
frontend is currently in the design phase.

## Project structure

```
papertrail/
  README.md
  BRANCHING.md
  backend/
    app/
      main.py
      config/
        settings.py
      database/
      models/
        user.py, workspace.py, project.py, models.py (Paper, TextBlock,
        VisualElement), draft_document.py, review_comment.py, ...
      routers/
        auth_router.py, workspace_router.py, project_router.py,
        paper_router.py, draft_router.py
      services/
        pdf_service.py, chunking_service.py, ocr_service.py,
        summary_service.py, keyword_service.py, paper_type_service.py,
        embedding_service.py, faiss_service.py, qa_service.py,
        draft_generation_service.py, draft_pdf_service.py,
        feedback_service.py, llm_service.py, email_service.py,
        arxiv_service.py, core_service.py, pubmed_service.py
      utils/
        auth_dependency.py, workspace_access.py, logging_utils.py
    requirements.txt
```

## Setup and running the backend

Requirements: Python 3.11+, a Groq API key, and (optionally) a Tesseract OCR
installation for scanned PDFs.

Create and activate a virtual environment, then install dependencies:

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside `backend/` with at least:

```
JWT_SECRET_KEY=your-secret-key
GROQ_API_KEY=your-groq-api-key
```

Other environment variables (Gmail credentials for password reset emails,
CORE API key for paper suggestions, various thresholds and file paths) have
defaults or are optional. See `app/config/settings.py` for the full list.

Run the server:

```
uvicorn app.main:app --reload --port 8000
```

The API is then available at `http://127.0.0.1:8000`, with interactive docs
at `http://127.0.0.1:8000/docs`.

## Main features

Authentication: signup, login, JWT-protected routes, forgot/reset password.

Workspaces and projects: workspace creation and invites, project management,
per-member project access restriction.

Upload and extraction: PDF upload with background AI processing (text
extraction, multi-column support, OCR fallback for scanned pages).

AI summarization: automatic contribution/methodology/key results/limitations
summary and keyword extraction for each uploaded paper, with anti-hallucination
verification against the source text.

Similarity and citation graph: embedding-based similarity between papers in a
project, off-topic detection, and a citation graph view.

Grounded Q&A: single-paper and multi-paper question answering, with answers
required to cite verifiable source sections, plus persistent chat history.

Drafts: draft CRUD, AI-assisted draft generation from selected papers'
summaries, automatic PDF export, reviewer feedback ingestion with AI-generated
correction suggestions.

Multi-source search: keyword search across papers and projects in a
workspace, with filters by review type, read status, and detected paper
type, plus external paper suggestions merged from arXiv, CORE, and PubMed.

## Branching strategy

See BRANCHING.md for how the sprint branches relate to each other and to the
`develop` integration branch.

## Known limitations

A few limitations have been identified and are accepted for now rather than
treated as unresolved bugs:

Abstract detection can miss the real abstract on papers that don't use
standard section headings (e.g. some physics journal formats), falling back
to the first few hundred words instead.

Chunking only recognizes a fixed list of section names; unrecognized
subsections get absorbed into the previous recognized section instead of
forming their own chunk.

Groq's per-minute token limit on the vision model means papers with a very
large number of figures can take a long time to get all of their figures
described, since the rate limit is enforced server-side regardless of how
requests are paced client-side.

Background paper processing does not survive a server restart. If the
server stops while a paper is still being processed, that paper is left in
whatever state it had reached, with no automatic resume.

Paper type detection (used to flag non-academic documents) can misclassify
documents that have no clear visual structure, such as plain-text files with
no font-size hierarchy.
