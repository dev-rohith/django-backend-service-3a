# Assignment 3A – AI Backend (Django + LLM)

This extends the Assignment 2 Django backend with four new AI-powered endpoints: document ingestion with chunking, a FAISS vector store, RAG-based Q&A, and a general LLM chat endpoint. Everything builds on the same stack and patterns from Assignment 2.

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Django 6.1 + Django REST Framework |
| LLM | Anthropic Claude (`claude-opus-5-5`) |
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2` (local, no extra API key) |
| Vector Store | FAISS (`faiss-cpu`) |
| Text Splitting | LangChain `RecursiveCharacterTextSplitter` |
| Auth | Token authentication (same as Assignment 2) |
| Package manager | `uv` |

## Project Layout

```
assignment-3a-backend/
├── config/          Django settings, URLs, wsgi
├── core/            Shared pagination and constants
├── accounts/        Register, login, logout
├── documents/       Document upload and keyword search (Assignment 2)
├── ai/              All AI endpoints (new)
│   ├── models.py    AIQueryHistory
│   ├── views.py     Four endpoint views
│   ├── routes.py
│   └── services/
│       ├── llm_service.py   Prompt templates + Claude API calls
│       ├── vector_store.py  FAISS wrapper
│       └── chunker.py       Text splitter
└── faiss_index/     Auto-created at runtime (index.faiss + metadata.json)
```

## Setup

Make sure you have Python 3.12+ and [uv](https://docs.astral.sh/uv/) installed.

```bash
cd assignment-3a-backend
cp .env.example .env
```

Open `.env` and fill in at minimum:

```
SECRET_KEY=your-secret-key
DEBUG=True
ANTHROPIC_API_KEY=sk-ant-...
```

Then install and run:

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/` and the Swagger docs are at `http://127.0.0.1:8000/api/docs/`.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | No | Set to `True` for local development |
| `DATABASE_URL` | No | Defaults to SQLite. Use `postgres://` in production |
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key |

## Chunking Strategy

Documents are split using `RecursiveCharacterTextSplitter` from LangChain with these settings:

- **Chunk size:** 500 characters (~125 tokens). Small enough to keep each chunk topically focused, which improves retrieval precision.
- **Chunk overlap:** 50 characters. Ensures sentences that fall across a boundary still appear in at least one chunk with enough context to be useful.

The splitter tries to break on paragraph boundaries first, then newlines, then spaces, so it respects natural document structure wherever possible.

## Vector Store

Embeddings are generated locally using `sentence-transformers` with the `all-MiniLM-L6-v2` model (384 dimensions). No external API call is needed for embedding — this keeps ingestion fast and avoids the cost of a separate embeddings API.

The FAISS index uses `IndexIDMap` wrapping `IndexFlatL2`, which allows chunks to be deleted by their database primary key. This makes re-ingesting a document clean and idempotent — old vectors are removed before new ones are added.

The index is saved to `faiss_index/index.faiss` and a JSON sidecar (`faiss_index/metadata.json`) keeps the mapping from vector ID to document ID and chunk text. Both are reloaded on startup. The `faiss_index/` directory is created automatically and can be left out of version control — the index can always be rebuilt by re-ingesting documents.

## API Endpoints

These are the new endpoints added in this assignment. All require `Authorization: Token <token>`.

| Method | Path | Description |
|---|---|---|
| POST | `/api/ask-ai` | General LLM Q&A using a prompt template |
| POST | `/api/ingest-doc` | Chunk a document and store its embeddings |
| POST | `/api/rag-query` | Answer a question using retrieved document chunks |
| GET | `/api/query-history` | Paginated history of AI queries for the current user |

The existing Assignment 2 endpoints (`/api/documents`, `/api/query`, etc.) are unchanged.

## Usage Examples

**Register and log in to get a token:**

```bash
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "strongpass123"}'

curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "strongpass123"}'
```

**Upload a document, then ingest it:**

```bash
curl -X POST http://127.0.0.1:8000/api/documents \
  -H "Authorization: Token <your-token>" \
  -F "title=My Doc" \
  -F "file=@notes.txt"

curl -X POST http://127.0.0.1:8000/api/ingest-doc \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"document_id": 1}'
```

Response:
```json
{"status": "success", "chunk_count": 12}
```

**Ask a RAG question:**

```bash
curl -X POST http://127.0.0.1:8000/api/rag-query \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "What does the document say about authentication?"}'
```

Response:
```json
{
  "answer": "According to the document, authentication uses token-based auth...",
  "source_chunks": [
    {"document_id": "1", "chunk_text": "Authentication is implemented using..."},
    {"document_id": "1", "chunk_text": "Tokens are issued at login and must be..."}
  ]
}
```

**Ask a general question (no documents needed):**

```bash
curl -X POST http://127.0.0.1:8000/api/ask-ai \
  -H "Authorization: Token <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is retrieval-augmented generation?"}'
```

Response:
```json
{"response": "Retrieval-Augmented Generation (RAG) is a technique that..."}
```

**View query history:**

```bash
curl http://127.0.0.1:8000/api/query-history \
  -H "Authorization: Token <your-token>"
```

Returns a paginated list (`page_size=10`). Add `?page=2` to get the next page.

## Running Tests

```bash
uv run pytest
```

To lint:

```bash
uv run ruff check .
```
