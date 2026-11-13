# MemoraAI – Intelligent Conversational Assistant & File Intelligence Workspace

> **"Every Conversation Matters. Every Memory Counts."**

MemoraAI is a full-stack, production-quality AI chatbot application powered by the **Google Gemini API**. It provides multi-turn conversational memory, intelligent document understanding, and a premium futuristic UI designed to rival ChatGPT, Gemini Advanced, and Claude.

---

## ✨ Features

### 🧠 Intelligent Conversation Memory
- Genuine multi-turn memory — the AI remembers and references previous messages
- Automatic context window management with token budgeting
- Conversation summarization for long threads
- Persistent SQLite storage via SQLAlchemy ORM

### 📄 File Intelligence System
- Upload **PDFs, Word Docs (.docx), Spreadsheets (.xlsx, .csv), Presentations (.pptx), Text/Markdown, and Images**
- Automatic text extraction and intelligent chunking
- Document context injected into AI prompts — the AI reads and answers about your files
- File Library sidebar with search, preview, and delete
- Drag-and-drop file upload anywhere on the screen
- Attachment strip on messages showing linked files

### 💬 Premium Chat Interface
- Modern dark/light theme with animated transitions
- Glassmorphism-inspired design with electric violet + cyan accent palette
- Markdown rendering with code syntax highlighting
- Copy response, Regenerate response, Export conversation
- Animated loading indicators and typing effects
- Responsive layout for desktop, tablet, and mobile

### 🗂️ Conversation Management
- Create, rename, delete conversations
- Full conversation history with search
- Contextual three-dot menus
- Active conversation highlighting

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5, CSS3 (custom), Vanilla JavaScript (ES6+) |
| **Backend** | Python 3.11+, Flask |
| **AI Provider** | Google Gemini API (`gemini-3.5-flash-lite`) |
| **Database** | SQLite + SQLAlchemy ORM |
| **File Processing** | pypdf, python-docx, python-pptx, openpyxl, Pillow |
| **Deployment** | Gunicorn (via `gunicorn.conf.py`) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- A Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd "chatbot AI"
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
GEMINI_API_KEY=AIzaSy...your_key_here
OPENAI_MODEL=gemini-3.5-flash-lite
FLASK_SECRET_KEY=your-random-secret-key
DATABASE_URL=sqlite:///contextai.db
```

> **Note:** The app auto-detects Gemini keys (starting with `AIzaSy`) and routes to the Gemini REST API. OpenAI keys (`sk-...`) route to the OpenAI Chat Completions API. No code changes needed — just set the right key.

### 3. Run the Application

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

**28 tests** cover:
- Multi-turn conversation memory (5-turn flow)
- Chat validation, regenerate, missing API key handling
- Context window management and token truncation
- Conversation CRUD operations and cascading deletes
- File upload (TXT, CSV), extraction, metadata, delete
- Rejection of unsupported file types

---

## 📁 Project Structure

```
chatbot AI/
├── app.py                    # Flask application factory (MemoraAI)
├── config.py                 # Config classes (Config, TestConfig)
├── database.py               # SQLAlchemy db instance
├── models.py                 # Conversation, Message, UploadedFile, DocumentChunk
├── openai_service.py         # Dual-provider AI service (Gemini + OpenAI)
├── conversation_service.py   # Conversation & message DB operations
├── context_manager.py        # Context window management + token budgeting
├── file_service.py           # File upload, extraction, chunking service
├── routes/
│   ├── __init__.py
│   ├── chat_routes.py        # /api/chat, /api/chat/regenerate, /api/export
│   ├── conversation_routes.py# /api/conversations CRUD
│   └── file_routes.py        # /api/files upload/list/delete/content
├── templates/
│   └── index.html            # MemoraAI single-page app
├── static/
│   ├── css/style.css         # MemoraAI premium theme
│   ├── js/app.js             # Frontend logic (file upload, chat, settings)
│   └── images/
│       ├── memoraai-logo.png # Full brand artwork (welcome screen)
│       └── memoraai-avatar.png # Compact robot avatar (sidebar, bubbles)
├── uploads/                  # Uploaded document storage
├── tests/
│   ├── conftest.py
│   ├── test_chat.py
│   ├── test_context.py
│   ├── test_conversations.py
│   ├── test_file_upload.py   # File intelligence tests (10 tests)
│   └── test_five_turn_conversation.py
├── requirements.txt
├── .env.example
├── gunicorn.conf.py
└── Procfile
```

---

## 🔐 Security

- API keys are **never** exposed to the browser, HTML, or JavaScript
- All keys stored server-side in `.env` only
- File uploads validated by extension and MIME type (25 MB limit)
- Secure filenames via `werkzeug.utils.secure_filename`
- Flask `SECRET_KEY` required for session security

---

## 🌐 Deployment

### Gunicorn (Linux/Mac)
```bash
gunicorn -c gunicorn.conf.py wsgi:app
```

### Render / Railway / Heroku
- Set environment variables in your platform dashboard
- Use `Procfile` for process configuration

---

## 📝 Supported File Types

| Category | Extensions |
|----------|-----------|
| Documents | `.pdf`, `.docx`, `.txt`, `.md` |
| Spreadsheets | `.xlsx`, `.csv` |
| Presentations | `.pptx` |
| Images | `.png`, `.jpg`, `.jpeg`, `.webp` |

---

## 🎨 Design System

| Token | Value |
|-------|-------|
| Primary BG | `#0a0d1a` (Deep midnight navy) |
| Secondary BG | `#0f1629` (Dark blue-grey) |
| Primary Accent | `#7c3aed` (Electric violet) |
| Secondary Accent | `#06b6d4` (Cyan blue) |
| Highlight | Soft purple gradients |
| Font | Inter (Google Fonts) |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built with ❤️ — MemoraAI v2.0.0*
