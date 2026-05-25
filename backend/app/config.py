"""
Application settings loaded from environment variables / .env file.

Usage:
    from app.config import settings
    print(settings.ollama_host)

The .env file is resolved relative to the working directory. Run all
commands from /backend so that backend/.env is found automatically.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
