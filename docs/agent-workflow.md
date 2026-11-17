# Agent tools and analysis workflow

## Tools

The analysis agent receives tools through `backend/agents/tool_registry.py`. The registry is an explicit allowlist. Each entry exposes a name, Pydantic input schema, description, and side-effect classification at `GET /api/agent/tools` for signed-in users.

The current agent allowlist contains only:

- `list_gmail_threads`: bounded read of matching conversations.
- `get_gmail_thread`: read of one full conversation with ordered messages.

Both tools are implemented under `backend/tools/gmail_tools.py` and call the integration service. Tool descriptions identify email content as untrusted input. Draft creation remains an API service action. Sending is absent from the tool registry.

## Graph

```text
START
  -> fetch_threads (allowlisted read tools)
  -> normalize_threads
  -> classify_threads (batches of 5, bounded concurrency)
  -> validate_analyses (thread ID, enums, summary and reply rules)
  -> persist_analyses (user-scoped idempotent upsert)
  -> END
```

The graph uses a typed shared state and fixed transitions. In mock mode it returns deterministic sample analysis. With mock mode disabled, the classifier uses Gemini structured output from `GEMINI_API_KEY` and `GEMINI_MODEL`. Invalid batch members receive one individual repair attempt; unresolved items are stored as `review` with no suggested reply. A failed item does not prevent valid items from being saved.

The workflow never receives a send tool. The API still requires a persisted draft, ownership check, and explicit confirmation for its simulated-send route. The live Gmail provider is not implemented, so mock mode is the supported mode today.
