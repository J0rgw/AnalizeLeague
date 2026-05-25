# CLAUDE.md — AnalizeLeague project context for AI agents

Read this file first. It gives you everything needed to work on this codebase.

## What this project is

AI assistant for professional League of Legends analysts/coaches.
Saves hours of replay review. NOT a stats dashboard (does not compete with op.gg/Porofessor).

Two endpoints (Phase 2 implementation):
- `POST /debrief` → ranked list of 6–8 game moments worth reviewing, each with timestamp
- `POST /query` → natural-language Q&A over historical scrim data

## Core design principle

**"Calculate in code, narrate with LLM."**

All heavy computation (gold diffs, lane states, fight detection, objective tracking,
jungle pathing) happens in Python using Polars. The LLM only receives a compact
GameDigest (~2 KB JSON) and returns prose. This lets a small local model perform
like a large one.

## Non-negotiable constraints

| Constraint | Why |
|-----------|-----|
| Zero cost — no paid APIs in dev | Budget constraint |
| LLM runs locally via Ollama | Scrim data privacy (sales argument) |
| Scrim data never sent to external LLM APIs | Hard requirement |
| `uv` only — never `pip` or `requirements.txt` | Package manager convention |

## Stack

- Python 3.12 (pinned via `.python-version`)
- uv (package manager)
- FastAPI + uvicorn
- Polars (dataframe operations in digest builder)
- DuckDB (local persistence)
- Ollama (local LLM client)
- Frontend (Phase 2): Next.js App Router + TypeScript + Tailwind

## Monorepo layout

```
/backend        Active Python package — all Phase 1 work is here
/frontend       Phase 2 placeholder (only a README.md exists)
/data           Gitignored — DuckDB file and raw game data live here
/.ai/           Design docs for AI agents (read before touching domain logic)
CLAUDE.md       This file
.env.example    Template for environment variables
```

## Key commands (run from /backend)

```powershell
uv sync                                          # install/update all deps
uv run uvicorn app.api.main:app --reload         # start dev server (port 8000)
uv run pytest -v                                 # run test suite
uv run ruff format . && uv run ruff check .      # format + lint
uv run mypy app                                  # type check
```

## Environment setup

All config is driven by `.env`. Copy `.env.example` to `backend/.env` and fill in values.
Commands are run from `/backend`, so pydantic-settings resolves `.env` relative to `/backend`.

Required variables: `RIOT_API_KEY`, `OLLAMA_HOST`, `OLLAMA_MODEL`, `DUCKDB_PATH`, `ENV`
Optional (production): `GRID_API_KEY`

## Entry points

| Purpose | File |
|---------|------|
| FastAPI app | `backend/app/api/main.py` |
| Settings | `backend/app/config.py` |
| Abstract data source | `backend/app/ingest/base.py` |
| Riot API adapter | `backend/app/ingest/riot.py` |
| GRID adapter (prod) | `backend/app/ingest/grid.py` |
| Digest builder | `backend/app/digest/builder.py` |
| Digest Pydantic models | `backend/app/digest/models.py` |
| DuckDB layer | `backend/app/storage/db.py` |
| Ollama agent | `backend/app/llm/agent.py` |
| API routes | `backend/app/api/routes.py` |

## Phase status

- **Phase 1** (current): skeleton only. All business logic is `NotImplementedError` stubs.
  Only `/health` works. Tests pass (2 tests).
- **Phase 2**: implement digest builder, Ollama prompts, DuckDB persistence, frontend.
- **Phase 3**: GRID adapter for production data.

## Agent documentation (read before implementing domain logic)

| Doc | Contents |
|-----|----------|
| `/.ai/product.md` | Product brief, two core features, differentiator |
| `/.ai/architecture.md` | Data flow, layer responsibilities |
| `/.ai/digest-schema.md` | Canonical GameDigest JSON contract (backend ↔ frontend) |
| `/.ai/data-sources.md` | Riot API vs GRID — capabilities and limitations |
| `/.ai/conventions.md` | Coding style, commit format, type rules |
