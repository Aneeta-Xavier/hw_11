"""Conversation memory (Task 7).

Each browser conversation has a stable `conversation_id`. The Agent SDK tracks
history under its own `session_id`. This module maps one to the other so that
follow-up messages resume the right SDK session and carry context.

An in-memory dict is fine for the course; swap for Redis/DB to survive restarts
or scale beyond one process.
"""

_STORE: dict[str, str] = {}


def get_session_id(conversation_id: str) -> str | None:
    """Return the SDK session_id for this conversation, or None if it's new."""
    return _STORE.get(conversation_id)


def set_session_id(conversation_id: str, session_id: str) -> None:
    """Remember the SDK session_id so the next message can resume it."""
    _STORE[conversation_id] = session_id
