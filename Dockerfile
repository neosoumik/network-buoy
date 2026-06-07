FROM debian:bookworm-slim

WORKDIR /app

# --- System deps ---
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        zstd \
    && rm -rf /var/lib/apt/lists/*

# --- uv (installs itself + manages Python) ---
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# --- Ollama ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# --- Python deps (uv pulls Python 3.14t from .python-version) ---
COPY pyproject.toml uv.lock .python-version ./
RUN uv python install && uv sync --frozen --no-dev

# --- App source ---
COPY buoy/ ./buoy/
COPY main.py ./

# --- Entrypoint ---
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Logs volume
RUN mkdir /data
ENV HONEYPOT_LOG=/data/honeypot.log \
    OLLAMA_URL=http://localhost:11434 \
    OLLAMA_MODEL=gemma3:1b

ENTRYPOINT ["/entrypoint.sh"]
