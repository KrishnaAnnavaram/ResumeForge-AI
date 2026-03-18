# CareerOS — AI Career Operating System

A production-grade AI system for generating tailored, evidence-grounded resumes and cover letters using a multi-agent LangGraph pipeline with hybrid retrieval.

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        CareerOS System                         │
├──────────────┬─────────────────────────────┬───────────────────┤
│   Frontend   │         FastAPI Backend      │   AI Pipeline     │
│  React 18    │                             │                   │
│  TypeScript  │  /api/auth    JWT Auth       │  JD Parser        │
│  Tailwind    │  /api/vault   Career Data    │  Profile Loader   │
│  Zustand     │  /api/jd      JD Analysis    │  Retrieval Agent  │
│  Framer Mot. │  /api/gen     Generation     │  Gap Analyzer     │
│              │  /api/tracker Applications   │  Rewrite Planner  │
│              │  /api/chat    AI Chat         │  Resume Writer    │
│              │                             │  CL Writer        │
├──────────────┴─────────────────────────────┤  Critic Agent     │
│              PostgreSQL 15+                 │  Feedback Interp. │
│  pgvector  │  Alembic  │  AsyncPG           ├───────────────────┤
│            │           │                   │   LangGraph       │
│  Users     │  Profiles │  Experiences       │   State Machine   │
│  JDs       │  Skills   │  Document Chunks   │   Human-in-Loop   │
│  Sessions  │  Resumes  │  Applications      │   PostgreSQL CKP  │
└────────────────────────────────────────────┴───────────────────┘
```

## Key Design Principles

1. **Truth Lock** — Generated content is validated by the Critic Agent against the exact evidence used. No fabricated metrics, skills, or titles.
2. **Hybrid Retrieval** — Three-layer retrieval: semantic (pgvector HNSW), structured (SQL array overlap), prior session (approved history).
3. **Evidence-Grounded Generation** — Resume Writer uses only the evidence retrieved for each section. Claim-evidence map is stored for every version.
4. **Append-Only Events** — Application event log is never updated or deleted, only appended.
5. **Human-in-the-Loop** — LangGraph interrupts at gap review and output review stages.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 async |
| Workflow | LangGraph (multi-agent graph) |
| Database | PostgreSQL 15+ with pgvector |
| LLM | Anthropic Claude (Sonnet for generation, Haiku for extraction) |
| Embeddings | sentence-transformers/all-mpnet-base-v2 |
| Frontend | React 18, TypeScript, Tailwind CSS, Framer Motion |
| Auth | JWT via python-jose + passlib bcrypt |
| Logging | structlog (JSON in production) |

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension
- Node.js 18+
- uv package manager

### PostgreSQL + pgvector

```bash
# Ubuntu/Debian
sudo apt install postgresql-15 postgresql-15-pgvector

# macOS (Homebrew)
brew install postgresql@15
# Then install pgvector: https://github.com/pgvector/pgvector

# Create database
createdb careeros
psql careeros -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql careeros -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
```

### Python Environment

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
cd /path/to/ResumeForge-AI
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your values:
# - DATABASE_URL
# - ANTHROPIC_API_KEY
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_hex(32))")
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Ingest Your Resume

```bash
python -c "
import asyncio
import uuid
from careeros.database.connection import AsyncSessionLocal
from careeros.ingestion.pipeline import ingest_document

async def main():
    async with AsyncSessionLocal() as db:
        user_id = uuid.UUID('YOUR-USER-UUID-HERE')
        await ingest_document(
            'Krishna_Annavaram_Resume (3).docx',
            user_id,
            db,
        )
        await db.commit()

asyncio.run(main())
"
```

### Run Backend

```bash
uvicorn careeros.main:app --reload --port 8000
```

### Run Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

## Agent Pipeline

```
START
  │
  ▼
Profile Loader ──── Loads all canonical career data from PostgreSQL
  │
  ▼
JD Parser ──────── Preprocesses JD, caches, extracts via LLM (Haiku)
  │
  ▼
Retrieval Agent ─── Three-layer hybrid search:
  │                  L1: Semantic (pgvector HNSW)
  │                  L2: Structured (skill array overlap)
  │                  L3: Prior session (approved history)
  ▼
Gap Analyzer ───── Deterministic pre-check + LLM nuance pass (Haiku)
  │
  ▼
[INTERRUPT: Surface gaps to user if critical skills missing]
  │
  ▼
Rewrite Planner ─── Section-by-section plan with evidence assignments (Sonnet)
  │
  ├──────────────────────────────┐
  ▼                              ▼
Resume Writer (Sonnet)    Cover Letter Writer (Sonnet)
  │                              │
  └──────────────┬───────────────┘
                 ▼
         Critic Agent ──── Validates all claims against evidence (Haiku)
                 │
                 ▼
         [INTERRUPT: Present to user for feedback]
                 │
                 ▼
         Feedback Interpreter ─── Parses feedback → action (Haiku)
                 │
         ┌───────┴──────┐
         ▼              ▼
    Approve       Refine/Regen
         │
         ▼
    Create Application Record
         │
         ▼
        END
```

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/auth/register | Register new user |
| POST | /api/auth/login | Login, get JWT token |
| GET | /api/auth/me | Current user info |
| GET | /api/vault/health | Vault completeness score |
| PATCH | /api/vault/profile | Update career profile |
| GET | /api/vault/experiences | List experiences |
| POST | /api/vault/experiences | Add experience |
| POST | /api/jd/analyze | Parse job description |
| POST | /api/generation/sessions | Create generation session |
| GET | /api/generation/sessions/{id}/stream | SSE pipeline stream |
| POST | /api/generation/sessions/{id}/feedback | Submit feedback |
| POST | /api/generation/sessions/{id}/approve | Approve output |
| POST | /api/tracker/applications | Log application |
| PATCH | /api/tracker/applications/{id}/status | Update status |
| GET | /api/tracker/applications/{id}/events | Event timeline |
| POST | /api/chat/sessions/{id}/messages | Send chat message |

## Running Tests

```bash
pytest tests/ -v --tb=short
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL async connection string | Yes |
| ANTHROPIC_API_KEY | Anthropic API key | Yes |
| SECRET_KEY | JWT signing secret (256-bit) | Yes |
| SONNET_MODEL | Claude Sonnet model ID | No (default set) |
| HAIKU_MODEL | Claude Haiku model ID | No (default set) |
| EMBEDDING_MODEL | Sentence transformer model | No |
| EMBEDDING_DIMENSION | Embedding vector size | No (768) |
| UPLOAD_DIR | File upload directory | No (./uploads) |
| CORS_ORIGINS | Allowed frontend origins | No |
| APP_ENV | development/production | No |
| LOG_LEVEL | Logging level | No (INFO) |

## Resume Found

The resume `Krishna_Annavaram_Resume (3).docx` was found in the repository root.
Run the ingestion script above after setting up the database and creating a user account.
