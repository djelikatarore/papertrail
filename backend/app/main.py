from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

Base.metadata.create_all(bind=engine)

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

@app.get("/health")
def health():
    return {"status": "ok"}