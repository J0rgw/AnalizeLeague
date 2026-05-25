"""
Riot Games API data source — demo / development mode.

Limitations (documented honestly):
  - Development API keys expire every 24 hours and must be renewed manually.
  - Riot API does NOT provide ward positions (only counts/timing).
  - Champion positions are available at 1-minute intervals only.
  - No live streaming — data is available only after the game ends.

Use GridDataSource in production for positional granularity.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.ingest.base import DataSource

logger = logging.getLogger(__name__)

_RIOT_BASE = "https://europe.api.riotgames.com"  # adjust region in Phase 2


class RiotDataSource(DataSource):
    """DataSource backed by the Riot Games REST API (match-v5)."""

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=_RIOT_BASE,
            headers={"X-Riot-Token": settings.riot_api_key},
            timeout=30.0,
        )

    async def get_game(self, game_id: str) -> dict[str, Any]:
        # TODO (Phase 2): GET /lol/match/v5/matches/{matchId}
        # and GET /lol/match/v5/matches/{matchId}/timeline for frame data
        logger.warning("RiotDataSource.get_game is a stub — returning empty dict")
        return {}

    async def get_match_history(
        self,
        player_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        # TODO (Phase 2): GET /lol/match/v5/matches/by-puuid/{puuid}/ids
        logger.warning("RiotDataSource.get_match_history is a stub — returning []")
        return []

    async def aclose(self) -> None:
        await self._client.aclose()
