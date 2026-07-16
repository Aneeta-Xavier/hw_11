"""FastAPI entrypoint: serves the chat UI and the /api/chat endpoint."""

import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config
from .concierge import answer

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


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    x_concierge_password: str | None = Header(default=None),
) -> ChatResponse:
    # Shared-password gate: if a password is configured, every chat request must
    # present it. Matched case-insensitively and trimmed, so phone keyboards
    # (auto-capitalization, stray spaces) don't lock people out. Returns 401 so
    # the frontend can prompt for it.
    if config.PASSWORD:
        supplied = (x_concierge_password or "").strip().lower()
        if supplied != config.PASSWORD.strip().lower():
            raise HTTPException(status_code=401, detail="Invalid or missing password.")

    # A new browser conversation arrives without an id; mint one and echo it
    # back so the client can send it on every follow-up (Task 7).
    conversation_id = req.conversation_id or str(uuid.uuid4())
    reply = await answer(req.message, conversation_id)
    return ChatResponse(reply=reply, conversation_id=conversation_id)


# Static assets (CSS/JS) live under /static; index.html is served at / above.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
