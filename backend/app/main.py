"""
FortuneDiary Backend — FastAPI entry point.

Endpoints:
- POST /agent       — AG-UI protocol (primary, used by Next.js frontend)
- POST /copilotkit  — CopilotKit SDK (legacy fallback)
- GET  /health      — health check
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FortuneDiary backend starting...")

    # 1. Compile the shared graph (used by both endpoints)
    from app.agent.agui_graph import build_agui_graph
    build_agui_graph()
    logger.info("✅ LangGraph graph ready")

    # 2. Mount AG-UI endpoint → /agent (primary)
    from app.agui_endpoint import mount_agui_endpoint
    mount_agui_endpoint(app)

    # 3. Mount CopilotKit SDK endpoint → /copilotkit (fallback)
    from app.copilotkit_endpoint import mount_copilotkit
    mount_copilotkit(app)

    # 4. Legacy checkpointed agent (REST API usage)
    try:
        from app.agent.graph import chat_agent
        await chat_agent.initialize()
    except Exception as exc:
        logger.warning("⚠️  Legacy chat agent init skipped: %s", exc)

    yield

    try:
        from app.agent.graph import chat_agent
        await chat_agent.shutdown()
    except Exception:
        pass
    logger.info("👋 Backend shut down")


app = FastAPI(title="FortuneDiary API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[*CORS_ORIGINS, "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST API routers ─────────────────────────────────────────────

for module_path, prefix, tag in [
    ("app.api.auth", "/api/v1/auth", "auth"),
    ("app.api.fortune", "/api/v1/fortune", "fortune"),
    ("app.api.diary", "/api/v1/diaries", "diaries"),
]:
    try:
        import importlib
        mod = importlib.import_module(module_path)
        app.include_router(mod.router, prefix=prefix, tags=[tag])
        logger.info("✅ %s router mounted at %s", tag, prefix)
    except Exception as exc:
        logger.warning("⚠️  %s router skipped: %s", tag, exc)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fortune-diary-backend"}
