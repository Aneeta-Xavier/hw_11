# Codebase Concierge — container image for Railway (or any container host).
#
# The Claude Agent SDK shells out to a bundled `claude` runtime that ships inside
# the pip package, fetched per-platform during `uv sync`. So a Linux build here
# pulls the Linux runtime automatically — no Node or separate CLI install needed.

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# git: to clone the target repo the concierge answers about.
# ca-certificates: TLS for the clone and for the Anthropic API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching. This step also downloads
# the platform-appropriate bundled `claude` runtime used by the SDK.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Application source.
COPY app ./app
COPY static ./static

# Bake a clean, read-only copy of the PUBLIC course repo as the concierge target.
# Stripping .git keeps the image smaller; the agent only reads files.
RUN git clone --depth 1 \
      https://github.com/AI-Maker-Space/The-AI-Engineering-Certification-v1.0.git \
      /srv/target-repo \
    && rm -rf /srv/target-repo/.git

ENV CONCIERGE_TARGET_REPO=/srv/target-repo \
    CONCIERGE_MODE=agent \
    CONCIERGE_MAX_TURNS=25 \
    PYTHONUNBUFFERED=1

# ANTHROPIC_API_KEY is injected at runtime as a Railway variable — never baked
# into the image.

EXPOSE 8000

# Railway provides $PORT at runtime; fall back to 8000 for local `docker run`.
CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
