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

The allowlisted tool registry is in backend/agents/tool_registry.py. Inspect tool names, descriptions, input schemas, and side-effect classes at GET /api/agent/tools after sign-in.

| Tool | Side effect |
| --- | --- |
| list_gmail_threads | Read mailbox thread metadata |
| get_gmail_thread | Read one conversation |
| get_gmail_profile | Read mock mailbox profile |
| create_important_reply_draft_tool | Create a draft only |

The LangGraph workflow fetches threads, normalizes messages, classifies in batches with bounded concurrency, validates the results, and saves per-user summaries. It then creates a draft only when the saved conversation category is Important and the reply decision is reply. The mail service checks ownership and both conditions again. Email text is untrusted input; the classifier never sends mail. Sending remains a user-confirmed UI action, and mock mode simulates it without contacting Gmail.

The mailbox can stay on fake data with MOCK_INTEGRATIONS=true while Gemini handles classification through LangChain. Set GEMINI_API_KEY and MOCK_AI=false; GEMINI_MODEL defaults to gemini-2.5-flash. Set MOCK_AI=true to force deterministic fixture analysis. Without a Gemini key, local development falls back to fixture analysis. The call is implemented in backend/agents/llm.py and used by backend/agents/nodes.py. The live Gmail adapter is not implemented yet.

## Configuration

Environment settings live in backend/config/settings.py. SQLite is the default for local development. Set DATABASE_URL to a PostgreSQL URL for a hosted database; the PostgreSQL driver is included. Set MOCK_INTEGRATIONS=false and provide Google OAuth credentials to use Google OpenID sign-in. That flow requests identity scopes only; it does not connect a Gmail mailbox.

Do not commit .env or real credentials. Use HTTPS and set COOKIE_SECURE=true when hosting the application.

## Remaining work

Encrypted Gmail refresh-token storage, live Gmail thread/draft adapters, a persistent external worker, and end-to-end verification are still required before using a real mailbox. The initial Alembic migration and FastAPI background sync are now in place.
