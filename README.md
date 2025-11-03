# ConversaAI

ConversaAI is a small monorepo that demonstrates a voice-enabled assistant with a Next.js frontend and a Python agent backend. It integrates LiveKit for real-time voice, a PostgreSQL-backed provider database (local Postgres or Supabase), and simple provider-search tooling (JSON + optional embeddings).

This repository is intended as a developer-focused starter: run the frontend UI locally, start the Python agent to handle audio/transcription/agent logic, and load provider data for search and lookup.

## What you'll find here

- `frontend/` — Next.js app and UI components (chat, agent controls, session views).
- `agent-starter-python/` — Python agent using LiveKit Agents, SQLAlchemy and pgvector for embeddings.
- `data/providerlist.json` — sample provider dataset used by the loader and search tools.

## Quick start

Prerequisites:

- Node 18+ and pnpm (for the frontend)
- Python 3.10+ and a virtual environment (for the Python agent)

Frontend (development):

```bash
cd frontend
pnpm install
pnpm dev
# open http://localhost:3000
```

Python agent (development):

```bash
cd agent-starter-python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
# run the agent process (see agent-starter-python/README or src/agent.py for how to start)
```

Load provider data into Postgres (local or Supabase):

1. Configure `agent-starter-python/.env.local` with your database URL (see examples below).
2. From the repository root run:

```bash
./load_local_providers.sh
```

This script runs the Python loader which reads `data/providerlist.json`, computes embeddings, and upserts rows into Postgres.

## Environment variables

Keep secrets out of source control. `agent-starter-python/.gitignore` already excludes `.env*` files.

Important vars for the agent (in `agent-starter-python/.env.local`):

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — credentials for LiveKit
- `POSTGRES_URL` — SQLAlchemy-compatible DB URL, for example:

  - Local Postgres (example):
    `POSTGRES_URL=postgresql+psycopg://vox_user:password@localhost:5433/voxology`

  - Supabase (hosted) — use URL-encoding for the password and require SSL:
    `POSTGRES_URL=postgresql+psycopg://postgres:ENCODED_PW@db.<project-ref>.supabase.co:5432/postgres?sslmode=require`

  To URL-encode a password locally (macOS / zsh):

  ```bash
  python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=''))" 'your-raw-password'
  ```

The code in `agent-starter-python/src/database/client.py` will read `POSTGRES_URL` directly and create the SQLAlchemy engine.

## Project layout (high level)

```
frontend/                 # Next.js app, UI components and configs
agent-starter-python/     # Python agent, DB client, loader and models
data/                     # providerlist.json sample data
load_local_providers.sh   # helper to run the Python loader
```

## Troubleshooting

- If you see DNS/`nodename nor servname provided` errors when connecting to a hosted DB, double-check your `POSTGRES_URL` host and that your machine/network can reach the host. For Supabase ensure DNS resolves and `sslmode=require` is present.
- If authentication fails, URL-encode the password before inserting into the URL. Passwords with `@`, `:`, `/`, `#`, etc. must be percent-encoded.

If you want, I can help you verify a `POSTGRES_URL` (without you pasting the raw password) by walking through the encoding step and running the loader locally.

## Contributing

Contributions are welcome. If you find issues or want features, open an issue or PR. Keep secrets out of commits and add reproducible steps for bugs.

----

License: MIT (or the license of upstream components as applicable)
