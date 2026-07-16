"""FastAPI entrypoint: serves the chat UI and the /api/chat endpoint."""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .concierge import answer, answer_stream

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Codebase Concierge")


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    # `gated` tells the frontend whether to show the password screen. The
    # password itself is never exposed.
    return {
        "status": "ok",
        "mode": config.MODE,
        "gated": bool(config.PASSWORD),
        "target_repo": str(config.TARGET_REPO),
    }


def _check_password(supplied: str | None) -> None:
    """Enforce the shared-password gate. Case-insensitive and trimmed so phone
    keyboards (auto-capitalization, stray spaces) don't lock people out."""
    if config.PASSWORD:
        if (supplied or "").strip().lower() != config.PASSWORD.strip().lower():
            raise HTTPException(status_code=401, detail="Invalid or missing password.")


@app.post("/api/chat/stream")
async def chat_stream(
    req: ChatRequest,
    x_concierge_password: str | None = Header(default=None),
) -> StreamingResponse:
    """Server-Sent Events version of /api/chat (Activity #1: live streaming).

    Streams the agent's tool activity to the browser as it works, then a final
    `done` event with the reply. Same password gate as /api/chat.
    """
    _check_password(x_concierge_password)
    conversation_id = req.conversation_id or str(uuid.uuid4())

    async def event_source():
        async for event_type, payload in answer_stream(req.message, conversation_id):
            yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    x_concierge_password: str | None = Header(default=None),
) -> ChatResponse:
    # Non-streaming endpoint (kept for simple clients / curl). The browser UI
    # uses /api/chat/stream instead.
    _check_password(x_concierge_password)

    # A new browser conversation arrives without an id; mint one and echo it
    # back so the client can send it on every follow-up (Task 7).
    conversation_id = req.conversation_id or str(uuid.uuid4())
    reply = await answer(req.message, conversation_id)
    return ChatResponse(reply=reply, conversation_id=conversation_id)


# Static assets (CSS/JS) live under /static; index.html is served at / above.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
