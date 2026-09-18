# Multi-Document AI Research Assistant

An enterprise-grade, multi-tenant research assistant platform for processing multi-format literature (PDF, DOCX, TXT), performing dense/hybrid semantic retrieval using PostgreSQL `pgvector`, generating study flashcards, and answering complex queries with exact inline citations.

---

## Architecture Stack

- **Backend**: Python 3.11, FastAPI, Async SQLAlchemy 2.0, Alembic, Pydantic v2
- **Database & Vectors**: PostgreSQL 16 + `pgvector` (Vector 384d embedding column)
- **Cache & Queue**: Redis 7
- **Frontend**: Next.js 14 (App Router), React, Tailwind CSS, Lucide Icons
- **Infrastructure**: Docker & Docker Compose

---

## Directory Structure

```
multi_document_ai_research_assistant/
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── db/
│       │   ├── session.py
│       │   ├── base_class.py
│       │   └── base.py
│       ├── models/
│       │   ├── workspace.py
│       │   ├── user.py
│       │   ├── document.py
│       │   ├── chunk.py
│       │   ├── embedding.py
│       │   ├── conversation.py
│       │   ├── message.py
│       │   ├── flashcard.py
│       │   └── query_cache.py
│       ├── core/
│       │   └── security.py
│       └── api/
│           └── v1/
│               ├── deps.py
│               ├── auth.py
│               └── router.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── tailwind.config.js
    └── src/
        └── app/
            ├── layout.tsx
            ├── page.tsx
            └── globals.css
```

---

## Getting Started

### 1. Docker Compose (Recommended)
To run the full stack (Postgres + pgvector, Redis, Backend, Frontend):

```bash
docker-compose up -d --build
```

- Backend API: `http://localhost:8000`
- API Documentation (Swagger): `http://localhost:8000/docs`
- Frontend Dashboard: `http://localhost:3000`

### 2. Manual Backend Run

```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```
