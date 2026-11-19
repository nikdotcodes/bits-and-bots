# Bits and Bots Code Club

FastAPI/Jinja application backed by Supabase. This repository is configured for a
Docker deployment on Render.

## Local development

Install dependencies with [uv](https://docs.astral.sh/uv/):

```sh
uv sync --all-groups
cp .env.example .env
uv run uvicorn bits_and_bots.main:app --reload --host 127.0.0.1 --port 8000
```

For local use, configure a development Supabase project if you need database-backed
features. Public pages and the test suite can run without connecting to production.

Run checks:

```sh
uv run pytest
uv run python -m compileall -q src tests scripts
docker build -t bits-and-bots:local .
```

## Application layout

- `src/bits_and_bots/main.py` — FastAPI app, health checks and middleware.
- `src/bits_and_bots/routers/` — public, authentication and administrator routes.
- `src/bits_and_bots/security.py` — opaque revocable sessions and role dependencies.
- `src/bits_and_bots/csrf.py` — signed double-submit CSRF protection.
- `src/bits_and_bots/audit.py` — metadata-only audit events.
- `src/bits_and_bots/database.py` — lazy Supabase client.
- `supabase/migrations/` — version-controlled SQL security migration.
- `scripts/create_admin.py` — one-time initial administrator provisioning.
- `scripts/migrate_consent_files_to_storage.py` — dry-run-first legacy file migration.
- `render.yaml` — Render Blueprint configuration.

## Important data handling

Never commit `.env`, Supabase secret keys, local database files, real consent scans,
or production exports. Consent and contact records contain sensitive information,
including children's and potentially special-category health data. Restrict access,
apply the data-retention policy, and follow the incident-response process.
