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


def _env(name: str, default: str) -> str:
    """Read an env var, treating unset OR blank as "use the default".

    Hosting dashboards often create a variable with an empty value; without this
    a blank `CONCIERGE_MAX_TURNS` would crash `int()`, and a blank target repo
    would point the agent at the wrong place. Blank == unset here.
    """
    value = os.environ.get(name, "")
    return value.strip() if value and value.strip() else default


# Which repository the concierge answers questions about. In the container the
# image bakes a snapshot at /srv/target-repo; fall back to it when present so a
# blank env var can't misdirect the agent. Locally, defaults to the cwd.
_default_target = "/srv/target-repo" if Path("/srv/target-repo").is_dir() else str(Path.cwd())
TARGET_REPO: Path = Path(_env("CONCIERGE_TARGET_REPO", _default_target)).resolve()

# Hard cap on agent-loop iterations per request, so no single question can
# loop forever on a headless server. Falls back to 25 if blank/invalid.
try:
    MAX_TURNS: int = int(_env("CONCIERGE_MAX_TURNS", "25"))
except ValueError:
    MAX_TURNS = 25

# "agent" (default) runs the real Claude Agent SDK loop.
# "echo" replaces it with a trivial echo — lets you verify the web plumbing
# end-to-end without an API key. This is the "swappable stub" seam.
MODE: str = _env("CONCIERGE_MODE", "agent").lower()

# Optional shared password. When set, /api/chat requires it (so a public URL
# can't spend your API credits). Blank = open, no gate.
PASSWORD: str = _env("CONCIERGE_PASSWORD", "")
