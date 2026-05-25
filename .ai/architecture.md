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
│    - lane state snapshots (min 5/10/15)          │
│    - fight detection and classification          │
│    - jungle path reconstruction                  │
│    - objective + tradeoff pairing                │
│    - recall sync analysis                        │
└──────────────┬───────────────────────────────────┘
               │ GameDigest (~2 KB JSON)
               ├──────────────────────────────────────┐
               ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  DuckDB  (app/storage/db.py)    │    │  Ollama  (app/llm/agent.py)     │
│  save_game() / query_history()  │    │  Local LLM inference only        │
└─────────────────────────────────┘    │  generate_debrief()             │
                                       │  answer_query()                 │
                                       └──────────────┬──────────────────┘
                                                      │ prose output
                                                      ▼
                                       ┌─────────────────────────────────┐
                                       │  FastAPI  (app/api/)            │
                                       │  POST /debrief                  │
                                       │  POST /query                    │
                                       │  GET  /health                   │
                                       └──────────────┬──────────────────┘
                                                      │ JSON response
                                                      ▼
                                       ┌─────────────────────────────────┐
                                       │  Frontend  (Phase 2)            │
                                       │  Next.js App Router             │
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

| Phase | Scope |
|-------|-------|
| 1 (current) | Skeleton only. /health works. All business logic is stubs. |
| 2 | Implement build_digest(), Ollama prompts, DuckDB persistence, frontend. |
| 3 | Implement GridDataSource for production GRID data. |
