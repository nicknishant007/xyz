# Gmail AI Mail Manager

A modular FastAPI + React starter for an AI-assisted Gmail dashboard. External service URLs and credentials are environment-configurable; mock mode works without external accounts and never sends real email.

## Run the API

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    Copy-Item .env.example .env
    alembic upgrade head
    uvicorn backend.main:app --reload

API docs: http://localhost:8000/docs

## Run the dashboard

    cd frontend
    npm install
    Copy-Item .env.example .env
    npm run dev

Open http://localhost:5173. In default mock mode, **Continue with Google** creates a local demo user, stores that user in the configured database, and redirects back to the dashboard. Use **Sync Gmail** to run the controlled LangGraph workflow over fake conversations. Category edits persist and are retained across subsequent mock syncs. Draft and send actions use local demo IDs; simulated sends never contact Gmail.

## Agent workflow

The read-only tool registry is in backend/agents/tool_registry.py. Inspect its names, descriptions, and Pydantic input schemas at GET /api/agent/tools after sign-in. The graph fetches threads, normalizes messages, classifies in batches with bounded concurrency, validates the results, and persists per-user summaries. Email text is treated as untrusted content. The model cannot create drafts or send mail.

Mock mode uses deterministic fixture analysis. With mock mode disabled, the classifier is configured for Gemini structured output using GEMINI_API_KEY and GEMINI_MODEL. The live Gmail adapter is not implemented yet.

## Configuration

Environment settings live in backend/config/settings.py. SQLite is the default for local development. Set DATABASE_URL to a PostgreSQL URL for a hosted database; the PostgreSQL driver is included. Set MOCK_INTEGRATIONS=false and provide Google OAuth credentials to use Google OpenID sign-in. That flow requests identity scopes only; it does not connect a Gmail mailbox.

Do not commit .env or real credentials. Use HTTPS and set COOKIE_SECURE=true when hosting the application.

## Remaining work

Encrypted Gmail refresh-token storage, live Gmail thread/draft adapters, a persistent external worker, and end-to-end verification are still required before using a real mailbox. The initial Alembic migration and FastAPI background sync are now in place.
