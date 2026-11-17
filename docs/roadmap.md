# Implementation roadmap

## Available now

- Environment-backed app and service URL settings.
- Alembic-managed schema, SQLAlchemy models, and repositories for users, Gmail connections, email summaries, and sync runs.
- Demo and Google OpenID sign-in with signed session cookies.
- Authenticated, user-scoped mailbox endpoints with database pagination and manual category overrides.
- Read-only Gmail tool functions with typed arguments and clear descriptions.
- Explicit tool registry and signed-in tool catalog endpoint.
- LangGraph fetch, normalize, batch classify, validate, and persist workflow.
- Gemini structured output path and deterministic fake analysis path.
- Per-user FastAPI background sync jobs with persisted status and duplicate-job protection.
- Mock draft creation and simulated sending, separate from agent tool capabilities.

## Next phases

1. Replace in-process background tasks with a persistent worker for restart-safe deployment.
2. Implement Gmail consent and encrypted refresh-token storage before enabling mailbox access.
3. Implement live Gmail retrieval, MIME normalization, Gmail drafts, and incremental history sync.
4. Improve partial-failure accounting and expose richer job progress to the dashboard.
5. Complete frontend priority/reply filters, full thread rendering, and production approval flow.
6. Add integration tests for tool allowlisting, untrusted email handling, validation retries, persistence, and user isolation.

Mock mode uses local demo identities and fake provider data. The agent registry does not include send or draft tools. Real OpenID mode signs in a user but does not request Gmail scopes or call Gmail APIs.
