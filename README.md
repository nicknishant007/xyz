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

The allowlisted tool registry is in backend/agents/tool_registry.py. Inspect tool names, descriptions, input schemas, and side-effect classes at GET /api/agent/tools after sign-in. Send natural-language requests to POST /api/agent/chat with a JSON message and the signed-in session's CSRF token.

| Tool | Side effect |
| --- | --- |
| list_gmail_threads | Read mailbox thread metadata |
| get_gmail_thread | Read one conversation |
| get_email_analysis_tool | Read the signed-in user's saved category and reply decision |
| get_gmail_profile | Read mock mailbox profile |
| create_important_reply_draft_tool | Create a draft only |

There are two LangGraph flows. The mailbox sync graph fetches threads, normalizes messages, classifies in batches, validates results, persists per-user summaries, then drafts only eligible Important replies. The conversational graph binds Gemini to the allowlisted tools, routes model tool calls to an executor, and loops back to Gemini for a final answer. It exits immediately when Gemini returns a normal answer, and stops safely on its request limits. Each request allows at most 4 Gemini turns, 6 tool calls, and one retry per Gemini or tool call. Tool output is capped at 12000 characters; list requests are capped at 25 rows. The executor injects the authenticated user ID, and the mail service checks ownership, category, and reply decision again. Email text is untrusted input. There is no send tool; sending remains a user-confirmed UI action and mock mode simulates it without contacting Gmail.

The mailbox can stay on fake data with MOCK_INTEGRATIONS=true while Gemini handles classification through LangChain. Set GEMINI_API_KEY and MOCK_AI=false; GEMINI_MODEL defaults to gemini-2.5-flash. Set MOCK_AI=true to force deterministic fixture analysis. Without a Gemini key, local development falls back to fixture analysis. The call is implemented in backend/agents/llm.py and used by backend/agents/nodes.py. The live Gmail adapter is not implemented yet.

## Configuration

Environment settings live in backend/config/settings.py. SQLite is the default for local development. Set DATABASE_URL to a PostgreSQL URL for a hosted database; the PostgreSQL driver is included. Set MOCK_INTEGRATIONS=false and provide Google OAuth credentials to use Google OpenID sign-in. That flow requests identity scopes only; it does not connect a Gmail mailbox.

Do not commit .env or real credentials. Use HTTPS and set COOKIE_SECURE=true when hosting the application.

## Remaining work

Encrypted Gmail refresh-token storage, live Gmail thread/draft adapters, a persistent external worker, and end-to-end verification are still required before using a real mailbox. The initial Alembic migration and FastAPI background sync are now in place.
