# Scanova MCP server (production image; see .github/workflows/deploy.yml).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first (cached across source changes); no dev tools in production.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src

# The release this image was built from (deploy.yml passes the release tag).
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION \
    PATH="/app/.venv/bin:$PATH"

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 scanova && chown -R scanova:scanova /app
USER scanova

EXPOSE 8000

# Fails (exit 1) unless /health answers 200.
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=5).status == 200 else 1)"

CMD ["python", "src/cloud_server.py"]
