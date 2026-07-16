# Session 11 — Reflection Questions

## ❓ Q1 — Why a permission system, and why plan mode from an empty directory?

An agent that runs shell commands **acts**, and many actions are irreversible — so a permission gate keeps a human approving the risky ones. From an empty directory there's no git history or tests to catch a mistake, so plan mode (read-only until you approve) lets you fix the architecture *before any code exists*, when changing course is free. I used it in Task 3 to lock in the swappable `concierge.answer()` seam before Claude Code wrote a line.

## ❓ Q2 — What belongs in `CLAUDE.md`?

Durable, high-signal facts you *can't* get by reading the code: how to run/test, the one architectural rule (agent logic stays behind `concierge.answer()`), and key conventions. Not: anything derivable from the code, prose, or stale detail — every line costs context in *every* session. It's the Session 3 context problem inverted: a small, curated block of persistent memory so future sessions start smart instead of rediscovering everything.

## ❓ Q3 — Agent SDK vs. hand-built LangGraph loops?

**Free:** a hardened agent loop with retries, production tools, permissions/hooks, auto context-compaction, session persistence, and MCP — everything I hand-assembled in Sessions 2–4, in one dependency. **Given up:** per-iteration control, custom graph topologies, and provider choice (Claude only). It trades control and flexibility for speed and robustness — a great deal when "an agent that answers about a repo" is the goal.

## ❓ Q4 — Why `query()` over a plain chat completion? New risks, and how addressed?

`query()` gives the model **agency** — it reads, greps, and globs the repo across turns to ground answers in real files (with citations), versus a single completion that only emits text. The new risk: a tool-wielding agent can take real actions or be hijacked by prompt-injection. I contained it with a **read-only allowlist** (`Read`/`Glob`/`Grep` + two custom tools), explicit denies for `Bash`/`Write`/network, hermetic settings (`setting_sources=[]`), and `max_turns=25` — so it structurally can't modify the filesystem, which I verified adversarially (asking it to write a file and run `whoami` both failed).

---

# Activity #1 — Level-Up: Live Progress Streaming

**What I built:** the browser now streams the agent's tool activity in real time — you see "🔧 Reading `main.py`…", "Searching…" as the agent works, then the final answer replaces it. (I also have a second custom tool, `largest_files`, which independently satisfies option 3.)

**Design decision (one paragraph):** The base app showed a static "thinking…" spinner while the agent did multi-step work — glob the tree, grep for entry points, read files — which can take 10–15 seconds and feels broken. I chose **live progress streaming** because it turns that opaque wait into a narrative that both reassures the user and *shows the agent grounding its answer in the actual code*. The technical decision was to use **Server-Sent Events over a POST via `fetch` + a `ReadableStream` reader**, rather than the browser's native `EventSource` — `EventSource` can only do GET and can't send a request body, which my `{message, conversation_id}` payload needs. On the server I refactored the agent seam into an async generator (`answer_stream`) that yields typed events (`tool`, `done`) as it consumes the SDK's message stream, and the endpoint serializes those as SSE frames; the frontend parses frames incrementally and updates the pending chat bubble. Crucially this reuses the *same* message stream the SDK already produces — I simply surface the `AssistantMessage` tool-use blocks as friendly status lines instead of discarding them — and I kept the original non-streaming `/api/chat` endpoint for simple clients and curl.
