FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/gerardnico/transcribe" \
      org.opencontainers.image.url="https://github.com/gerardnico/transcribe" \
      org.opencontainers.image.title="transcribe" \
      org.opencontainers.image.description="Get transcripts from file and social media"

# Install uv from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    TRANSCRIBE_HOME=/home/app/.transcribe

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy metadata first to improve dependency-layer caching.
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Install production dependencies only (no dev, no optional whisper extra).
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p "${TRANSCRIBE_HOME}" \
    && chown -R app:app /app /home/app

ENV PATH="/app/.venv/bin:${PATH}"

USER app

EXPOSE 8000

CMD ["transcribe", "mcp", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
