# Product Brief — AnalizeLeague

## What it is

An AI assistant for professional League of Legends analysts and coaches.
It transforms raw game data into structured insights, saving hours of replay review.

**Not** a stats dashboard. Does not compete with op.gg, Porofessor, DPM, or Itero.
Those tools surface what happened. This tool surfaces **what to review and why**.

## Two core features

### 1. Post-game Debrief (`POST /debrief`)

Given a game ID, generates a ranked "review agenda" of the 6–8 moments that matter,
each with a timestamp and a description of what to look for.

Flow:
1. Fetch raw game data from a DataSource (Riot API in dev, GRID in prod).
2. Calculate a compact GameDigest in Python (gold diffs, lane states, fights, etc.).
3. Send only the GameDigest (~2 KB) to a local Ollama LLM.
4. Return structured prose analysis to the coach/analyst.

### 2. Historical Q&A (`POST /query`)

Ask natural-language questions about a game or trends across scrim history.

Flow:
1. Load stored GameDigest(s) from DuckDB.
2. Send digest + question to the local Ollama LLM.
3. Return a focused prose answer.

Example questions:
- "When did we lose map control in game 3?"
- "How does our jungle pathing compare this week vs last week?"
- "What did we trade for Baron and was it worth it?"

## Key differentiator

### GRID data (production)
In production, the backend connects to scrim data via GRID (official Riot partner).
GRID provides ward positions, sub-second positional data, and live event streaming —
capabilities the Riot API cannot provide. No public tool has access to this.

### Local LLM privacy
All inference runs locally via Ollama. Scrim data never leaves the team's machine.
This is a strong trust and competitive-intelligence argument for professional teams.

## Design principle

**"Calculate in code, narrate with LLM."**

The LLM is a narration engine, not a reasoning engine. All quantitative analysis
(gold calculations, fight detection, objective scoring) happens deterministically
in Python using Polars. The LLM only receives the finished compact digest.

Benefits:
- A small local model (llama3.1 7B) performs like a much larger one.
- Results are reproducible and auditable — calculations don't rely on LLM "reasoning".
- Prompt tokens stay minimal, keeping inference fast and cost-free.

## Constraints (non-negotiable)

| Constraint | Why |
|-----------|-----|
| Zero cost | No paid APIs in dev/demo mode |
| Local LLM via Ollama | Privacy — scrim data stays on team's machine |
| Riot API for demo | Free, no partnership required |
| GRID for production | Granular data that Riot API cannot provide |
