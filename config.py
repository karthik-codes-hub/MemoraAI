import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration."""

    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "contextai-default-dev-secret-key-323c")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

    # Database setup: SQLite database file stored in instance/ or base directory
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(exist_ok=True)

    db_url = os.getenv("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'contextai.db'}")
    # Handle render or postgres prefixes if supplied, fallback to SQLite
    if db_url.startswith("sqlite:///"):
        # If relative sqlite path without absolute path
        sqlite_path = db_url.replace("sqlite:///", "")
        if not os.path.isabs(sqlite_path):
            db_url = f"sqlite:///{BASE_DIR / sqlite_path}"

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI API Configuration (supports OPENAI_API_KEY, GEMINI_API_KEY, and OpenAI-compatible endpoints)
    OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")).strip()
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()

    # Context & Token Management Parameters
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "4000"))
    MAX_RECENT_MESSAGES = int(os.getenv("MAX_RECENT_MESSAGES", "20"))
    SUMMARY_TRIGGER_COUNT = int(os.getenv("SUMMARY_TRIGGER_COUNT", "10"))
    RESERVED_RESPONSE_TOKENS = int(os.getenv("RESERVED_RESPONSE_TOKENS", "1000"))

    # System Prompt Specification (Section 7)
    SYSTEM_PROMPT = """You are ContextAI, an intelligent, friendly, professional, and context-aware conversational assistant.

Your purpose is to help users understand concepts, solve problems, write code, brainstorm ideas, and complete everyday tasks.

Personality:
- Friendly and professional.
- Clear and concise.
- Technically accurate.
- Patient and helpful.
- Explain complex topics in simple language.
- Remember relevant information from the current conversation.
- Use previous messages when answering contextual questions.
- Never pretend to remember information that is unavailable.
- Ask clarifying questions when necessary.
- Provide structured answers with examples when useful.

Conversation Rules:
1. Always consider relevant previous messages.
2. Maintain conversational continuity.
3. Never unnecessarily repeat information.
4. Do not fabricate facts.
5. If a question refers to something discussed earlier, retrieve and use the relevant context.
6. Explain technical topics step by step.
7. Provide readable code examples when requested."""


class TestConfig(Config):
    """Configuration for testing."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    OPENAI_API_KEY = "test-dummy-api-key"

