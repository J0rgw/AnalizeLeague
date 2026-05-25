"""
Seed script: ingest 3–5 real games via RiotDataSource, build digests, store in DuckDB.

Usage (run from /backend):
    # By Riot ID (gameName#tagLine) — looks up recent ranked games:
    uv run python scripts/seed.py --riot-id "PlayerName#EUW"

    # By PUUID directly:
    uv run python scripts/seed.py --puuid <puuid> --limit 5

    # By explicit match IDs:
    uv run python scripts/seed.py --match-ids EUW1_7012345678 EUW1_7012345679

Requires RIOT_API_KEY to be set in backend/.env
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("seed")


async def _run(args: argparse.Namespace) -> int:
    from app.digest.builder import build_digest
    from app.ingest.riot import RiotDataSource
    from app.storage.db import init_db, save_game

    src = RiotDataSource()
    db = init_db()

    try:
        match_ids: list[str] = []

        if args.match_ids:
            match_ids = args.match_ids

        elif args.puuid:
            logger.info("Fetching match history for PUUID %s", args.puuid)
            history = await src.get_match_history(args.puuid, limit=args.limit)
            match_ids = [h["match_id"] for h in history]

        elif args.riot_id:
            game_name, tag_line = args.riot_id.rsplit("#", 1)
            logger.info("Resolving Riot ID: %s#%s", game_name, tag_line)
            puuid = await src.get_puuid(game_name, tag_line)
            logger.info("PUUID: %s", puuid)
            history = await src.get_match_history(puuid, limit=args.limit)
            match_ids = [h["match_id"] for h in history]

        else:
            logger.error("Provide --riot-id, --puuid, or --match-ids")
            return 1

        if not match_ids:
            logger.error("No match IDs found. Check your API key and player ID.")
            return 1

        logger.info("Processing %d games: %s", len(match_ids), match_ids)
        ingested = 0

        for match_id in match_ids:
            try:
                logger.info("--- Ingesting %s ---", match_id)
                raw = await src.get_game(match_id)
                digest = build_digest(raw, analyzed_side=args.side)
                save_game(db, digest)
                logger.info(
                    "Saved %s | patch=%s | result=%s | fights=%d",
                    match_id,
                    digest.meta.patch,
                    digest.meta.result,
                    len(digest.fights),
                )
                ingested += 1
                await asyncio.sleep(0.5)  # rate-limit courtesy
            except Exception as exc:
                logger.error("Failed to ingest %s: %s", match_id, exc)

        logger.info("Done. Ingested %d/%d games.", ingested, len(match_ids))
        return 0

    finally:
        await src.aclose()
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed DuckDB with real Riot API games.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--riot-id",
        metavar="NAME#TAG",
        help="Riot ID (gameName#tagLine) to look up match history",
    )
    group.add_argument("--puuid", help="PUUID to look up match history")
    group.add_argument(
        "--match-ids",
        nargs="+",
        metavar="MATCH_ID",
        help="One or more explicit match IDs (e.g. EUW1_7012345678)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max number of recent games to fetch (default: 5)",
    )
    parser.add_argument(
        "--side",
        choices=["blue", "red"],
        default="blue",
        help="Which team to analyze (default: blue)",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
