# Begin — FortuneDiary

A personalized daily fortune and diary app that combines **BaZi (八字)** Chinese astrology, **Tarot** readings, and **AI-powered insights** into an interactive chat experience.

Users receive a daily "battery-style" fortune report across life domains (career, wealth, love, social, study), write diary entries that feed back into future readings, and chat with an AI agent that understands their personal context.

## Architecture

```
┌─────────────────────┐       AG-UI / SSE        ┌──────────────────────────┐
│   Next.js Frontend  │ ◄──────────────────────► │   FastAPI Backend        │
│   (React 18 + TW)   │                          │                          │
│                      │   REST /api/v1/*         │  ┌────────────────────┐  │
│  CopilotKit React   │ ◄──────────────────────► │  │  LangGraph Agent   │  │
│  Framer Motion       │                          │  │  (ReAct + Gemini)  │  │
└─────────────────────┘                          │  └────────┬───────────┘  │
                                                  │           │              │
                                                  │  ┌────────▼───────────┐  │
                                                  │  │  Services          │  │
                                                  │  │  · BaZi Engine     │  │
                                                  │  │  · Tarot Service   │  │
                                                  │  │  · Fortune Scoring │  │
                                                  │  │  · Memory / RAG    │  │
                                                  │  │  · Diary Vectors   │  │
                                                  │  └────────┬───────────┘  │
                                                  │           │              │
                                                  │  ┌────────▼───────────┐  │
                                                  │  │  Supabase          │  │
                                                  │  │  (Postgres + Auth) │  │
                                                  │  └────────────────────┘  │
                                                  └──────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, Tailwind CSS, Framer Motion, CopilotKit |
| Backend | FastAPI, Python 3.11+ |
| AI / LLM | Google Gemini (`gemini-3-flash-preview`), LangGraph ReAct agent |
| Embeddings | `gemini-embedding-001` (for diary RAG) |
| Database | Supabase (PostgreSQL + Auth + Row-Level Security) |
| Memory | AsyncPostgresSaver (LangGraph checkpointer), Letta (optional) |
| Astrology | BaZi engine (`cnlunar`, `sxtwl`), structured fortune scoring |
| Structured Output | `instructor` library for Pydantic-validated LLM responses |

## Features

- **Daily Fortune** — Battery-style fortune report generated from BaZi + Tarot + AI, with scores and actionable advice per domain
- **Tarot Draw** — Daily card draw (front-end animated or back-end random), persisted per user per day
- **BaZi Analysis** — Chinese astrology day-flow analysis based on user birth date, with stem/branch influence
- **AI Chat Agent** — LangGraph ReAct agent with diary RAG search, fortune knowledge retrieval, and diary generation tools
- **Thinking Process** — Gemini thinking/reasoning exposed to the frontend via state snapshots (configurable LOW/MEDIUM/HIGH)
- **Diary System** — Write and search diary entries with vector embeddings for semantic retrieval
- **Personalization** — User memory, contextual diary events, and personality traits feed into fortune generation
- **i18n** — Chinese (zh-CN) and English (en-US) with runtime language switching
- **Onboarding Flow** — Multi-step questionnaire (name, gender, birthday, region, life status) that branches based on student/working status

## Project Structure

```
Begin/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, router mounting
│   │   ├── config.py                # Centralized configuration
│   │   ├── agent/
│   │   │   ├── graph.py             # LangGraph ReAct agent (LangChain wrapper)
│   │   │   ├── agui_graph.py        # AG-UI graph (Google GenAI SDK, thinking)
│   │   │   └── prompts.py           # System prompts + fortune context loader
│   │   ├── api/
│   │   │   ├── auth.py              # Supabase JWT auth
│   │   │   ├── fortune.py           # Fortune endpoints (daily, history, stats)
│   │   │   ├── diary.py             # Diary CRUD + vector search
│   │   │   └── user.py              # User profile + preferences
│   │   ├── services/
│   │   │   ├── bazi_service.py       # BaZi astrology engine
│   │   │   ├── tarot_service.py      # Tarot card draw + persistence
│   │   │   ├── structured_fortune_service.py  # Battery fortune generation
│   │   │   ├── fortune_scoring_engine.py      # Domain score calculation
│   │   │   ├── vector_service.py     # Embedding + similarity search
│   │   │   ├── memory_service.py     # User memory extraction
│   │   │   ├── knowledge_service.py  # Fortune knowledge RAG
│   │   │   └── letta_service.py      # Letta integration (optional)
│   │   └── core/
│   │       ├── db.py                 # Supabase client
│   │       └── genai_service.py      # Google GenAI wrapper
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # Landing + onboarding flow
│   │   ├── home/page.tsx             # Main app (fortune tab, diary tab, chat)
│   │   ├── layout.tsx                # Root layout
│   │   ├── components/
│   │   │   ├── FortuneTab.tsx        # Battery fortune display
│   │   │   ├── DiaryTab.tsx          # Diary list + editor
│   │   │   ├── ChatOverlay.tsx       # AI chat panel
│   │   │   ├── CelestialPanel.tsx    # Tarot card display
│   │   │   └── ThinkingBubble.tsx    # AI thinking process display
│   │   ├── contexts/AuthContext.tsx   # Auth state management
│   │   ├── i18n/                     # Internationalization
│   │   └── lib/
│   │       ├── api.ts                # Backend API client
│   │       └── theme.ts              # Design tokens + colors
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── start.sh                          # Local dev launcher
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+ (3.12 or 3.13 recommended)
- Node.js 18+
- A [Supabase](https://supabase.com) project (Postgres + Auth)
- A [Google AI](https://ai.google.dev) API key (Gemini access)

### Setup

1. **Clone the repo**

```bash
git clone <repo-url>
cd Begin
```

2. **Configure environment variables**

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your credentials:

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_DB_URI=postgresql://postgres.your-project:password@...
GOOGLE_API_KEY=AIza...

# Optional
LETTA_BASE_URL=http://localhost:8283
THINKING_LEVEL=HIGH          # LOW | MEDIUM | HIGH
```

3. **Start the app** (recommended — handles venv + deps automatically)

```bash
./start.sh
```

This will:
- Create a Python virtual environment in `backend/.venv`
- Install backend dependencies via `pip install -e .`
- Install frontend dependencies via `npm install`
- Start the backend at `http://localhost:8000`
- Start the frontend at `http://localhost:3000`

### Manual Start

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
source .env && uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

Exposes backend on port `8002` and frontend on port `3001`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/agent` | AG-UI protocol (primary chat endpoint) |
| `POST` | `/copilotkit` | CopilotKit SDK (legacy fallback) |
| `GET` | `/api/v1/fortune/status` | Check if today's fortune is generated |
| `GET` | `/api/v1/fortune/daily` | Get/generate daily fortune |
| `GET` | `/api/v1/fortune/history` | Fortune history (last N days) |
| `GET` | `/api/v1/fortune/tarot-cards` | All tarot cards for front-end draw |
| `GET` | `/api/v1/fortune/tarot/draw-daily` | Back-end daily tarot draw |
| `GET` | `/api/v1/fortune/categories/{type}` | Category-specific fortune |
| `GET` | `/api/v1/fortune/stats` | Fortune statistics |
| `*` | `/api/v1/diaries/*` | Diary CRUD + search |
| `*` | `/api/v1/auth/*` | Authentication |
| `*` | `/api/v1/user/*` | User profile + preferences |

## How Fortune Generation Works

1. **BaZi Engine** — Calculates day-flow analysis from user's birth date using Chinese lunar calendar libraries (`cnlunar`, `sxtwl`). Determines day master, stem/branch influences, and body strength.

2. **Tarot Draw** — One card per user per day. Can be drawn from the front-end (animated card selection) or back-end (random). Persisted to prevent re-draws.

3. **Memory Context** — Retrieves user diary history, recent concerns, upcoming events, personality traits, and goals via vector similarity search.

4. **Fortune Scoring Engine** — Computes numerical scores (0-100) per domain based on BaZi elements, tarot card meaning, and user context.

5. **Battery Fortune Generation** — Structured LLM call (via `instructor`) produces the "battery" format: overall + per-domain sections with status, charge actions, drain warnings, and scores.

6. **Caching** — Results are stored in `daily_fortune_details` (Supabase) and an in-memory cache (1-hour TTL). Subsequent requests return cached data.

