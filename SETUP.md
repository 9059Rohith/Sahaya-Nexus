# Setup

## Local Python and Node

Copy `backend/.env.example` to `backend/.env` if you need to customize settings. The default SQLite database is `backend/sahaya.db`. Run migrations before launching the API.

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.cli create-admin
.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/alembic upgrade head
.venv/bin/python -m app.cli create-admin
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then in `frontend`: `npm ci && npm run dev`. Next.js proxies to `127.0.0.1:8000` by default. Set `API_INTERNAL_URL` if your API lives elsewhere. Use a unique `SECRET_KEY` and HTTPS before deployment.

The frontend is at `http://localhost:3000`; API docs are at `http://127.0.0.1:8000/docs`; health is `/api/v1/health`. No external AI process is required.

## Docker

Copy `.env.example` to `.env`, replace `POSTGRES_PASSWORD` and `SECRET_KEY` with long random secrets, then `docker compose up --build -d`. Create the first admin with `docker compose exec api python -m app.cli create-admin`. PostGIS, Redis, the API, maintenance worker and frontend start together; the database and private files use named volumes. Redis only holds short lived rate counters. No seed command is needed or supplied.

To enable local voice transcription, run `docker compose exec api python -m app.cli prepare-speech`. This one-time command downloads the open speech model into the private data volume. Typed intake works before and after the download.

## Isolated browser tests

Playwright refuses to run against the normal port 3000. Start a separate API on port 8100 with `APP_MODE=test` and `DATABASE_URL=sqlite:///./qa-e2e.db`, migrate that SQLite database with Alembic, and start a separate Next.js process on port 3100 with `API_INTERNAL_URL=http://127.0.0.1:8100`. Set `E2E_BASE_URL=http://localhost:3100`, `E2E_API_URL=http://127.0.0.1:8100`, and `E2E_DB_URL=sqlite:///./qa-e2e.db`, then run `npm run test:e2e` in `frontend`. The full lifecycle and offline tests check that the API runs in test mode, create disposable test accounts and use a guarded CLI to promote the QA operator. They refuse any database other than `qa-e2e.db`. Do not point E2E at an installation with real records.

For the PostGIS path, create a separate database named `sahaya_qa`, migrate it, and run `python -m scripts.postgis_smoke` with `DATABASE_URL` ending in `/sahaya_qa`. The script has a hard guard against any other database. Remove the QA database after verification; never seed the normal `sahaya` database.

## Optional local LLM

Set `OLLAMA_URL` to an existing local Ollama HTTP endpoint and `OLLAMA_MODEL` to an installed model. A timeout or malformed model response falls back to rule-based interpretation. AI output is always shown for human review and cannot mutate request state.
