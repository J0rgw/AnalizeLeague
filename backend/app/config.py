"""
Application settings loaded from environment variables / .env file.

Usage:
    from app.config import settings
    print(settings.ollama_host)

The .env file is resolved relative to the working directory. Run all
commands from /backend so that backend/.env is found automatically.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    riot_api_key: str = Field(default="", description="Riot Games developer API key")

    ollama_host: str = Field(
        default="http://localhost:11434",
        description="Base URL of the local Ollama server",
    )
    ollama_model: str = Field(
        default="llama3.1",
        description="Ollama model tag to use for generation",
    )
    ollama_timeout_s: int = Field(
        default=60,
        ge=1,
        description="Per-request timeout (seconds) for Ollama chat calls",
    )

    duckdb_path: str = Field(
        default="../data/analizeleague.duckdb",
        description="Path to the DuckDB database file",
    )

    env: str = Field(default="dev", description="Runtime environment: dev | prod")

    riot_region: str = Field(
        default="europe",
        description="Riot API regional routing cluster: europe | americas | asia | sea",
    )

    grid_api_key: str = Field(
        default="",
        description="GRID Esports API key (production only, leave empty in dev)",
    )

    allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins. Comma-separated in env, e.g. http://a,http://b",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        # pydantic-settings reads env vars as strings; accept "a,b,c" form.
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("ollama_host")
    @classmethod
    def _must_be_loopback(cls, v: str) -> str:
        # Enforces the product's privacy promise: scrim data never leaves the box.
        # Opt-out exists for users running Ollama on a trusted LAN host.
        if os.getenv("ALLOW_REMOTE_LLM") == "1":
            return v
        host = (urlparse(v).hostname or "").lower()
        if host in _LOOPBACK_HOSTS:
            return v
        raise ValueError(
            f"OLLAMA_HOST={v!r} is not loopback (got host={host!r}). "
            "Scrim data must stay on this machine. "
            "Set ALLOW_REMOTE_LLM=1 to override at your own risk."
        )


settings = Settings()
