# AnalizeLeague

> AI assistant for professional League of Legends analysts and coaches.
> Saves hours of replay review by surfacing what actually matters.

## What it does

Two core features:

1. **Post-game Debrief** (`POST /debrief`) — Given a game ID, generates a ranked
   "review agenda" of the 6–8 moments that matter, each with a timestamp and what
   to look for.

2. **Historical Q&A** (`POST /query`) — Ask natural-language questions about a game
   or trends across your scrim history.

## Privacy first

All LLM inference runs locally via [Ollama](https://ollama.ai). Scrim data never
leaves the team's machine. This is a hard requirement, not just an optimization.

## Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Backend  | Python 3.12, FastAPI, Polars, DuckDB    |
| LLM      | Ollama (local)                          |
| Data     | Riot API (demo) / GRID Esports (prod)   |
| Frontend | Next.js App Router + TypeScript (Phase 2)|

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Ollama](https://ollama.ai) — local LLM runtime

```powershell
# Pull a model (do this once)
ollama pull llama3.1
```

## Quick start

```powershell
# 1. Copy and configure environment
Copy-Item .env.example backend\.env
# Edit backend\.env with your RIOT_API_KEY

# 2. Install dependencies
cd backend
uv sync

# 3. Start the API
uv run uvicorn app.api.main:app --reload

# 4. Verify
Invoke-RestMethod http://localhost:8000/health
# → { status: ok }
```

## Running tests

```powershell
cd backend
uv run pytest -v
```

## Project layout

```
/backend    Python FastAPI application
/frontend   Next.js UI (Phase 2)
/data       DuckDB database and raw game files (gitignored)
/.ai/       Design docs for AI coding agents
```

See [CLAUDE.md](./CLAUDE.md) for the quick-reference guide used by AI assistants.
See [.ai/](/.ai/) for full architecture and design documentation.
