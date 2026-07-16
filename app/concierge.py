"""The concierge agent — the one swappable seam behind /api/chat.

`answer()` is the only thing the web layer calls. In the skeleton this was an
echo stub; here it drives the Claude Agent SDK's `query()` loop over a target
repository with a read-only toolset. Everything the server needs to know about
"how a reply is produced" lives in this file.
"""

import logging

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    query,
)

from . import config
from .sessions import get_session_id, set_session_id
from .tools import ALLOWED_TOOL_NAMES, concierge_server

logger = logging.getLogger("concierge")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

SYSTEM_PROMPT = """You are the codebase concierge for a single repository.

Answer questions about THIS repository concisely and accurately. Ground every
answer in the actual files: read them, and cite the file paths (and line numbers
where helpful) you relied on. If the repo does not contain the answer, say so
plainly rather than guessing. Never invent files, functions, or APIs you have
not seen. Keep answers tight — a few sentences or a short list, not an essay."""

# Read-only built-ins + our custom tools. This allowlist is the entire safety
# story on a headless server: with only these tools the agent structurally
# cannot modify the filesystem, no matter what a user types into the chat box.
ALLOWED_TOOLS = ["Read", "Glob", "Grep", *ALLOWED_TOOL_NAMES]

# Defense in depth: explicitly deny every built-in that can write, execute, or
# reach the network, so an unlisted tool can never be auto-approved.
DISALLOWED_TOOLS = [
    "Bash", "Write", "Edit", "MultiEdit", "NotebookEdit",
    "WebFetch", "WebSearch", "Task", "ToolSearch",
]


def _build_options(resume: str | None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=ALLOWED_TOOLS,
        disallowed_tools=DISALLOWED_TOOLS,
        # Hermetic: do NOT inherit the operator's personal ~/.claude settings
        # (which may pre-approve Bash etc.). The allowlist above is the whole story.
        setting_sources=[],
        permission_mode="default",
        cwd=str(config.TARGET_REPO),
        max_turns=config.MAX_TURNS,
        mcp_servers={"concierge": concierge_server},
        resume=resume,
    )


async def _agent_answer(message: str, conversation_id: str) -> str:
    """Run one turn of the SDK agent loop, resuming this conversation's session."""
    resume = get_session_id(conversation_id)
    options = _build_options(resume=resume)

    reply: str | None = None
    error_text: str | None = None
    session_id: str | None = None

    try:
        async for msg in query(prompt=message, options=options):
            # The init message carries the session_id we need to resume later (Task 7).
            if isinstance(msg, SystemMessage) and msg.subtype == "init":
                session_id = msg.data.get("session_id")
            # Log each tool the agent reaches for — visible evidence of the loop,
            # including our custom tools (Task 8).
            elif isinstance(msg, AssistantMessage):
                for block in getattr(msg, "content", []):
                    name = getattr(block, "name", None)
                    if name:
                        logger.info("agent tool call: %s", name)
            # The result message is the finished answer (Task 6). It can also carry
            # an error (e.g. "Not logged in"), which we keep and surface verbatim.
            elif isinstance(msg, ResultMessage):
                if getattr(msg, "is_error", False):
                    error_text = msg.result
                else:
                    reply = msg.result
    except Exception:
        # The SDK may raise after emitting an error ResultMessage. If we already
        # captured something useful, prefer it over re-raising.
        if reply is None and error_text is None:
            raise

    if reply is not None:
        # Only remember the session for a successful turn, so follow-ups resume
        # a real conversation rather than a failed one.
        if session_id:
            set_session_id(conversation_id, session_id)
        return reply

    if error_text:
        return f"The agent couldn't complete that request: {error_text}"

    return "I couldn't produce an answer for that one."


async def answer(message: str, conversation_id: str) -> str:
    """Produce a chat reply for `message` within `conversation_id`.

    This is the seam the rest of the app depends on. Any failure is turned into a
    polite reply here so /api/chat never returns a 500 to the browser.
    """
    if config.MODE == "echo":
        return f"echo: {message}"

    try:
        return await _agent_answer(message, conversation_id)
    except Exception as exc:  # noqa: BLE001 - surface anything as a friendly reply
        return (
            "Sorry — I ran into a problem answering that "
            f"({type(exc).__name__}). Please try again."
        )
