"""Central configuration, read once from the environment.

Kept in its own module so both the agent and the custom tools can share it
without importing each other (avoids a circular import).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load a local .env (gitignored) so ANTHROPIC_API_KEY and the settings below are
# available however the app is launched.
load_dotenv()

# Which repository the concierge answers questions about. Point this at any
# checkout on disk; defaults to the current working directory.
TARGET_REPO: Path = Path(os.environ.get("CONCIERGE_TARGET_REPO", Path.cwd())).resolve()

# Hard cap on agent-loop iterations per request, so no single question can
# loop forever on a headless server.
MAX_TURNS: int = int(os.environ.get("CONCIERGE_MAX_TURNS", "25"))

# "agent" (default) runs the real Claude Agent SDK loop.
# "echo" replaces it with a trivial echo — lets you verify the web plumbing
# end-to-end without an API key. This is the "swappable stub" seam.
MODE: str = os.environ.get("CONCIERGE_MODE", "agent").lower()

# Optional shared password. When set, /api/chat requires it (so a public URL
# can't spend your API credits). Empty string = open, no gate.
PASSWORD: str = os.environ.get("CONCIERGE_PASSWORD", "").strip()
