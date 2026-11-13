# ContextAI – Intelligent Conversational Assistant

> **"Conversations That Remember. Intelligence That Understands."**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/AI-OpenAI%20API-emerald.svg)](https://platform.openai.com/)
[![SQLite](https://img.shields.io/badge/database-SQLite%20%2F%20SQLAlchemy-blue.svg)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Project Overview

**ContextAI** is a production-quality, context-aware conversational AI application powered by the real OpenAI Chat Completions API. Unlike naive question-and-answer bots that treat each interaction in isolation, ContextAI is architected with persistent multi-turn conversational memory, intelligent token budgeting, and running summarization.

ContextAI accurately tracks conversation state across turns, remembers facts and preferences mentioned earlier, and seamlessly persists all conversation histories in SQLite so users can pick up right where they left off—even across browser refreshes and sessions.

---

## 2. Key Features

- **Genuine Multi-Turn Conversational Memory**: Remembers context across arbitrarily long exchanges.
- **Hybrid Context Window Management**:
  - *Recent Message Truncation*: Keeps the latest 20 turns within active working memory.
  - *Running Conversation Summary*: Automatically summarizes older conversation history when turn thresholds are reached.
  - *Token Budgeting*: Dynamic token estimation using `tiktoken` to respect model context constraints without losing original messages from the database.
- **Real OpenAI Integration**: Direct integration via the official `openai` Python SDK. Configurable model (`gpt-4o-mini`, `gpt-4o`, `gpt-4.1-mini`, etc.) via environment variables.
- **Persistent SQLite Database**: Full cascade deletion, conversation indexing, search filtering, and timestamp tracking via SQLAlchemy ORM.
- **Premium Futuristic UI**:
  - Dark mode by default with instant toggle to light mode (persisted in `localStorage`).
  - Sleek glassmorphism surfaces, radial neon glows, and fluid micro-interactions.
  - Full Markdown rendering (tables, blockquotes, bold/italic, lists) via `marked.js` and `DOMPurify`.
  - Code syntax highlighting with `highlight.js` featuring individual "Copy Code" buttons on snippet headers.
  - Suggested starter prompts for quick exploration.
  - Auto-scrolling, typing wave indicator, response regeneration, copy response, conversation search, inline renaming, and deletion modals.
- **Enterprise-Ready Architecture & Security**:
  - Zero client-side API key exposure; all keys and models are validated securely on the backend.
  - Hardened security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`).
  - Comprehensive error handling with clean, user-friendly messages for rate limits, network timeouts, and authentication issues.
- **Production & Cloud Ready**: Fully equipped with Gunicorn configuration, `wsgi.py`, `Procfile`, and zero-downtime deployment guidance for platforms like Render, Railway, or AWS.

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Custom Glassmorphism & Neon Tokens), Modern ES6+ JavaScript |
| **Libraries (CDN)** | `marked.js` (Markdown), `DOMPurify` (XSS Sanitizer), `highlight.js` (Syntax Highlighter) |
| **Backend** | Python 3.11+, Flask 3.1, Flask-CORS, REST API |
| **ORM & Database** | SQLAlchemy ORM, Flask-SQLAlchemy 3.1, SQLite 3 |
| **AI Integration** | Official OpenAI Python SDK (`openai>=1.40.0`), `tiktoken` (BPE Token Estimation) |
| **Environment** | `python-dotenv` |
| **Production WSGI** | `gunicorn` (Linux/Cloud), Threaded Multi-Worker Architecture |
| **Testing** | `pytest`, `pytest-mock`, Custom Five-Turn Verification Suite |

---

## 4. Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Client (Browser / SPA)"]
        UI["ContextAI Modern UI (Dark/Light)"]
        Markdown["Markdown & Code Highlighter"]
        State["Client State & Storage"]
        UI <--> Markdown
        UI <--> State
    end

    subgraph Backend["Flask REST API Backend"]
        Routes["REST Endpoints (/api/chat, /api/conversations)"]
        ConvService["ConversationService (CRUD & Search)"]
        ContextMgr["ContextManager (Token Budgeting & Window Pruning)"]
        OpenAISvc["OpenAIService (SDK Client & Error Translator)"]

        Routes <--> ConvService
        Routes <--> ContextMgr
        Routes <--> OpenAISvc
    end

    subgraph Storage["Persistent Storage"]
        DB[("SQLite Database (contextai.db)")]
        ConvTable["conversations table"]
        MsgTable["messages table (Cascade Delete)"]
        DB --- ConvTable
        DB --- MsgTable
    end

    subgraph LLM["OpenAI Cloud API"]
        OpenAIAPI["OpenAI Chat Completions API (gpt-4o-mini)"]
    end

    UI -- "HTTPS / JSON (POST /api/chat)" --> Routes
    ConvService <--> DB
    ContextMgr -- "1. Fetches History\n2. Injects Running Summary\n3. Truncates under Token Budget" --> ConvService
    OpenAISvc -- "Secure API Request (Bearer Token)" --> OpenAIAPI
    OpenAIAPI -- "Response Tokens + Usage" --> OpenAISvc
    OpenAISvc --> Routes
    Routes -- "JSON Response + Message Model" --> UI
```

---

## 5. Context Window Management Strategy

ContextAI implements a **three-pillar hybrid context strategy** inside `context_manager.py`:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      TOTAL CONTEXT WINDOW BUDGET                       │
│                           (e.g., 4000 Tokens)                          │
├──────────────────┬──────────────────────┬──────────────────────────────┤
│  SYSTEM PROMPT   │   RUNNING SUMMARY    │    RECENT TURNS WINDOW       │
│  (Base Persona   │  (Older Contextual   │  (Up to 20 Chronological     │
│   & Guidelines)  │   Facts & Memory)    │   Messages, Token Budgeted)  │
└──────────────────┴──────────────────────┴──────────────────────────────┘
```

1. **System Prompt Preservation**:
   - The assistant's custom persona, helpfulness constraints, and conversational guidelines are permanently anchored at the top of every completion payload.
2. **Running Conversation Summary**:
   - When a conversation exceeds the configured threshold (e.g., 10 messages), older messages outside the recent active window are summarized via a dedicated low-temperature summary call.
   - The resulting summary is persisted in `conversations.summary` and injected as a contextual memory frame into future requests.
3. **Recent Message Truncation & Token Budgeting**:
   - Up to 20 recent messages are kept verbatim in active memory.
   - Using `tiktoken` (BPE encoding), exact token lengths are computed including message formatting overhead.
   - If candidate messages exceed the allocated context budget, oldest candidate turns are trimmed one by one.
   - **Crucial Rule**: Original raw messages are **never deleted from SQLite**. Users can always scroll back and view their complete unfiltered chat history.

---

## 6. Project Structure

```
chatbot AI/
│
├── .env.example             # Template for environment configuration
├── .env                     # Local environment file (ignored by Git)
├── .gitignore               # Comprehensive Git ignore rules
├── requirements.txt         # Production and development dependencies
├── Procfile                 # Process file for Render / Heroku deployment
├── wsgi.py                  # WSGI entrypoint for production servers
├── gunicorn.conf.py         # Production Gunicorn concurrency settings
│
├── config.py                # Application configuration & system prompt
├── database.py              # Flask-SQLAlchemy instance setup
├── models.py                # Conversation and Message database models
├── openai_service.py        # OpenAI SDK integration & robust error handling
├── context_manager.py       # Token budgeting, truncation & summary logic
├── conversation_service.py  # Database CRUD operations and search indexing
├── app.py                   # Application factory, routes, and error handlers
│
├── routes/
│   ├── __init__.py          # Blueprint registrations
│   ├── chat_routes.py       # /api/chat, /api/health, /api/regenerate
│   └── conversation_routes.py # /api/conversations CRUD & clear
│
├── templates/
│   └── index.html           # Single Page Application HTML5 template
│
├── static/
│   ├── css/
│   │   └── style.css        # Futuristic dark/light styling, glassmorphism
│   ├── js/
│   │   └── app.js           # Client controller, markdown, syntax highlighting
│   └── images/
│       └── logo.svg         # ContextAI neural vector logo
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures and mock OpenAI provider
│   ├── test_chat.py         # Multi-turn chat, validation, error scenarios
│   ├── test_context.py      # Token counting, truncation, summary logic
│   ├── test_conversations.py# Conversation CRUD, search, and cascade delete
│   └── test_five_turn_conversation.py # Mandatory 5-turn memory verification
│
├── run_five_turn_test.py    # Standalone 5-turn test runner (live or --mock)
└── README.md                # Comprehensive project documentation
```

---

## 7. Installation & Local Setup

### Prerequisites
- Python 3.11 or newer installed.
- Git installed.
- OpenAI API Key ([Get an API Key](https://platform.openai.com/api-keys)).

### Step 1: Clone or Navigate to the Repository
```bash
cd "c:\Users\dasar\Downloads\chatbot AI"
```

### Step 2: (Optional but Recommended) Create a Virtual Environment
```bash
# On Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# On macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 8. Environment Variable Configuration

Create a `.env` file in the root directory by copying `.env.example`:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your OpenAI credentials:

```env
# =====================================================================
# ContextAI Environment Configuration
# =====================================================================

# 1. Your OpenAI API Key (Required for live AI responses)
OPENAI_API_KEY=sk-proj-your-actual-openai-api-key-here

# 2. Model Selection (Configurable without changing code)
# Options: gpt-4o-mini (recommended, fast & cost-efficient), gpt-4o, gpt-4-turbo
OPENAI_MODEL=gpt-4o-mini

# 3. Flask Security
FLASK_SECRET_KEY=generate_a_random_32_character_string_for_production
FLASK_DEBUG=False

# 4. Database Location
DATABASE_URL=sqlite:///contextai.db

# 5. Context Memory Parameters
MAX_CONTEXT_TOKENS=4000
MAX_RECENT_MESSAGES=20
SUMMARY_TRIGGER_COUNT=10
RESERVED_RESPONSE_TOKENS=1000
```

> **Security Note**: Never commit your `.env` file to version control. The repository's `.gitignore` automatically prevents `.env` and SQLite database files from being tracked.

---

## 9. Running the Application Locally

Start the Flask development server:

```bash
python app.py
```

You will see output similar to:
```
2026-11-13 18:45:00 [INFO] contextai: Database tables initialized successfully.
2026-11-13 18:45:00 [INFO] contextai: Starting ContextAI on port 5000 (debug=False)...
 * Running on http://127.0.0.1:5000
```

Open your web browser and navigate to:
```
http://localhost:5000
```

---

## 10. REST API Documentation

ContextAI exposes a full REST API for programmatic access:

### 1. Send Message
- **Endpoint**: `POST /api/chat`
- **Body**:
  ```json
  {
    "conversation_id": "optional-uuid-here",
    "message": "My name is Karthik."
  }
  ```
- **Response** `(200 OK)`:
  ```json
  {
    "success": true,
    "conversation_id": "da0849bf-dc1a-40f5-a743-d0410d5be573",
    "conversation_title": "Introduction with Karthik",
    "message": {
      "id": "e98cb145-21fb-4819-bf93-6a9ad7865c3b",
      "conversation_id": "da0849bf-dc1a-40f5-a743-d0410d5be573",
      "role": "assistant",
      "content": "Hello Karthik! It's a pleasure to meet you. How can I assist you today?",
      "created_at": "2026-11-13T13:15:00.000Z"
    },
    "usage": {
      "prompt_tokens": 140,
      "completion_tokens": 22,
      "total_tokens": 162
    }
  }
  ```

### 2. Create Conversation
- **Endpoint**: `POST /api/conversations`
- **Body**: `{"title": "Machine Learning Research"}` (Optional)
- **Response** `(201 Created)`:
  ```json
  {
    "success": true,
    "conversation": {
      "id": "da0849bf-dc1a-40f5-a743-d0410d5be573",
      "title": "Machine Learning Research",
      "created_at": "2026-11-13T13:15:00.000Z",
      "updated_at": "2026-11-13T13:15:00.000Z",
      "summary": null,
      "message_count": 0,
      "last_message": null
    }
  }
  ```

### 3. List Conversations & Search
- **Endpoint**: `GET /api/conversations?q=search_term`
- **Response** `(200 OK)`:
  ```json
  {
    "success": true,
    "count": 1,
    "conversations": [...]
  }
  ```

### 4. Get Conversation Details & Messages
- **Endpoint**: `GET /api/conversations/<conversation_id>`
- **Response** `(200 OK)`:
  ```json
  {
    "success": true,
    "conversation": {
      "id": "da0849bf-dc1a-40f5-a743-d0410d5be573",
      "title": "Introduction with Karthik",
      "summary": null,
      "messages": [
        {
          "id": "msg-1",
          "role": "user",
          "content": "My name is Karthik.",
          "created_at": "2026-11-13T13:14:50.000Z"
        },
        {
          "id": "msg-2",
          "role": "assistant",
          "content": "Hello Karthik!",
          "created_at": "2026-11-13T13:14:52.000Z"
        }
      ]
    }
  }
  ```

### 5. Rename Conversation
- **Endpoint**: `PATCH /api/conversations/<conversation_id>`
- **Body**: `{"title": "Updated Conversation Name"}`
- **Response** `(200 OK)`: `{"success": true, "conversation": {...}}`

### 6. Delete Conversation
- **Endpoint**: `DELETE /api/conversations/<conversation_id>`
- **Response** `(200 OK)`: `{"success": true, "message": "Conversation deleted successfully"}`

### 7. Regenerate Previous AI Response
- **Endpoint**: `POST /api/conversations/<conversation_id>/regenerate`
- **Response** `(200 OK)`: Returns newly generated assistant message without duplicating the previous user prompt.

### 8. System Health Check
- **Endpoint**: `GET /api/health`
- **Response** `(200 OK)`:
  ```json
  {
    "status": "healthy",
    "database": "connected",
    "openai_configured": true,
    "model": "gpt-4o-mini",
    "max_context_tokens": 4000,
    "max_recent_messages": 20
  }
  ```

---

## 11. Automated Testing Suite

ContextAI comes with an automated test suite covering all functional and edge cases.

### Running Pytest
Run the test suite inside your terminal:
```bash
python -m pytest -v
```

All 18 unit and integration tests execute with mocked responses to prevent consuming any OpenAI API credits during automated testing:

```
tests/test_chat.py::test_chat_multi_turn_flow PASSED                     [  5%]
tests/test_chat.py::test_chat_empty_message_validation PASSED            [ 11%]
tests/test_chat.py::test_chat_regenerate_response PASSED                 [ 16%]
tests/test_chat.py::test_chat_missing_api_key_error PASSED               [ 22%]
tests/test_context.py::test_token_estimation PASSED                      [ 27%]
tests/test_context.py::test_message_token_calculation PASSED             [ 33%]
tests/test_context.py::test_context_building_with_system_and_summary PASSED [ 38%]
tests/test_context.py::test_recent_message_truncation_under_budget PASSED [ 44%]
tests/test_context.py::test_messages_to_summarize_partition PASSED       [ 50%]
tests/test_context.py::test_database_messages_preserved_after_truncation PASSED [ 55%]
tests/test_conversations.py::test_health_check PASSED                    [ 61%]
tests/test_conversations.py::test_create_conversation PASSED             [ 66%]
tests/test_conversations.py::test_get_conversations_and_search PASSED    [ 72%]
tests/test_conversations.py::test_get_conversation_details PASSED        [ 77%]
tests/test_conversations.py::test_rename_conversation PASSED             [ 83%]
tests/test_conversations.py::test_delete_conversation_cascading PASSED   [ 88%]
tests/test_conversations.py::test_clear_conversation_messages PASSED     [ 94%]
tests/test_five_turn_conversation.py::test_mandatory_five_turn_conversation_flow PASSED [100%]
============================= 18 passed in 0.54s ==============================
```

---

## 12. Mandatory Five-Turn Memory Test

To verify genuine multi-turn conversational memory, execute the dedicated test:

### Sequence Under Test:
- **Turn 1**: *"My name is Karthik."*
- **Turn 2**: *"I am a third-year CSE student."*
- **Turn 3**: *"My specialization is Artificial Intelligence and Machine Learning."*
- **Turn 4**: *"I am interested in developing AI projects."*
- **Turn 5**: *"Based on our conversation, tell me my name, academic year, specialization, and interest."*

### Running the Live or Mock Test:

```bash
# Run with the live OpenAI API (requires OPENAI_API_KEY in .env):
python run_five_turn_test.py

# Or run with the built-in mock runner (zero API credits consumed):
python run_five_turn_test.py --mock
```

**Verification Results Output**:
```
=================================================================
ContextAI - Mandatory Five-Turn Conversational Memory Test
=================================================================

--- Turn 1 ---
User: My name is Karthik.
[Conversation Created ID: d3fe813a-0ec8-4135-a105-18e990c3591a]
AI: I've noted that: "My name is Karthik.". How can I assist you further?

--- Turn 2 ---
User: I am a third-year CSE student.
AI: I've noted that: "I am a third-year CSE student.". How can I assist you further?

--- Turn 3 ---
User: My specialization is Artificial Intelligence and Machine Learning.
AI: I've noted that: "My specialization is Artificial Intelligence and Machine Learning.". How can I assist you further?

--- Turn 4 ---
User: I am interested in developing AI projects.
AI: I've noted that: "I am interested in developing AI projects.". How can I assist you further?

--- Turn 5 ---
User: Based on our conversation, tell me my name, academic year, specialization, and interest.
AI: Based on our conversation:
- Name: Karthik
- Academic Year: third-year CSE student
- Specialization: Artificial Intelligence and Machine Learning
- Interest: developing AI projects

--- Simulating Browser Refresh (SQLite Persistence Check) ---
Fetching conversation d3fe813a-0ec8-4135-a105-18e990c3591a from SQLite database...
[✓] Retrieved 10 messages successfully from SQLite database!

--- Verification Checklist ---
[✓] Name (Karthik): PASSED
[✓] Academic Year (third-year): PASSED
[✓] Specialization (AI / ML): PASSED
[✓] Interest (AI projects): PASSED

[SUCCESS] Mandatory Five-Turn Memory Test Passed Successfully!
```

---

## 13. Production Deployment Guide

ContextAI is prepared for deployment to hosting platforms such as **Render**, **Railway**, or **Heroku**.

### Deploying to Render

1. **Push your code to a GitHub repository** (ensure `.env` is NOT pushed).
2. Go to the [Render Dashboard](https://dashboard.render.com/) and click **New > Web Service**.
3. Connect your GitHub repository.
4. Set the following build and run configurations:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
5. Under **Environment Variables**, add:
   - `OPENAI_API_KEY`: Your real OpenAI API Key (`sk-...`)
   - `OPENAI_MODEL`: `gpt-4o-mini`
   - `FLASK_SECRET_KEY`: A strong random string
   - `FLASK_ENV`: `production`
6. Click **Deploy Web Service**.

### Persistent Database Guidance:
- For Render's free tier, the SQLite file resides on the ephemeral disk.
- To persist database records across redeploys, add a **Render Disk** mounted at `/data` and set:
  ```env
  DATABASE_URL=sqlite:////data/contextai.db
  ```
- Alternatively, for enterprise production scaling, connect a managed PostgreSQL instance by setting:
  ```env
  DATABASE_URL=postgresql://user:password@host:5432/dbname
  ```
  *(SQLAlchemy handles PostgreSQL automatically without application code changes).*

---

## 14. GitHub Publishing Instructions

To publish your project to GitHub:

```bash
# 1. Verify that .env is NOT tracked
git status

# 2. Stage all project files
git add .

# 3. Create initial commit
git commit -m "feat: complete production-grade ContextAI conversational assistant"

# 4. Link your remote repository
git remote add origin https://github.com/your-username/contextai.git

# 5. Push to GitHub main branch
git branch -M main
git push -u origin main
```

---

## 15. Future Enhancements

- **Vector Search (RAG)**: Integration of ChromaDB or pgvector for semantic knowledge retrieval over uploaded documents (PDF, CSV, TXT).
- **Voice Input & Synthesis**: Native browser Web Speech API integration for speech-to-text input and natural text-to-speech AI playback.
- **Multi-Model Selector**: Live dropdown to switch between GPT-4o, Claude 3.5 Sonnet, and Gemini Pro at runtime.
- **Streaming Completions (SSE)**: Real-time token streaming using Server-Sent Events.

---

## 16. License

This project is licensed under the [MIT License](LICENSE).
