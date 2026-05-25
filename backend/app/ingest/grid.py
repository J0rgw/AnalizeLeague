"""
GRID Esports data source — production mode.

GRID provides three access modes:
  1. Central Data (GraphQL)   — historical stats and aggregates
  2. Series State (GraphQL)   — structured in-series state at discrete points
  3. Series Events (JSONL)    — streaming positional events via HTTP/WebSocket

Key advantage over Riot API: ward positions with exact map coordinates,
champion positions at sub-second granularity, and live game streaming.

Requires a GRID Esports partnership agreement. Set GRID_API_KEY in .env.
Contact: https://grid.gg
"""
from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.ingest.base import DataSource

logger = logging.getLogger(__name__)


class GridDataSource(DataSource):
    """DataSource backed by the GRID Esports API."""

    def __init__(self) -> None:
        if not settings.grid_api_key:
            raise ValueError(
                "GRID_API_KEY must be set to use GridDataSource. "
                "Use RiotDataSource for demo/dev mode."
            )

    async def get_game(self, game_id: str) -> dict[str, Any]:
        # TODO (Phase 3): implement GRID Central Data GraphQL query
        # for series stats (cheaper) or Series Events JSONL for full
        # positional granularity (ward positions, jungle pathing).
        logger.warning("GridDataSource.get_game is a stub — returning empty dict")
        return {}

    async def get_match_history(
        self,
        player_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        # TODO (Phase 3): GRID Central Data GraphQL for historical series list
        logger.warning("GridDataSource.get_match_history is a stub — returning []")
        return []
