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

Open http://localhost:5173. In default mock mode, **Continue with Google** creates a local demo user, stores that user in the configured database, and redirects back to the dashboard. The fake Gmail provider returns sample conversations and creates demo draft IDs. Simulated send requests never contact Gmail.

## Configuration

Environment settings live in backend/config/settings.py. SQLite is the default for local development. Set DATABASE_URL to a PostgreSQL URL for a hosted database; the PostgreSQL driver is included. Set MOCK_INTEGRATIONS=false and provide Google OAuth credentials to use the OpenID profile sign-in flow. That flow requests identity scopes only; it does not connect a Gmail mailbox.

Do not commit .env or real credentials. Use HTTPS and set COOKIE_SECURE=true when hosting the application.

## Current scope

Implemented: settings, SQLAlchemy schema and user repository, demo/Google OpenID sign-in, email list/detail mock API, sync/draft/simulated-send routes, and the dashboard.

Still needed before real mailbox use: protect email APIs with authenticated-user scoping, store encrypted Google refresh tokens after Gmail consent, add Gmail thread/draft adapters, persist summaries and sync jobs through repositories, add Alembic migrations, and implement Gemini/LangGraph analysis.
