# 🛍️ ShopMind AI

> AI-powered product recommendation and price intelligence platform.
> Built with LangGraph multi-agent architecture, FastAPI, Groq LLM, and Streamlit.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2-purple)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)](https://postgresql.org)

---

## What It Does

ShopMind AI understands natural language product queries, discovers relevant products across the web, analyses pricing and reviews, and delivers ranked recommendations — with plain-English explanations for each pick. Users can watch products for price drops and receive WhatsApp alerts automatically.

**Example:** *"Find me wireless noise-cancelling headphones under $150"* returns a ranked list of products with deal scores, review analysis, and an explanation of why each was chosen.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Streamlit UI  (localhost:8501)                           │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼───────────────────────────────────┐
│  FastAPI  (localhost:8000)                                │
│  POST /search  │  POST /search/watch  │  GET /watchlist  │
│                              ▲                            │
│  APScheduler (daily 08:00 UTC) ───────┘                  │
└──────────────────────┬───────────────────────────────────┘
                       │ graph.ainvoke()
┌──────────────────────▼───────────────────────────────────┐
│  LangGraph StateGraph                                     │
│                                                           │
│  [orchestrator] ──→ route_intent()                        │
│       │                    │                              │
│  "search"              "watch"                            │
│       ▼                    ▼                              │
│  [preference]    [save_watchlist] ──→ END                 │
│       ▼                                                   │
│  [product_intelligence]  ←── SerpAPI / Mock               │
│       ▼                                                   │
│  [recommendation]  ←── Groq LLM / Template               │
│       ▼                                                   │
│      END                                                  │
│                                                           │
│  [alert_checker] (APScheduler only) ──→ Twilio ──→ END   │
└──────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│  PostgreSQL                                               │
│  users │ user_preferences │ products (cache)             │
│  watchlist │ search_history │ alert_logs                 │
└──────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Responsibility | LLM? |
|-------|---------------|------|
| **Orchestrator** | Classify intent (search/watch), extract product query + budget | ✅ Groq |
| **Preference Agent** | Load user preferences from DB, merge with query context | ❌ DB only |
| **Product Intelligence** | Fetch products (SerpAPI/mock), compute trust scores, cache results | ❌ API only |
| **Recommendation Agent** | Score products, rank by deal+review+relevance, generate explanations | ✅ Groq |
| **Alert Agent** | Check watchlist prices daily, send WhatsApp alerts via Twilio | ❌ Scheduled |

### Scoring Formula

```
final_score = deal_score × 0.40 + review_score × 0.35 + relevance_score × 0.25
```

- **deal_score**: Price vs budget + discount percentage
- **review_score**: Rating quality + review volume (logarithmic)
- **relevance_score**: Trust score + preferred brand boost

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph 0.2 (StateGraph) |
| LLM | Groq (llama-3.3-70b-versatile) |
| Backend API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Product Search | SerpAPI (Google Shopping) |
| Notifications | Twilio WhatsApp |
| Scheduler | APScheduler |
| Frontend | Streamlit |
| Testing | pytest + pytest-asyncio |
| Linting | Ruff |
| Containerisation | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Docker Desktop (for PostgreSQL)
- API keys: [Groq](https://console.groq.com) · [SerpAPI](https://serpapi.com) · [Twilio](https://console.twilio.com)

### 1. Clone & Install

```bash
git clone https://github.com/yourusername/shopmind-ai.git
cd shopmind-ai

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your API keys
```

> **No API keys?** Set `USE_MOCK_DATA=true` in `.env` to run fully on mock data — no SerpAPI or Groq needed.

### 3. Start Database

```bash
docker compose up postgres -d
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Backend

```bash
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 6. Start Frontend (new terminal)

```bash
streamlit run frontend/app.py
# UI: http://localhost:8501
```

### One-command setup (with Make)

```bash
make install    # Create venv and install deps
make dev        # Start Postgres + backend
make frontend   # Start Streamlit (separate terminal)
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check |
| `GET` | `/health/ready` | Readiness check (DB connection) |
| `POST` | `/users` | Create user |
| `PUT` | `/users/{id}/preferences` | Set user preferences |
| `POST` | `/search` | Run AI product search |
| `POST` | `/search/watch` | Add to watchlist |
| `GET` | `/watchlist/{user_id}` | List watchlist |
| `PATCH` | `/watchlist/{user_id}/{item_id}` | Update watchlist item |
| `DELETE` | `/watchlist/{user_id}/{item_id}` | Remove from watchlist |

### Example: Search Request

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "query": "best wireless headphones under $150"
  }'
```

### Example: Watch Request

```bash
curl -X POST http://localhost:8000/search/watch \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "your-user-id",
    "query": "Sony WH-1000XM5",
    "product_title": "Sony WH-1000XM5 Wireless Headphones",
    "target_price": 249.99
  }'
```

---

## Running Tests

```bash
make test           # All tests
make test-fast      # Unit tests only (no DB needed)
make test-cov       # With HTML coverage report
```

---

## Project Structure

```
shopmind-ai/
├── app/
│   ├── agents/           # 5 LangGraph agent nodes
│   ├── api/routes/       # FastAPI route handlers
│   ├── core/             # Config, DB, logging, exceptions
│   ├── graph/            # LangGraph StateGraph + state schema
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── scheduler/        # APScheduler job definitions
│   ├── services/         # Database service layer
│   ├── tools/            # SerpAPI, price scorer, Twilio, mock data
│   └── main.py           # FastAPI application entry point
├── frontend/
│   └── app.py            # Streamlit UI
├── migrations/           # Alembic database migrations
├── mock_data/            # Sample product data for dev mode
├── tests/
│   ├── test_agents/      # Agent unit tests
│   └── test_api/         # API integration tests
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── README.md
```

---

## Key Design Decisions

### Why LangGraph over plain Python?
LangGraph provides a structured state machine with:
- **Conditional routing**: one line to add a new intent/path
- **Shared state**: every agent reads/writes from a single TypedDict — no manual data plumbing
- **Visualisation**: `graph.get_graph().draw_mermaid()` generates architecture diagrams from code
- **Async native**: all nodes are async by default

### Why PostgreSQL as a product cache?
- Avoids redundant SerpAPI calls (100 calls/month on free tier)
- TTL-based invalidation: re-fetch when `fetched_at > PRODUCT_CACHE_TTL_HOURS`
- Queryable: can ask "find all cached Sony products in headphones category"
- No extra infrastructure (Redis) needed

### Why APScheduler over a separate worker?
- Simpler: no Redis, no Celery, no separate worker process
- Sufficient for this scale
- Trade-off: in-process scheduling means job state is lost on restart
- Production upgrade path: migrate to Celery + Redis + persistent job store

### Mock data fallback
Auto-enabled when API keys are placeholders. Allows the full multi-agent pipeline to run — LangGraph graph, scoring, recommendations — without any paid API calls. Makes the project immediately demonstrable in interviews.

---

## License

MIT
