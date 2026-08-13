import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in .env")

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
EMAIL_FROM = os.getenv("EMAIL_FROM", f"PaperTrail <{GMAIL_ADDRESS}>")

if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
    raise RuntimeError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))
VERIFICATION_TOKEN_EXPIRE_MINUTES = int(os.getenv("VERIFICATION_TOKEN_EXPIRE_MINUTES", "120"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
MAX_PAPERS_PER_PROJECT = 8
VALID_REVIEW_TYPES = {"SYSTEMATIC", "SCOPING", "CRITICAL", "NARRATIVE", "RAPID"}
VALID_DOCUMENT_TYPES = {"LITERATURE_REVIEW", "RESEARCH_PROPOSAL", "THESIS_CHAPTER", "CONFERENCE_PAPER", "OTHER"}
VALID_PROJECT_STATUSES = {"ACTIVE", "ARCHIVED"}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Optional second Groq account with its own separate quota — llm_service.py
# switches to it immediately on a 429 from the primary key rather than
# waiting out the primary key's rate limit. Unset by default; when absent,
# behavior is unchanged (primary key only).
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in .env")

TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_DPI = 300

CORE_API_KEY = os.getenv("CORE_API_KEY")
if not CORE_API_KEY:
    raise RuntimeError("CORE_API_KEY is not set in .env")

# Optional — unlike CORE_API_KEY above, this is allowed to be unset. When
# absent, semantic_scholar_service.get_citation_count always raises (caught
# by paper_router.py's fallback to CrossRef), so the app degrades gracefully
# rather than failing to start.
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# Optional — "Sign in with Google" is additive on top of the existing
# email/password system, not required for the app to run. When unset,
# POST /auth/google rejects with a clear 500 instead of failing startup.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

VISUAL_ELEMENTS_DIR = os.getenv("VISUAL_ELEMENTS_DIR", "visual_elements")
DRAFT_PDF_DIR = os.getenv("DRAFT_PDF_DIR", "draft_pdfs")
DRAFT_PDF_FOOTER_TEXT = "Generated from PaperTrail draft"

# Empirically determined (see conversation record): related papers within the same
# subfield scored ~0.52-0.73 cosine similarity; unrelated domains scored ~0.02-0.08.
# 0.30 sits comfortably in the gap between the two clusters.
OFF_TOPIC_SIMILARITY_THRESHOLD = float(os.getenv("OFF_TOPIC_SIMILARITY_THRESHOLD", "0.30"))

# Empirically determined (Sprint 6, Task 4): question-vs-chunk cosine similarity for
# genuinely answerable questions about the "Attention Is All You Need" test paper
# scored 0.32-0.58; unrelated questions (including an ML-adjacent but off-paper one)
# scored 0.01-0.23. 0.28 sits in the gap, leaning toward refusing borderline cases
# rather than risking an ungrounded answer.
QA_OUT_OF_SCOPE_THRESHOLD = float(os.getenv("QA_OUT_OF_SCOPE_THRESHOLD", "0.28"))
