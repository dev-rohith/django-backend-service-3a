# Django GenAI Backend — Assignments 3A & 3B

A Django REST API extended with AI capabilities: document ingestion, a FAISS vector store, RAG-based Q&A, a LangGraph conversational agent, and a Streamlit chat UI. Builds directly on the Assignment 2 codebase.

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Django 6.1 + Django REST Framework |
| LLM | Anthropic Claude (`claude-opus-5-5`) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (local, no extra API key) |
| Vector Store | FAISS (`faiss-cpu`) |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Agent | LangGraph `StateGraph` with conditional routing |
| External Tool | Open-Meteo weather API (free, no key required) |
| UI | Streamlit |
| Auth | Token authentication (same as Assignment 2) |
| Package manager | `uv` |

## Project Layout

```
django-backend-service-3a/
├── config/           Django settings, URLs, wsgi
├── core/             Shared pagination and constants
├── accounts/         Register, login, logout
├── documents/        Document upload and keyword search (Assignment 2)
├── ai/               Assignment 3A — direct LLM endpoints
│   ├── models.py     AIQueryHistory
│   ├── views.py      ask-ai, ingest-doc, rag-query, query-history
│   └── services/
│       ├── llm_service.py   Prompt templates + Claude API calls
│       ├── vector_store.py  FAISS wrapper (thread-safe singleton)
│       └── chunker.py       Text splitter
├── agent/            Assignment 3B — conversational agent
│   ├── models.py     ChatSession, ChatMessage
│   ├── views.py      file upload, chat, history
│   └── services/
│       ├── agent.py  LangGraph graph — classify → [rag|weather|general] → respond
│       └── tools.py  RAG search + Open-Meteo weather
├── streamlit_app/    Streamlit chat UI
│   └── app.py
└── faiss_index/      Auto-created at runtime (index.faiss + metadata.json)
```

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
```

Fill in `.env`:

```
SECRET_KEY=your-secret-key
DEBUG=True
ANTHROPIC_API_KEY=sk-ant-...
```

Install and run:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/` and Swagger docs at `http://127.0.0.1:8000/api/docs/`.

**To run the Streamlit UI** (separate terminal):

```bash
pip install streamlit requests
streamlit run streamlit_app/app.py
```

Open `http://localhost:8501`, log in with a registered account, upload a document, and start chatting.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Set to `True` for local development |
| `DATABASE_URL` | No | Defaults to SQLite |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `BACKEND_URL` | No | Streamlit target (defaults to `http://localhost:8000`) |

## Chunking Strategy

Documents are split with `RecursiveCharacterTextSplitter` (chunk size 500 chars, overlap 50 chars). The splitter respects paragraph and sentence boundaries, so each chunk tends to be topically cohesive rather than cut mid-thought. Overlap ensures context is preserved across boundaries.

## Vector Store

Embeddings are generated locally with `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dimensions) — no embeddings API or extra cost. The FAISS index uses `IndexIDMap` wrapping `IndexFlatL2` so individual chunks can be deleted by their database primary key. Re-ingesting a document is idempotent: old vectors are removed before new ones are added.

The index persists to `faiss_index/index.faiss` alongside a JSON sidecar that maps vector IDs to document IDs and chunk text. Both are loaded on startup.

## LangGraph Agent (3B)

Each chat message flows through a three-node decision graph:

```
classify_intent
      ↓
  [rag | weather | general]  ← conditional branch based on intent
      ↓
generate_response
```

- **rag** — searches the FAISS vector store and includes source chunks in the response
- **weather** — calls the Open-Meteo geocoding + forecast API to return live temperature data
- **general** — answers directly using the conversation history as context

Session memory is maintained per `session_key`: all prior turns are loaded from the database and passed to the agent on each request.

## API Endpoints

All endpoints require `Authorization: Token <token>`.

**Assignment 3A**

| Method | Path | Description |
|---|---|---|
| POST | `/api/ask-ai` | General LLM Q&A |
| POST | `/api/ingest-doc` | Chunk and embed a document by ID |
| POST | `/api/rag-query` | Answer using retrieved document chunks |
| GET | `/api/query-history` | Paginated query history (page_size=10) |

**Assignment 3B**

| Method | Path | Description |
|---|---|---|
| POST | `/api/agent/upload/` | Upload PDF or TXT, auto-ingest into FAISS |
| POST | `/api/agent/chat/` | Chat with the LangGraph agent (session memory) |
| GET | `/api/agent/history/<session_key>/` | Last 100 messages for a session |

## Usage Examples

**Register and get a token:**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "strongpass123"}'

curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "strongpass123"}'
```

**Upload and auto-ingest a document:**

```bash
curl -X POST http://127.0.0.1:8000/api/agent/upload/ \
  -H "Authorization: Token <your-token>" \
  -F "file=@report.pdf"
```

Response:
```json
{"status": "success", "document_id": 3, "chunk_count": 18}
```

**Chat with the agent:**

```bash
curl -X POST http://127.0.0.1:8000/api/agent/chat/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the report say about revenue?", "session_id": null}'
```

Response:
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "response": "According to the report, revenue increased by 12% year-over-year...",
  "sources": [
    {"document_id": "3", "chunk_text": "Revenue grew from $4.2M to $4.7M in FY2024..."}
  ]
}
```

**Ask a weather question:**

```bash
curl -X POST http://127.0.0.1:8000/api/agent/chat/ \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Tokyo?", "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"}'
```

**3A — RAG query (uses document ID from ingest-doc):**

```bash
curl -X POST http://127.0.0.1:8000/api/rag-query \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the authentication flow?"}'
```

## Running Tests

```bash
uv run pytest
```

To lint:

```bash
uv run ruff check .
```
