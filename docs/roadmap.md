# Implementation roadmap

## Available now

- Environment-backed backend and mock service URL configuration in `backend/config/settings.py`.
- FastAPI email list/detail, sync status, draft, and explicitly confirmed simulated-send routes.
- Mock conversations and fake draft IDs. The adapter rejects live mode until a real provider is implemented.
- Responsive React dashboard with category navigation, search, pagination, detail panel, and a mock draft/send flow.

## Next phases

1. Persist users, Gmail connections, email summaries, and sync state in PostgreSQL with Alembic migrations.
2. Add Google OAuth session handling, encrypted refresh tokens, CSRF/state validation, and per-user authorization.
3. Implement the Gmail adapter for full threads, MIME normalization, history-based incremental sync, and Gmail draft creation.
4. Add Gemini structured classification with Pydantic validation, retry, and LangGraph orchestration.
5. Make sync a background job with deduplication and durable progress.
6. Add database-backed filtering, stable sorting, category overrides, and multi-user isolation.
7. Add frontend authentication, live thread detail retrieval, editable category and reply controls, and production send approvals.
8. Add integration tests using mock providers before enabling live external credentials.

Live Gmail access and delivery are intentionally not enabled in mock mode. Configure real credentials only after implementing and reviewing the production provider and authentication boundaries.
