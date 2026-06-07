FROM debian:bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        zstd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock .python-version ./
RUN uv python install && uv sync --frozen --no-dev

COPY buoy/ ./buoy/
COPY forwarders/ ./forwarders/
COPY main.py ./

RUN mkdir /data
ENV HONEYPOT_LOG=/data/honeypot.log

CMD [".venv/bin/python", "main.py"]
