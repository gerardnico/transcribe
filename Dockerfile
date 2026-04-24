FROM python:3.11-slim-bookworm


# Install uv from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    TRANSCRIBE_HOME=/home/app/.transcribe \
    DENO_INSTALL=/opt/deno \
    DENO_VERSION=2.3.5

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl unzip \
    && curl -fsSL https://deno.land/install.sh | sh -s v${DENO_VERSION} \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install production dependencies only (no dev, no optional whisper extra).
# Copy metadata first to improve dependency-layer caching.
# The README is reference in the pyproject.toml and is therefore needed
# but has we don't want to resync when this file change, we don't copy it
RUN echo "# Transcribe" > README.md
COPY pyproject.toml uv.lock ./
# This layer is cached as long as pyproject.toml and uv.lock don't change
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p "${TRANSCRIBE_HOME}" \
    && chown -R app:app /app /home/app

ENV PATH="/app/.venv/bin:${DENO_INSTALL}/bin:${PATH}"

USER app

EXPOSE 8206

# The thing that may changes
LABEL org.opencontainers.image.source="https://github.com/gerardnico/transcribe" \
      org.opencontainers.image.url="https://github.com/gerardnico/transcribe" \
      org.opencontainers.image.title="transcribe" \
      org.opencontainers.image.description="Get transcripts from file and social media"

ENTRYPOINT ["transcribe"]

COPY src ./src
RUN uv sync --frozen --no-dev  # installs your package, fast (deps already cached)