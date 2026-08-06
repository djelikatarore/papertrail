from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import Base, engine

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.project import Project
from app.models.models import Paper, TextBlock, VisualElement
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.draft_document import DraftDocument
from app.models.review_comment import ReviewComment
from app.models.project_access_restriction import ProjectAccessRestriction

from app.routers.auth_router import router as auth_router
from app.routers.draft_router import router as draft_router
from app.routers.paper_router import router as paper_router
from app.routers.project_router import router as project_router
from app.routers.workspace_router import router as workspace_router
from app.utils.logging_utils import safe_log

Base.metadata.create_all(bind=engine)

# create_all only creates missing tables — it never alters an existing one, so
# the UniqueConstraint added to WorkspaceMember.__table_args__ has no effect on
# a database that already has this table. This index enforces the same
# constraint (SQLite raises the same IntegrityError on either) without a full
# migration framework, and is safe to run on every startup.
with engine.connect() as conn:
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_workspace_member_workspace_user "
        "ON workspace_members (workspace_id, user_id)"
    ))
    conn.commit()

app = FastAPI(
    title="PaperTrail API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(workspace_router)
app.include_router(project_router)
app.include_router(paper_router)
app.include_router(draft_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Without this, any bug that isn't already caught as an HTTPException falls
    through to Starlette's default handler, which returns a plain-text (not
    JSON) 500 body — inconsistent with every other error response in this API,
    which is always {"detail": "..."}. This keeps that shape uniform even for
    genuinely unexpected failures, while still logging the real exception."""
    safe_log(f"[main] Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred. Please try again."})


@app.get("/health")
def health():
    return {"status": "ok"}