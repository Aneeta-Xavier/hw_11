"""Task 5: feel the SDK primitive in isolation.

Run it to watch the agent loop's anatomy scroll by, then read the final result:

    uv run scratch_query.py [/path/to/any/repo]

Requires ANTHROPIC_API_KEY in the environment (or another configured Claude auth).
"""

import asyncio
import sys
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

REPO = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())


async def main() -> None:
    async for message in query(
        prompt="What does this project do? Answer in two sentences.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            cwd=REPO,
        ),
    ):
        print(type(message).__name__)  # watch the loop's anatomy
        if hasattr(message, "result"):
            print("\n" + message.result)


if __name__ == "__main__":
    asyncio.run(main())
