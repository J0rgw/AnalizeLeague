# System Architecture — AnalizeLeague

## Data flow

```
┌─────────────────────────────────┐
│  Riot API  /  GRID Esports      │  External data sources
└──────────────┬──────────────────┘
               │ raw dict payload
               ▼
┌──────────────────────────────────────────────────┐
│  DataSource (abstract — app/ingest/base.py)      │
│  ├── RiotDataSource  (dev, riot.py)              │
│  └── GridDataSource  (prod, grid.py)             │
└──────────────┬───────────────────────────────────┘
               │ raw dict payload
               ▼
┌──────────────────────────────────────────────────┐
│  build_digest()  (app/digest/builder.py)         │
│  Polars dataframe operations:                    │
│    - gold diff per lane and team                 │
│    - lane state snapshots (min 8/14/20)          │
│    - fight detection and classification          │
│    - jungle path reconstruction (approx., from   │
│      jungleMinionsKilled deltas + positions)     │
│    - objective + tradeoff pairing                │
│    - recall sync analysis                        │
│    - ban championIds → names via Data Dragon     │
│      (app/digest/champions.py, cached on disk)   │
└──────────────┬───────────────────────────────────┘
               │ GameDigest (~2 KB JSON)
               ├──────────────────────────────────────┐
               ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  DuckDB  (app/storage/db.py)    │    │  Ollama  (app/llm/agent.py)     │
│  save_game() / get_game() /     │    │  Local LLM inference only       │
│  list_games() / get_all_digests │    │  generate_agenda(digest)        │
│  Derived tables: games,         │    │  answer_question(question,conn) │
│  lane_states, objectives,       │    │    — two-stage text-to-SQL,     │
│  fights                         │    │      gated by app/llm/sql.py    │
└─────────────────────────────────┘    └──────────────┬──────────────────┘
                                                      │ prose output
                                                      ▼
                                       ┌─────────────────────────────────┐
                                       │  FastAPI  (app/api/)            │
                                       │  GET  /games                    │
                                       │  GET  /games/{id}/digest        │
                                       │  GET  /games/{id}/agenda        │
                                       │  POST /ask                      │
                                       │  GET  /health                   │
                                       │  (POST /debrief, POST /query    │
                                       │   kept as deprecated shims)     │
                                       └──────────────┬──────────────────┘
                                                      │ JSON response
                                                      ▼
                                       ┌─────────────────────────────────┐
                                       │  Frontend (Next.js App Router)  │
                                       │  Landing, scrim list,           │
                                       │  debrief view, Q&A page         │
                                       └─────────────────────────────────┘
```

## Layer responsibilities

| Layer    | Module                      | Responsibility                                        |
|----------|-----------------------------|-------------------------------------------------------|
| Ingest   | `app/ingest/`               | Fetch raw data, abstract over data source             |
| Digest   | `app/digest/`               | Calculate compact GameDigest (Python/Polars)          |
| Storage  | `app/storage/db.py`         | Persist and query GameDigest records (DuckDB)         |
| LLM      | `app/llm/agent.py`          | Prompt construction and local Ollama inference        |
| API      | `app/api/`                  | HTTP interface, request/response validation           |
| Config   | `app/config.py`             | Centralized settings (pydantic-settings from .env)    |

## Why the LLM only receives the compact digest

Raw Riot/GRID payloads are 200–500 KB. Sending them to an LLM would:

1. **Exceed context windows** of many local models (7B/13B quantized).
2. **Force unreliable quantitative reasoning** — LLMs are poor calculators.
3. **Leak unnecessary data** — player names, item builds, raw coordinates.

By pre-computing everything in Python, we get:
- Reproducible, auditable results (deterministic calculations).
- Fast inference — the LLM prompt is tiny.
- A small local model that performs like a large one.

## DataSource abstraction

`app/ingest/base.py` defines the `DataSource` abstract class.
Switching from Riot API (demo) to GRID (production) requires only instantiating
a different concrete class. The digest, storage, and LLM layers are unaffected.

```
DataSource (abstract)
├── RiotDataSource   ← ENV=dev, uses RIOT_API_KEY
└── GridDataSource   ← ENV=prod, uses GRID_API_KEY
```

## Phase roadmap

| Phase | Status | Scope |
|-------|--------|-------|
| 1 | done | Skeleton, settings, `DataSource` abstract, `/health`. |
| 2 | done | `build_digest()`, Ollama agent (`generate_agenda` + `answer_question` with mechanical fallback), DuckDB persistence (`games`, `lane_states`, `objectives`, `fights`), Next.js frontend (landing, scrim list, debrief view, Q&A page). |
| 2.5 (hardening) | done | Loopback validator on `OLLAMA_HOST`, `/ask` input bounds, `game_id` regex, Ollama timeouts, narrow exception handling, env-driven CORS. Two-stage text-to-SQL Q&A gated by `app/llm/sql.py`. Position-based `jungle_path` (no fake `MONSTER_KILL` events). Champion-name resolver via cached Data Dragon. CWD-independent cache + DuckDB paths. Version single-sourced from `pyproject.toml`. |
| 3 | in progress | `GridDataSource.stream_grid_events` JSONL parser shipped; HTTP fetcher is a stub awaiting a GRID partnership. |
