# Codebase Concierge

A chat web app powered by the **Claude Agent SDK**. Point it at any repository on
disk and ask questions about it in the browser — the answers come from a
read-only agent that reads, greps, and globs the code, plus a couple of custom
tools. Built for Session 11 of the AI Engineering Certification.

```
browser chat UI  ──POST /api/chat──▶  FastAPI  ──▶  concierge.answer()  ──▶  Claude Agent SDK
   (static/)                          (app/main.py)   (the swappable seam)      query() loop
```

## Requirements

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- An `ANTHROPIC_API_KEY` (only for the real agent; not needed for `echo` mode)

## Setup

```bash
uv sync                      # install dependencies
cp .env.example .env         # then edit .env
```

Set at least `CONCIERGE_TARGET_REPO` to the absolute path of the repo you want to
ask about, and `ANTHROPIC_API_KEY` for the real agent.

## Run

```bash
# Real agent (needs ANTHROPIC_API_KEY + CONCIERGE_TARGET_REPO):
CONCIERGE_TARGET_REPO=/path/to/repo uv run uvicorn app.main:app --reload

# Or verify the web plumbing with no API key — replies just echo your message:
CONCIERGE_MODE=echo uv run uvicorn app.main:app --reload
```

Then open <http://localhost:8000>.

## Test the endpoint directly

```bash
curl -s localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "what does this repo do?", "conversation_id": "demo"}'
# -> {"reply": "...", "conversation_id": "demo"}
```

Health check: `curl -s localhost:8000/api/health`

## Try the SDK primitive on its own

```bash
uv run scratch_query.py /path/to/any/repo
```

## How it's put together

| File | Role |
| ---- | ---- |
| `app/main.py` | FastAPI routes: serves the UI, exposes `POST /api/chat`. |
| `app/concierge.py` | **The seam.** `answer(message, conversation_id)` runs the SDK agent loop. |
| `app/tools.py` | Custom in-process tools (`count_lines`, `largest_files`). |
| `app/sessions.py` | Maps each browser `conversation_id` to an SDK `session_id` for follow-ups. |
| `app/config.py` | Env-driven config (target repo, max turns, mode). |
| `static/` | Plain HTML/CSS/JS chat UI — no frontend framework. |

### Safety model

The agent runs headless, so there's no human to approve tool calls. The guard
rails are structural: the allowlist is **read-only** (`Read`, `Glob`, `Grep`, and
two custom read-only tools), and `max_turns` caps every request. With this
allowlist the agent cannot modify the filesystem no matter what a user types.

## Configuration

| Env var | Default | Meaning |
| ------- | ------- | ------- |
| `CONCIERGE_TARGET_REPO` | cwd | Absolute path of the repo to answer about. |
| `CONCIERGE_MAX_TURNS` | `25` | Hard cap on agent-loop turns per request. |
| `CONCIERGE_MODE` | `agent` | `agent` = real SDK loop; `echo` = echo stub. |
| `CONCIERGE_PASSWORD` | — | If set, visitors must enter this shared password to chat. |
| `ANTHROPIC_API_KEY` | — | Required in `agent` mode. |

## Deploying

A `Dockerfile` and `railway.json` are included. The image installs the app,
clones the public course repo as the concierge's target, and runs uvicorn on
`$PORT`. Set `ANTHROPIC_API_KEY` (and optionally `CONCIERGE_PASSWORD`) as
service variables on your host — never bake secrets into the image.
