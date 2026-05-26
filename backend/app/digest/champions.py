"""
Champion-ID → canonical-name resolver backed by Riot's Data Dragon CDN.

Why this exists: the Riot match-v5 payload reports bans as numeric champion
IDs (e.g. 157), not display names. Rendering "157" in the UI is unfriendly.
Data Dragon is a public, anonymous CDN; resolving names here is cheap and
keeps the rest of the codebase free of HTTP calls.

Design notes:
  * Cache aggressively on disk under /data/cache/ddragon/ so the demo runs
    fully offline after the first successful fetch.
  * Never raise — if the network and the cache both fail, fall back to
    str(champion_id). The digest schema stays intact (list[str]); only
    the values are uglier.
  * The actual HTTP call lives in `_fetch_champion_json`, which tests can
    monkey-patch to avoid touching the network.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DDRAGON_URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
_DEFAULT_VERSION = "14.10.1"

# repo_root/data/cache/ddragon — anchored to the file so CWD doesn't matter.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CACHE_DIR = _REPO_ROOT / "data" / "cache" / "ddragon"

# In-process memoization keyed by Data Dragon version.
_NAME_CACHE: dict[str, dict[int, str]] = {}


def _version_for_patch(patch: str | None) -> str:
    """Map a Riot game patch like '14.10' to a Data Dragon version like '14.10.1'."""
    if not patch:
        return _DEFAULT_VERSION
    parts = patch.split(".")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}.{parts[1]}.1"
    return _DEFAULT_VERSION


def _parse_ddragon(raw: dict[str, Any]) -> dict[int, str]:
    """Extract {championId: name} from a Data Dragon champion.json payload."""
    out: dict[int, str] = {}
    for entry in raw.get("data", {}).values():
        key = entry.get("key")
        # In DDragon, "id" is the canonical display name (e.g. "Aatrox"),
        # while "name" is the localized name. We want the canonical one.
        name = entry.get("id")
        if key is None or name is None:
            continue
        try:
            out[int(key)] = str(name)
        except (TypeError, ValueError):
            continue
    return out


def _load_from_disk(version: str) -> dict[int, str] | None:
    fp = _CACHE_DIR / f"champion_{version}.json"
    if not fp.exists():
        return None
    try:
        raw = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("DDragon cache unreadable (%s): %s", fp, exc)
        return None
    return _parse_ddragon(raw)


def _save_to_disk(version: str, raw: dict[str, Any]) -> None:
    fp = _CACHE_DIR / f"champion_{version}.json"
    try:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(json.dumps(raw), encoding="utf-8")
    except OSError as exc:
        logger.warning("DDragon cache not writable (%s): %s", fp, exc)


def _fetch_champion_json(version: str) -> dict[str, Any] | None:
    """Synchronous network fetch. Returns None on any error. Patched in tests."""
    url = _DDRAGON_URL.format(version=version)
    try:
        resp = httpx.get(url, timeout=10.0)
        resp.raise_for_status()
        parsed: Any = resp.json()
        if isinstance(parsed, dict):
            return parsed
        return None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("DDragon fetch failed (%s): %s", url, exc)
        return None


def _load_or_fetch(version: str) -> dict[int, str]:
    cached = _NAME_CACHE.get(version)
    if cached is not None:
        return cached
    from_disk = _load_from_disk(version)
    if from_disk is not None:
        _NAME_CACHE[version] = from_disk
        return from_disk
    raw = _fetch_champion_json(version)
    if raw is None:
        # Negative cache the failure so we don't hammer the CDN every ban.
        _NAME_CACHE[version] = {}
        return {}
    parsed = _parse_ddragon(raw)
    _save_to_disk(version, raw)
    _NAME_CACHE[version] = parsed
    return parsed


def resolve_champion_name(champion_id: int | str, patch: str | None = None) -> str:
    """
    Return the canonical champion name, or `str(champion_id)` if the lookup
    cannot be satisfied (network down AND no cache). Never raises.

    An empty/None `champion_id` returns "" — matches the historical behaviour
    of the bans list, which uses "" as a placeholder for an absent ban.
    """
    if champion_id in ("", None):
        return ""
    try:
        cid_int = int(champion_id)
    except (TypeError, ValueError):
        return str(champion_id)
    version = _version_for_patch(patch)
    try:
        table = _load_or_fetch(version)
    except Exception as exc:  # noqa: BLE001 — last-resort guard, never crash the digest
        logger.warning("Champion resolver crashed (%s) — degrading", exc)
        return str(cid_int)
    return table.get(cid_int, str(cid_int))


def clear_cache() -> None:
    """Reset the in-process memoization. Used by tests."""
    _NAME_CACHE.clear()
