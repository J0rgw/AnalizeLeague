# Frontend

Frontend is initialized in Phase 2.

**Stack**: Next.js (App Router) + TypeScript + Tailwind CSS

## Initialization (Phase 2)

```powershell
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir
```

## API target

The frontend communicates with the backend API running at `http://localhost:8000`.

See `/.ai/digest-schema.md` for the shared data contract between backend and frontend.
