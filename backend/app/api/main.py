"""
FastAPI application entry point.

Start the development server:
    cd backend
    uv run uvicorn app.api.main:app --reload

Production:
    uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

logging.basicConfig(
    level=logging.DEBUG if settings.env == "dev" else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AnalizeLeague API",
    description="AI assistant backend for League of Legends analysts and coaches.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Phase 2 Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe. Returns 200 {"status": "ok"} unconditionally."""
    return {"status": "ok"}


logger.info("AnalizeLeague API initializing in env=%s", settings.env)
