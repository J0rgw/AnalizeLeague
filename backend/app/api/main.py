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
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.storage.db import init_db

logging.basicConfig(
    level=logging.DEBUG if settings.env == "dev" else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Open DuckDB on startup, close on shutdown."""
    logger.info("Opening DuckDB connection")
    app.state.db = init_db()
    yield
    logger.info("Closing DuckDB connection")
    app.state.db.close()


app = FastAPI(
    title="AnalizeLeague API",
    description="AI assistant backend for League of Legends analysts and coaches.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", tags=["ops"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


logger.info("AnalizeLeague API initializing in env=%s", settings.env)
