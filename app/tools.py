"""Custom in-process tools for the concierge (Task 8).

The SDK models custom tools as an in-process MCP server — the Session 8 concept
with zero networking. Each tool is a normal async Python function; the agent can
call it exactly like a built-in. Tools are allowlisted by the name
`mcp__<server-key>__<tool-name>` (see ALLOWED_TOOL_NAMES below).

Both tools resolve paths against config.TARGET_REPO and refuse to escape it, so a
chat user cannot use them to read arbitrary files on the server.
"""

from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server, tool

from . import config

# Directories that are never interesting to scan and can be huge.
_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
              ".pytest_cache", ".ruff_cache", "dist", "build", ".next"}


def _safe_resolve(rel_path: str) -> Path:
    """Resolve `rel_path` under TARGET_REPO, raising if it escapes the repo."""
    target = (config.TARGET_REPO / rel_path).resolve()
    if config.TARGET_REPO not in target.parents and target != config.TARGET_REPO:
        raise ValueError(f"path {rel_path!r} is outside the target repository")
    return target


def _text(msg: str) -> dict:
    """Wrap a plain string in the MCP tool-result envelope."""
    return {"content": [{"type": "text", "text": msg}]}


@tool(
    "count_lines",
    "Count the number of lines in a single file. file_path is relative to the repo root.",
    {"file_path": str},
)
async def count_lines(args):
    try:
        path = _safe_resolve(args["file_path"])
        n = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
    except (OSError, ValueError) as exc:
        return _text(f"Could not count lines: {exc}")
    return _text(f"{args['file_path']}: {n} lines")


@tool(
    "largest_files",
    "List the largest source files in the repo by line count. "
    "Optional 'limit' (default 10) and 'subdir' (relative path to restrict the scan).",
    {"limit": int, "subdir": str},
)
async def largest_files(args):
    limit = args.get("limit") or 10
    subdir = args.get("subdir") or "."
    try:
        root = _safe_resolve(subdir)
    except ValueError as exc:
        return _text(str(exc))

    results: list[tuple[int, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(config.TARGET_REPO).parts):
            continue
        try:
            n = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
        except OSError:
            continue
        results.append((n, str(path.relative_to(config.TARGET_REPO))))

    results.sort(reverse=True)
    top = results[:limit]
    if not top:
        return _text(f"No readable files found under {subdir!r}.")
    listing = "\n".join(f"{n:>7} lines  {rel}" for n, rel in top)
    return _text(f"Largest files under {subdir!r}:\n{listing}")


# The in-process MCP server the agent talks to.
concierge_server = create_sdk_mcp_server(
    name="concierge",
    version="1.0.0",
    tools=[count_lines, largest_files],
)

# Fully-qualified names to add to the agent's allowed_tools.
ALLOWED_TOOL_NAMES = [
    "mcp__concierge__count_lines",
    "mcp__concierge__largest_files",
]
