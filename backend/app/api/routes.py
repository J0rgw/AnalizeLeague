"""
API route handlers.

Phase 1: all business routes return HTTP 501 Not Implemented.
They define the contract (request/response shapes); implementation is Phase 2.

Route summary:
  POST /debrief  — generate post-game analysis from a game ID
  POST /query    — answer a natural-language question about a stored game
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DebriefRequest(BaseModel):
    game_id: str
    data_source: str = "riot"   # "riot" | "grid"


class DebriefResponse(BaseModel):
    game_id: str
    debrief: str


class QueryRequest(BaseModel):
    game_id: str
    question: str


class QueryResponse(BaseModel):
    game_id: str
    answer: str


@router.post("/debrief", response_model=DebriefResponse)
async def post_debrief(body: DebriefRequest) -> DebriefResponse:
    """
    Generate a post-game debrief.

    Phase 2 steps:
      1. Select DataSource based on body.data_source ("riot" | "grid").
      2. Fetch raw game data via DataSource.get_game(body.game_id).
      3. Build GameDigest via build_digest().
      4. Persist via save_game().
      5. Generate prose via generate_debrief().
    """
    raise HTTPException(status_code=501, detail="Not implemented — Phase 2")


@router.post("/query", response_model=QueryResponse)
async def post_query(body: QueryRequest) -> QueryResponse:
    """
    Answer a natural-language question about a stored game.

    Phase 2 steps:
      1. Load stored GameDigest from DuckDB via query_history().
      2. Generate answer via answer_query(digest, body.question).
    """
    raise HTTPException(status_code=501, detail="Not implemented — Phase 2")
