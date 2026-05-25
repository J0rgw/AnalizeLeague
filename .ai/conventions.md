# Code Conventions — AnalizeLeague

## Language

All code, identifiers, comments, docstrings, commit messages, and documentation
are written in **English**. No exceptions — including variable names, function names,
and inline comments.

## Type strictness

### Backend (Python)
- **mypy strict mode**: every function must have complete type annotations.
- `from __future__ import annotations` at the top of every file (enables forward references, deferred evaluation).
- No `Any` without an explicit comment explaining why.
- Run: `uv run mypy app`

### Frontend (TypeScript — Phase 2)
- `"strict": true` in `tsconfig.json`.
- No `any` without a comment.
- Prefer `unknown` over `any` for untyped external data.

## Formatting and linting

### Python
Tool: **ruff** (replaces black + isort + flake8).  
Config: root `pyproject.toml` `[tool.ruff]` section.

```powershell
uv run ruff format .     # format
uv run ruff check .      # lint
uv run ruff check --fix .  # auto-fix safe issues
```

### TypeScript (Phase 2)
ESLint + Prettier via Next.js defaults.

## Package management

- **Always use uv**. Never use `pip`, `pip install`, or `requirements.txt`.
- Add a dependency: `uv add <package>`
- Add a dev dependency: `uv add --group dev <package>`
- Install from lockfile: `uv sync`

## Commit messages — Conventional Commits

Format: `<type>(<scope>): <description>`

**Types**:
| Type | Use for |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `docs` | Documentation only |
| `test` | Tests only |
| `chore` | Tooling, deps, CI |

**Scopes**: `backend`, `frontend`, `infra`, `docs`, `ai-docs`

**Examples**:
```
feat(backend): implement build_digest() gold diff calculation
fix(backend): handle missing GRID_API_KEY gracefully on startup
docs(ai-docs): update digest-schema.md with recall sync field
test(backend): add integration tests for /debrief endpoint
chore(backend): bump fastapi to 0.116
```

## Stub pattern

Unimplemented Phase 1 functions raise `NotImplementedError` with a message that names
the target phase and the module. They do NOT return empty values silently — silent
failures hide integration bugs.

```python
raise NotImplementedError(
    "function_name is a Phase 1 stub. Implement in Phase 2. "
    "See app/module/file.py and /.ai/architecture.md."
)
```

## Environment variables

All config is accessed via `app.config.settings` (pydantic-settings singleton).
Never call `os.environ` directly in application code.
Never hardcode API keys, hostnames, or file paths in source code.

## No business logic in stubs

Phase 1 stubs define signatures, docstrings, and TODOs. They do not contain partial
implementations. An incomplete implementation is worse than no implementation because
it creates false confidence and hidden bugs.

## File and module layout

- All Python source under `backend/app/`.
- Tests under `backend/tests/` — mirrors the `app/` structure.
- No `src/` layout — flat layout with `packages = ["app"]` in hatchling config.
- One module per concern: do not add new functionality to existing modules without
  updating this document.
