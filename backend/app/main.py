"""
FortuneDiary Backend — FastAPI entry point.

Serves:
- /agent  — AG-UI protocol endpoint (for CopilotKit frontend)
- /health — health check

Run:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.agui_endpoint import router as agui_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info("🚀 FortuneDiary backend starting...")

    # Eagerly build the AG-UI graph so first request is fast
    from app.agui_endpoint import get_graph
    try:
        get_graph()
        logger.info("✅ AG-UI graph ready")
    except Exception as e:
        logger.error(f"⚠️  AG-UI graph build failed: {e}")

    # Mount CopilotKit SDK endpoint
    try:
        from app.copilotkit_endpoint import mount_copilotkit
        mount_copilotkit(app)
    except Exception as e:
        logger.warning(f"⚠️  CopilotKit endpoint mount skipped: {e}")

    # Also init the original chat agent if needed for non-AG-UI usage
    try:
        from app.agent.graph import chat_agent
        await chat_agent.initialize()
    except Exception as e:
        logger.warning(f"⚠️  Legacy chat agent init skipped: {e}")

    yield

    # Shutdown
    try:
        from app.agent.graph import chat_agent
        await chat_agent.shutdown()
    except Exception:
        pass
    logger.info("👋 Backend shut down")


# ── App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="FortuneDiary API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow CopilotKit frontend (Next.js dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *CORS_ORIGINS,
        "http://localhost:3000",   # Next.js default
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount AG-UI router
app.include_router(agui_router, tags=["ag-ui"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "fortune-diary-backend"}
