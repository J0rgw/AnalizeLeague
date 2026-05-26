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

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.ingest.base import DataSource

logger = logging.getLogger(__name__)

_BASE_URL = "https://{region}.api.riotgames.com"
# Anchor the cache to the repo root regardless of CWD.
# riot.py lives at backend/app/ingest/riot.py → parents[3] is the repo root.
_CACHE_ROOT = Path(__file__).resolve().parents[3] / "data" / "cache"


class _RateLimitError(Exception):
    """Raised when Riot API responds with HTTP 429."""


class RiotDataSource(DataSource):
    """DataSource backed by the Riot Games REST API (match-v5)."""

    def __init__(self, region: str | None = None) -> None:
        r = region or settings.riot_region
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL.format(region=r),
            headers={"X-Riot-Token": settings.riot_api_key},
            timeout=30.0,
        )
        _CACHE_ROOT.mkdir(parents=True, exist_ok=True)

    @retry(
        retry=retry_if_exception_type(_RateLimitError),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _get(self, path: str) -> Any:  # noqa: ANN401 — external API response shape varies
        resp = await self._client.get(path)
        if resp.status_code == 429:
            wait_s = int(resp.headers.get("Retry-After", "5"))
            logger.warning("Rate limited; sleeping %ds", wait_s)
            await asyncio.sleep(wait_s)
            raise _RateLimitError()
        resp.raise_for_status()
        return resp.json()

    async def get_game(self, game_id: str) -> dict[str, Any]:
        """
        Fetch match details + timeline for game_id.

        Returns dict with keys: "game_id", "match", "timeline".
        Raw responses are cached to /data/cache/{game_id}/ on first fetch.
        """
        cache_dir = _CACHE_ROOT / game_id
        match_f = cache_dir / "match.json"
        timeline_f = cache_dir / "timeline.json"

        if match_f.exists() and timeline_f.exists():
            logger.debug("Cache hit: %s", game_id)
            match_data: dict[str, Any] = json.loads(match_f.read_text(encoding="utf-8"))
            timeline_data: dict[str, Any] = json.loads(timeline_f.read_text(encoding="utf-8"))
        else:
            logger.info("Fetching %s from Riot API", game_id)
            cache_dir.mkdir(parents=True, exist_ok=True)
            match_data = await self._get(f"/lol/match/v5/matches/{game_id}")
            await asyncio.sleep(0.6)  # stay inside 20 req/s rate limit
            timeline_data = await self._get(f"/lol/match/v5/matches/{game_id}/timeline")
            match_f.write_text(json.dumps(match_data), encoding="utf-8")
            timeline_f.write_text(json.dumps(timeline_data), encoding="utf-8")
            logger.info("Cached %s", game_id)

        return {"game_id": game_id, "match": match_data, "timeline": timeline_data}

    async def get_match_history(
        self,
        player_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Return recent ranked match IDs for the given PUUID."""
        ids: list[str] = await self._get(
            f"/lol/match/v5/matches/by-puuid/{player_id}/ids?count={limit}&type=ranked"
        )
        return [{"match_id": mid} for mid in ids]

    async def get_puuid(self, game_name: str, tag_line: str) -> str:
        """Resolve a Riot ID (gameName#tagLine) to a PUUID."""
        data: dict[str, Any] = await self._get(
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        return str(data["puuid"])

    async def aclose(self) -> None:
        await self._client.aclose()
