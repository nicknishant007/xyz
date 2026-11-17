# Implementation roadmap

## Available now

- Environment-backed service URL and app configuration in backend/config/settings.py.
- SQLAlchemy tables for users, Gmail connections, email summaries, and sync runs.
- SQLite local setup plus PostgreSQL URL support.
- Demo/Google OpenID sign-in with signed session cookies.
- Mailbox endpoints that require a signed-in session and scope data by user.
- Database-backed pagination, filtering, search, category overrides, and draft ownership checks.
- Mock sync, draft, and simulated-send flows plus the React dashboard.

## Next phases

1. Add Alembic migrations for the current schema.
2. Implement Gmail consent and encrypted refresh-token storage before enabling mailbox access.
3. Add Gmail thread retrieval, MIME normalization, Gmail draft creation, and incremental history sync.
4. Add Gemini structured classification with Pydantic validation, retry, and LangGraph orchestration.
5. Run synchronization as a durable background job with duplicate-job protection and partial-failure reporting.
6. Complete frontend full-thread rendering, priority/reply filters, send approval UX, and production error states.
7. Verify multi-user isolation and complete the end-to-end scenarios from the project specification.

Mock mode uses a local demo identity and fake data. Real OpenID mode signs in a user but does not request Gmail scopes or call Gmail APIs.
