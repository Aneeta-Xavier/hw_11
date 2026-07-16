# Codebase Concierge — working notes for Claude

A FastAPI chat app that serves the Claude Agent SDK behind a web UI: users ask
questions about a target repository and a read-only agent answers.

## Run & verify

```bash
uv sync
# real agent (needs ANTHROPIC_API_KEY):
CONCIERGE_TARGET_REPO=/path/to/repo uv run uvicorn app.main:app --reload
# plumbing only, no API key:
CONCIERGE_MODE=echo uv run uvicorn app.main:app --reload
```

Smoke-test the endpoint:

```bash
curl -s localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"hi","conversation_id":"demo"}'
```

Always verify a change by actually running the server and hitting `/api/chat` —
don't stop at "it imports".

## The one architectural rule

`app/concierge.py::answer(message, conversation_id)` is the **only** seam between
the web layer and the agent. `app/main.py` must never import the SDK directly —
it calls `answer()` and nothing else. Keep all agent/SDK logic inside
`concierge.py` (and its helpers `tools.py`, `sessions.py`, `config.py`).

## Conventions

- Frontend is plain HTML/CSS/JS in `static/` — no framework, no build step.
- The agent's `allowed_tools` are **read-only** on purpose; that allowlist is the
  server's safety story. Do not add write/exec tools without a deliberate reason.
- Config comes from env vars via `app/config.py` — don't hard-code paths.
- `answer()` must never raise to the caller: turn failures into a polite reply so
  `/api/chat` never 500s.
