import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not set in .env")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587
EMAIL_FROM = os.getenv("EMAIL_FROM", f"PaperTrail <{GMAIL_ADDRESS}>")

if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
    raise RuntimeError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
MAX_PAPERS_PER_PROJECT = 8
VALID_REVIEW_TYPES = {"SYSTEMATIC", "SCOPING", "CRITICAL", "NARRATIVE", "RAPID"}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in .env")

TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
OCR_DPI = 300

VISUAL_ELEMENTS_DIR = os.getenv("VISUAL_ELEMENTS_DIR", "visual_elements")

# Empirically determined (see conversation record): related papers within the same
# subfield scored ~0.52-0.73 cosine similarity; unrelated domains scored ~0.02-0.08.
# 0.30 sits comfortably in the gap between the two clusters.
OFF_TOPIC_SIMILARITY_THRESHOLD = float(os.getenv("OFF_TOPIC_SIMILARITY_THRESHOLD", "0.30"))

FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "faiss_index.bin")
