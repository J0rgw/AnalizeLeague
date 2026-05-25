# Data Sources — Riot API vs GRID

## Riot API (demo / development mode)

**Access**: Free developer key at https://developer.riotgames.com/  
**Key lifecycle**: Expires every 24 hours — must be renewed manually.  
**Rate limits**: 20 requests/second, 100 requests/2 minutes (development key).  
**Config**: Set `RIOT_API_KEY` in `.env`.

### What it provides

- **Match history** — `GET /lol/match/v5/matches/by-puuid/{puuid}/ids`
- **Match details** — `GET /lol/match/v5/matches/{matchId}` (participant stats, objectives, kills)
- **Match timeline** — `GET /lol/match/v5/matches/{matchId}/timeline` (frame-by-frame events)

Timeline frames provide: gold, XP, CS per player at 1-minute intervals; kill, objective,
item, and ward events with timestamps.

### Honest limitations

| Limitation | Impact |
|-----------|--------|
| **Ward positions**: Riot API provides ward placement counts and timing only — **no map coordinates**. Vision control maps cannot be reconstructed. | Cannot show where vision was / wasn't. |
| **Champion positions**: 1-minute interval snapshots only. | Cannot reconstruct fights below 60-second granularity. |
| **No live data**: Available only after the game ends. | No real-time coaching. |
| **Key expiry**: 24-hour TTL on dev keys. | Manual renewal required. |

---

## GRID Esports (production mode)

**Access**: Requires a GRID Esports partnership agreement.  
**Contact**: https://grid.gg  
**Config**: Set `GRID_API_KEY` in `.env`.  
**Adapter**: `backend/app/ingest/grid.py` (Phase 3 implementation).

GRID is an official Riot esports data partner. It provides data for professional
and semi-professional tournaments and scrim environments.

### Three access modes

#### 1. Central Data (GraphQL)
Historical stats aggregated per series/game.

- Champion picks/bans, player stats, match results
- Aggregations across multiple games (patch trends, champion win rates)
- Good for: match history, player performance over time

#### 2. Series State (GraphQL)
Structured in-game state at discrete time points.

- More granular than Riot API timeline frames
- Per-player per-minute stats with higher resolution
- Good for: detailed lane state analysis, objective control snapshots

#### 3. Series Events (JSONL streaming / WebSocket)
High-frequency positional event stream during (or after) games.

- **Ward positions with exact map coordinates** ← key differentiator
- Champion positions at sub-second granularity
- Jungle camp spawn/clear events for exact pathing reconstruction
- Good for: vision control maps, exact fight reconstruction, jungle pathing

### What GRID adds over Riot API

| Capability                       | Riot API         | GRID                     |
|----------------------------------|------------------|--------------------------|
| Ward positions (map coordinates) | No               | Yes — Series Events      |
| Champion positions (granular)    | 1-min frames     | Sub-second — Series Events|
| Jungle camp clear timestamps     | Approximate      | Exact — Series Events    |
| Historical aggregates            | Limited          | Yes — Central Data       |
| Live streaming during game       | No               | Yes — Series Events      |
| Scrim data access                | No               | Yes (with agreement)     |

### Cost model
GRID access is negotiated per partnership. For the demo, the Riot API (free) is used.
GRID is the production upgrade path — no code changes are needed beyond swapping
`RiotDataSource` for `GridDataSource` (the `DataSource` interface is the same).

---

## DataSource interface

Both sources implement `app.ingest.base.DataSource`:

```python
class DataSource(abc.ABC):
    async def get_game(self, game_id: str) -> dict[str, Any]: ...
    async def get_match_history(self, player_id: str, *, limit: int = 20) -> list[dict[str, Any]]: ...
```

Switching data sources in production requires only changing which concrete class
is instantiated. The digest builder, storage layer, and LLM agent are unaffected.
