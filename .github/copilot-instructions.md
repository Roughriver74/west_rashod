# GitHub Copilot / AI agent instructions for West Potok (west_rashod)

Purpose: Short, actionable guide for an AI coding agent to be productive immediately in this repo.

## 🔭 Big picture

- **Architecture:** Monorepo with two main apps:
  - **backend/** — FastAPI service (entry: `backend/app/main.py`), DB models, Alembic migrations, Celery tasks. API prefix: **`/api/v1`**.
  - **frontend/** — Vite + React + TypeScript (scripts in `frontend/package.json`).
- **Background & scheduling:** sync scheduler + background task manager live in `app/services` and `backend/app/celery_app.py`. Uses Redis optionally (controlled by `USE_REDIS` in config).
- **Data flow:** 1C OData (config keys in `app/core/config.py`: `ODATA_1C_*`) → importer (`app/services/bank_transaction_1c_import.py`) → DB (Postgres). Fin module uses FTP downloads (`west_fin_source` / `app/modules/fin`).

## 🛠 How to run & debug (exact commands)

- Local all-in-one dev: from repo root
  - ./start-dev.sh all (starts DB via Docker Compose, backend and frontend; backend runs on **8005**, frontend **5178**)
- Run backend only (manual):
  - cd backend && uvicorn app.main:app --reload --port 8001
- Quick smoke test (from `QUICK_START.md`):
  - Get token: `POST /api/v1/auth/login` (see curl example in `QUICK_START.md`)
  - Start async sync: `POST /api/v1/sync-1c/bank-transactions/sync-async` (see JSON body example)
- Logs & debugging:
  - tail -f backend/logs/app.log
  - docker compose logs -f backend
  - ws debug: `wscat -c "ws://localhost:8001/api/v1/ws/tasks/<task_id>"`

## ✅ Migrations & deploy

- Migrations live in `backend/alembic/`. Typical commands:
  - `alembic revision --autogenerate -m "msg"`
  - `alembic upgrade head`
- Production migration & deploy helper: `migrate-db.sh` (syncs migration files and runs `alembic upgrade head` on the server). See `deploy/` and `DEPLOY_INSTRUCTIONS.md` for deployment specifics.

## 🔬 Tests

- Quick tests: `cd backend && python test_background_tasks.py` (project provides specific test scripts).
- Or run full test suite: `cd backend && pytest`
- Unit tests live alongside backend code (`backend/test_*.py`, `backend/app/...`)

## ⚙️ Config & env

- Settings object: `app/core/config.py` (Pydantic BaseSettings, `env_file = ".env"`).
- Important defaults (replace in production): `DATABASE_URL` (Postgres, default port **54330**), `SECRET_KEY`, `ODATA_1C_*` credentials, `USE_REDIS` flags.
- **Note:** defaults include local dev credentials — do not assume they are secure in prod; prefer `.env` or secret manager.

## 📐 Project-specific conventions

- **Language & style:** Project uses **English** for code & variable names; project-level AI doc `CLAUDE.md` asks assistants to reply in **Russian** for user-facing text. Follow `CLAUDE.md` for localization and tone.
- **Background tasks:** prefer use of `app.services.*` helpers, and task progress is reported via `/api/v1/tasks` + WebSocket events. See `app/services/async_sync_service.py` and `app/services/background_tasks.py`.
- **Celery:** optional; default broker is memory (fallback), enable `USE_REDIS` for production and workers (`celery -A app.celery_app worker -B` or similar).

## 🔗 Integration points to watch for when changing code

- 1C OData client (`app/services/odata_1c_client.py`) — external API timeouts and auth tokens are in config.
- DB migrations (`alembic/versions`) must be added when changing `app/db/models.py`.
- WebSocket/API contract: changes to tasks endpoints affect front-end components in `frontend/src/components` (e.g., `TaskProgress`, `SyncModal`).

## 🔎 Good-first tasks for agents

- Add a missing test for `app.services.bank_transaction_1c_import` using small test DB fixtures.
- Improve health-checks and add a lightweight integration test for `/api/v1/sync-1c/...` that mocks OData client.

## Files to reference (fast scanning)

- `QUICK_START.md`, `CLAUDE.md`, `DEPLOY_INSTRUCTIONS.md`, `start-dev.sh`, `migrate-db.sh`
- Backend: `backend/app/main.py`, `backend/app/celery_app.py`, `backend/alembic/`, `backend/app/services/`
- Frontend: `frontend/package.json`, `frontend/src/components/`

---

Если нужно, могу сократить/переформатировать этот файл, добавить больше примеров `curl`/`pytest` или специфичные инструкции по PR/commit message style — скажите, что непонятно или чего не хватает.
