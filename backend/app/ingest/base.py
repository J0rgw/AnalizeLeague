"""
Abstract base class for all data source adapters.

Concrete implementations:
  - RiotDataSource  (demo mode, riot.py)
  - GridDataSource  (production mode, grid.py)

The interface returns raw dicts. Parsing into domain models happens in
the digest layer, keeping this layer thin and swappable.
"""

from __future__ import annotations

import abc
from typing import Any


class DataSource(abc.ABC):
    """Fetch raw game data from an upstream data provider."""

    @abc.abstractmethod
    async def get_game(self, game_id: str) -> dict[str, Any]:
        """Return raw game data for the given game_id."""
        ...

    @abc.abstractmethod
    async def get_match_history(
        self,
        player_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return the most recent `limit` matches for the given player."""
        ...
