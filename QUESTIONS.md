# Session 11 — Reflection Questions

## ❓ Q1 — Why a permission system, and why plan mode from an empty directory?

An agent that runs shell commands **acts**, and many actions are irreversible — so a permission gate keeps a human approving the risky ones. From an empty directory there's no git history or tests to catch a mistake, so plan mode (read-only until you approve) lets you fix the architecture *before any code exists*, when changing course is free. I used it in Task 3 to lock in the swappable `concierge.answer()` seam before Claude Code wrote a line.

## ❓ Q2 — What belongs in `CLAUDE.md`?

Durable, high-signal facts you *can't* get by reading the code: how to run/test, the one architectural rule (agent logic stays behind `concierge.answer()`), and key conventions. Not: anything derivable from the code, prose, or stale detail — every line costs context in *every* session. It's the Session 3 context problem inverted: a small, curated block of persistent memory so future sessions start smart instead of rediscovering everything.

## ❓ Q3 — Agent SDK vs. hand-built LangGraph loops?

**Free:** a hardened agent loop with retries, production tools, permissions/hooks, auto context-compaction, session persistence, and MCP — everything I hand-assembled in Sessions 2–4, in one dependency. **Given up:** per-iteration control, custom graph topologies, and provider choice (Claude only). It trades control and flexibility for speed and robustness — a great deal when "an agent that answers about a repo" is the goal.

## ❓ Q4 — Why `query()` over a plain chat completion? New risks, and how addressed?

`query()` gives the model **agency** — it reads, greps, and globs the repo across turns to ground answers in real files (with citations), versus a single completion that only emits text. The new risk: a tool-wielding agent can take real actions or be hijacked by prompt-injection. I contained it with a **read-only allowlist** (`Read`/`Glob`/`Grep` + two custom tools), explicit denies for `Bash`/`Write`/network, hermetic settings (`setting_sources=[]`), and `max_turns=25` — so it structurally can't modify the filesystem, which I verified adversarially (asking it to write a file and run `whoami` both failed).
