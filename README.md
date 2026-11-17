# Gmail AI Mail Manager

A modular FastAPI starter for an AI-assisted Gmail dashboard. External services are configured through environment URLs and default to local mock endpoints, so development does not require Gmail credentials or send real mail.

## Run

Requires Python 3.11+.

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    Copy-Item .env.example .env
    uvicorn backend.main:app --reload

API docs: http://localhost:8000/docs

Set MOCK_INTEGRATIONS=true to use the built-in fake Gmail and AI service. The fake provider returns sample conversations, creates local draft IDs, and never sends email. To connect real Google/Gemini APIs later, set MOCK_INTEGRATIONS=false and configure the corresponding credentials and base URLs.

## Configuration

See .env.example. API URLs are centralized in backend/config/settings.py. Do not commit .env or real credentials.

## Current scope

This first commit establishes configuration, a working API foundation, mock integration adapters, and typed email/sync schemas. PostgreSQL persistence, OAuth, LangGraph classification, and the React dashboard are subsequent implementation phases; mock endpoints make the initial API usable without external accounts.
