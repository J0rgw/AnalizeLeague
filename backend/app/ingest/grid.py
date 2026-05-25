"""
GRID Esports data source — production mode.

GRID provides three access modes:
  1. Central Data (GraphQL)   — historical stats and aggregates
  2. Series State (GraphQL)   — structured in-series state at discrete points
  3. Series Events (JSONL)    — streaming positional events via HTTP/WebSocket

Key advantage over Riot API: ward positions with exact map coordinates,
champion positions at sub-second granularity, and live game streaming.

The stream_grid_events() function is the core innovation: it parses the
compressed JSONL stream line-by-line without loading the full payload into
memory, filtering only the event types the digest builder needs.

GridDataSource adapter is a Phase 3 stub — the interface and streaming
parser are complete and tested; the HTTP integration requires a GRID
partnership agreement.
"""

from __future__ import annotations

import logging
from collections.abc import Generator, Iterable
from typing import Any

import orjson

from app.config import settings
from app.ingest.base import DataSource

logger = logging.getLogger(__name__)

# Event types relevant to the digest builder.
# Filtering at parse time keeps peak memory near zero regardless of stream size.
_DEFAULT_RELEVANT: frozenset[str] = frozenset(
    {
        "champion_kill",
        "building_destroyed",
        "epic_monster_killed",
        "jungle_monster_killed",
        "ward_placed",
        "ward_destroyed",
    }
)


def stream_grid_events(
    source: Iterable[bytes],
    *,
    event_types: frozenset[str] | None = None,
) -> Generator[dict[str, Any], None, None]:
    """
    Parse a GRID Series Events JSONL stream, yielding only relevant events.

    Reads the stream line-by-line — never loads the full payload into memory.
    Call on a raw HTTP response body (or an open gzip-decompressed file handle).

    Args:
        source:      Iterable of raw byte lines (one JSON object per line).
        event_types: Event type strings to retain. None → use _DEFAULT_RELEVANT.
                     Pass an empty frozenset to yield every event.

    Yields:
        Parsed event dicts whose "type" field (lowercased) is in event_types.
    """
    keep = event_types if event_types is not None else _DEFAULT_RELEVANT
    for raw in source:
        line: bytes = raw if isinstance(raw, bytes) else raw.encode()
        line = line.strip()
        if not line:
            continue
        try:
            event: dict[str, Any] = orjson.loads(line)
        except orjson.JSONDecodeError:
            logger.warning("Skipping malformed JSONL line")
            continue
        etype = str(event.get("type", "")).lower()
        if not keep or etype in keep:
            yield event


class GridDataSource(DataSource):
    """DataSource backed by the GRID Esports API (Phase 3)."""

    def __init__(self) -> None:
        if not settings.grid_api_key:
            raise ValueError(
                "GRID_API_KEY must be set to use GridDataSource. "
                "Use RiotDataSource for demo/dev mode."
            )

    async def get_game(self, game_id: str) -> dict[str, Any]:
        # Phase 3: GraphQL Central Data query + Series Events JSONL streaming.
        # The JSONL stream is parsed via stream_grid_events() above.
        logger.warning("GridDataSource.get_game is a Phase 3 stub — returning empty dict")
        return {}

    async def get_match_history(
        self,
        player_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        # Phase 3: GraphQL Central Data for historical series list.
        logger.warning("GridDataSource.get_match_history is a Phase 3 stub — returning []")
        return []
