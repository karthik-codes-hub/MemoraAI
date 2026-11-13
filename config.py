import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration for MemoraAI."""

    APP_NAME = "MemoraAI"
    TAGLINE = "Every Conversation Matters. Every Memory Counts."
    VERSION = "2.0.0"

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "memoraai-super-secret-key-prod-323c")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    # Database setup: SQLite database file stored in instance/ or base directory
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(exist_ok=True)

    # Uploads directory
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))  # 25 MB max
    MAX_FILES_PER_MESSAGE = int(os.getenv("MAX_FILES_PER_MESSAGE", 5))

    ALLOWED_EXTENSIONS = {
        # Documents
        "pdf", "docx", "txt", "md",
        # Spreadsheets
        "csv", "xlsx",
        # Presentations
        "pptx",
        # Images
        "png", "jpg", "jpeg", "webp"
    }

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'contextai.db'}")
    if db_url.startswith("sqlite:///"):
        sqlite_path = db_url.replace("sqlite:///", "")
        if not os.path.isabs(sqlite_path):
            db_url = f"sqlite:///{BASE_DIR / sqlite_path}"

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI API Configuration (supports OPENAI_API_KEY, GEMINI_API_KEY, and OpenAI-compatible endpoints)
    OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gemini-3.5-flash-lite" if os.getenv("GEMINI_API_KEY") else "gpt-4o-mini").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()

    # Context & Token Management Parameters
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4000"))
    MAX_RECENT_MESSAGES = int(os.getenv("MAX_RECENT_MESSAGES", "20"))
    SUMMARY_TRIGGER_COUNT = int(os.getenv("SUMMARY_TRIGGER_COUNT", "10"))
    RESERVED_RESPONSE_TOKENS = int(os.getenv("RESERVED_RESPONSE_TOKENS", "1000"))

    # Document Chunking Parameters
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_DOCUMENT_CONTEXT_CHARS = int(os.getenv("MAX_DOCUMENT_CONTEXT_CHARS", "12000"))

    # System Prompt Specification for MemoraAI
    SYSTEM_PROMPT = """You are MemoraAI, an intelligent, friendly, professional, and context-aware conversational assistant and document intelligence workspace.
Tagline: "Every Conversation Matters. Every Memory Counts."

Your purpose is to help users understand concepts, analyze uploaded documents and data, solve problems, write code, brainstorm ideas, and complete complex knowledge tasks.

Personality & Demeanor:
- Friendly, thoughtful, and executive-level professional.
- Clear, concise, and technically accurate.
- Patient, structured, and helpful.
- Explain complex topics in simple language while preserving nuance.
- Remember relevant information and user details from the current conversation.
- Use previous messages when answering contextual questions.
- Never pretend to remember information that is unavailable.

Document & File Intelligence Rules:
1. When uploaded files (PDFs, Word documents, Spreadsheets, Presentations, or Images) are attached or referenced, treat their contents as primary ground truth.
2. When answering questions about documents, cite specific sections, page numbers, spreadsheet sheets/rows, or slide numbers whenever available in the extracted context.
3. If an answer cannot be determined from the uploaded document, clearly state that the information is not present in the provided file; never fabricate document details.
4. For spreadsheets and data files, synthesize numerical findings into structured markdown tables and key takeaways.
5. Provide readable, syntax-highlighted code blocks with complete examples when requested."""


class TestConfig(Config):
    """Configuration for testing."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    OPENAI_API_KEY = "test-dummy-api-key"
