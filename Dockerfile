# Codebase Concierge — container image for Railway (or any container host).
#
# The Claude Agent SDK shells out to a bundled `claude` runtime that ships inside
# the pip package, fetched per-platform during `uv sync`. So a Linux build here
# pulls the Linux runtime automatically — no Node or separate CLI install needed.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# ca-certificates: TLS for the Anthropic API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching. This step also downloads
# the platform-appropriate bundled `claude` runtime used by the SDK.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Application source (for running the server).
COPY app ./app
COPY static ./static

# The concierge answers questions about a target repo. We point it at this app's
# OWN source — a clean, self-contained snapshot copied from the build context
# (no .git, no .venv, no .env thanks to .dockerignore). No network needed at
# build time, so nothing can block the deploy.
COPY . /srv/target-repo

ENV CONCIERGE_TARGET_REPO=/srv/target-repo \
    CONCIERGE_MODE=agent \
    CONCIERGE_MAX_TURNS=25 \
    PYTHONUNBUFFERED=1

# ANTHROPIC_API_KEY is injected at runtime as a Railway variable — never baked
# into the image.

EXPOSE 8000

# Railway provides $PORT at runtime; fall back to 8000 for local `docker run`.
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
