# Gmail AI Mail Manager

A modular FastAPI + React starter for an AI-assisted Gmail dashboard. External service URLs and credentials are environment-configurable; mock mode works without external accounts and never sends real email.

## Run the API

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    Copy-Item .env.example .env
    uvicorn backend.main:app --reload

API docs: http://localhost:8000/docs

## Run the dashboard

    cd frontend
    npm install
    Copy-Item .env.example .env
    npm run dev

Open http://localhost:5173. In default mock mode, **Continue with Google** creates a local demo user, stores that user in the configured database, and redirects back to the dashboard. Use **Sync Gmail** to persist sample conversations. Category edits persist and are retained across subsequent mock syncs. Draft and send actions use local demo IDs; simulated sends never contact Gmail.

## Configuration

Environment settings live in backend/config/settings.py. SQLite is the default for local development. Set DATABASE_URL to a PostgreSQL URL for a hosted database; the PostgreSQL driver is included. Set MOCK_INTEGRATIONS=false and provide Google OAuth credentials to use the Google OpenID profile sign-in flow. That flow requests identity scopes only; it does not connect a Gmail mailbox.

Do not commit .env or real credentials. Use HTTPS and set COOKIE_SECURE=true when hosting the application.

## Current scope

Implemented: settings, SQLAlchemy models and user/email repositories, demo/Google OpenID sign-in, signed sessions, authenticated and user-scoped email APIs, database pagination/search/filtering, manual category overrides, sync status persistence, mock draft ownership checks, and the dashboard.

Still needed before real mailbox use: Alembic migrations, encrypted Google refresh-token storage and Gmail consent, Gmail thread/draft adapters, actual background sync and incremental history processing, Gemini/LangGraph analysis, and end-to-end verification.
