# CLAUDE.md — AnalizeLeague project context for AI agents

Read this file first. It gives you everything needed to work on this codebase.

## What this project is

AI assistant for professional League of Legends analysts/coaches.
Saves hours of replay review. NOT a stats dashboard (does not compete with op.gg/Porofessor).

Active endpoints consumed by the frontend (`backend/app/api/routes.py`):
- `GET  /games`                → summary list for the game selector
- `GET  /games/{id}/digest`    → full GameDigest for the detail view
- `GET  /games/{id}/agenda`    → LLM-generated ranked review agenda (cached in DuckDB)
- `POST /ask`                  → two-stage text-to-SQL Q&A over the derived tables
- `GET  /health`               → liveness probe

`POST /debrief` and `POST /query` are retained as `deprecated=True` shims for backwards
compatibility — do not build new functionality on them.

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
/backend        FastAPI + Polars + DuckDB + Ollama. Phase 1–3 features live here.
/frontend       Next.js App Router + TypeScript + Tailwind (landing, scrim list, debrief view, Q&A).
/data           Gitignored — DuckDB file, raw game cache, Data Dragon cache.
/.ai/           Design docs for AI agents (read before touching domain logic).
CLAUDE.md       This file.
PRODUCT.md      Brand / register / anti-references for the UI.
.env.example    Template for environment variables.
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
Optional: `RIOT_REGION` (default `europe`), `OLLAMA_TIMEOUT_S` (default 60), `ALLOWED_ORIGINS` (CSV, default `http://localhost:3000`), `ALLOW_REMOTE_LLM` (`1` to allow non-loopback `OLLAMA_HOST` — off by default to keep scrim data on-machine), `GRID_API_KEY` (production only).

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
| SQL validator (Q&A safety) | `backend/app/llm/sql.py` |
| Champion-name resolver (Data Dragon) | `backend/app/digest/champions.py` |

## Phase status

- **Phase 1** — done. Skeleton, settings, `DataSource` abstract, FastAPI scaffold, `/health`.
- **Phase 2** — done. `build_digest()` (Polars), `generate_agenda()` + `answer_question()` via Ollama with mechanical fallback, DuckDB persistence (`games`, `lane_states`, `objectives`, `fights`), active routes (`/games`, `/games/{id}/digest`, `/games/{id}/agenda`, `/ask`), Next.js frontend (landing, scrim list, debrief view with gold chart, Q&A page).
- **Phase 3** — in progress. `GridDataSource.stream_grid_events` JSONL parser is shipped; the HTTP fetcher remains a stub pending a GRID partnership.

Hardening passes on top of Phase 2 (all merged):
- Privacy validator on `OLLAMA_HOST` (loopback only unless `ALLOW_REMOTE_LLM=1`).
- `/ask` input bounded; `game_id` path params regex-validated.
- Ollama calls wrapped in `asyncio.wait_for(ollama_timeout_s)`; exception handlers split by failure class.
- CORS origins driven by `ALLOWED_ORIGINS` env.
- `POST /ask` rewritten as two-stage text-to-SQL with strict validator (`app/llm/sql.py`) over a whitelist of derived tables; destructive keywords and off-whitelist tables are rejected before execution.
- `jungle_path` rebuilt from `jungleMinionsKilled` deltas + position (Riot does not emit per-camp events).
- Bans resolved to champion names via cached Data Dragon (`app/digest/champions.py`).
- Cache + DuckDB paths anchored to repo root (no more `..` CWD dependency).
- Version is single-sourced from `backend/pyproject.toml` and read by `main.py` via `importlib.metadata`.

Current test count: **84 passing** (`uv run pytest -v`).

## Agent documentation (read before implementing domain logic)

| Doc | Contents |
|-----|----------|
| `/.ai/product.md` | Product brief, two core features, differentiator |
| `/.ai/architecture.md` | Data flow, layer responsibilities |
| `/.ai/digest-schema.md` | Canonical GameDigest JSON contract (backend ↔ frontend) |
| `/.ai/data-sources.md` | Riot API vs GRID — capabilities and limitations |
| `/.ai/conventions.md` | Coding style, commit format, type rules |
