# Implementation roadmap

## Available now

- Environment-backed service URL and application configuration in backend/config/settings.py.
- SQLAlchemy models for users, Gmail connections, email summaries, and sync runs; SQLite is the local default and PostgreSQL URLs are supported.
- User repository and demo/Google OpenID sign-in routes with signed session cookies.
- Mock-backed email list/detail, sync, draft, and explicitly confirmed simulated-send routes.
- Responsive React dashboard with category navigation, search, pagination, conversation details, and demo sign-in.

## Next phases

1. Add authenticated-user dependencies to every mailbox endpoint and scope all database reads/writes to the session user.
2. Add Alembic migrations and repositories for summary upserts, preserving user-selected categories.
3. Implement Gmail consent and encrypted refresh-token storage before enabling mailbox access.
4. Implement complete Gmail thread retrieval, MIME normalization, Gmail drafts, and incremental history sync.
5. Add Gemini structured classification with Pydantic validation, retry, and LangGraph orchestration.
6. Make sync a deduplicated background job with durable status and failure handling.
7. Complete frontend filters, manual category updates, full thread rendering, draft ownership, and send approval.
8. Add integration tests using mock providers before enabling live external credentials.

Mock mode uses a local demo identity and fake data. Real OpenID mode only signs in a user; Gmail scopes and Gmail API calls are intentionally not enabled yet.
