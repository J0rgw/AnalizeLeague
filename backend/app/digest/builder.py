"""
Digest builder: converts raw game data (from any DataSource) into a
compact GameDigest suitable for LLM prompting.

Design principle: ALL heavy calculation happens here in Python code.
  - Gold diff calculation via Polars dataframe operations
  - Lane state snapshots at minutes 5, 10, 15
  - Fight detection (engagements with >= 1 kill)
  - Jungle path reconstruction from camp clear events
  - Objective tracking with tradeoff detection
  - Recall sync analysis

The LLM only receives the finished GameDigest, never raw API payloads.
See /.ai/architecture.md for the full data flow.
"""
from __future__ import annotations

import logging
from typing import Any

from app.digest.models import GameDigest

logger = logging.getLogger(__name__)


def build_digest(raw_game_data: dict[str, Any]) -> GameDigest:
    """
    Transform raw game data into a GameDigest.

    Args:
        raw_game_data: Unstructured payload from a DataSource.get_game() call.
                       Shape varies by data source (Riot vs GRID).

    Returns:
        A fully populated GameDigest instance ready for LLM prompting.

    Raises:
        NotImplementedError: Phase 1 stub. Implement in Phase 2.
    """
    # TODO (Phase 2): implement using Polars for dataframe operations:
    #   1. Parse timeline frames into a Polars DataFrame
    #   2. Calculate per-minute gold diffs for each lane and team total
    #   3. Snapshot lane states at minutes 5, 10, 15
    #   4. Detect fights: windows where >= 1 kill occurs, group nearby kills
    #   5. Reconstruct jungle paths from camp clear events
    #   6. Identify objective events and detect concurrent tradeoffs
    #   7. Parse recall events and check team synchronization
    raise NotImplementedError(
        "build_digest is a Phase 1 stub. Implement in Phase 2 using Polars. "
        "See app/digest/models.py for the output schema."
    )
