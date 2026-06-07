# network-buoy

A multi-protocol honeypot that listens on common ports, captures credentials, and streams events to a real-time dashboard.

## Repo layout

```
network-buoy/
├── buoy/                    # Python honeypot service (package root)
│   ├── buoy/                # Core Python package
│   │   ├── config.py        # PROTOCOLS list — port/name/handler triples
│   │   ├── handler.py       # handle_connection() — per-connection dispatcher
│   │   ├── listener.py      # TCP accept loop, one thread per protocol
│   │   ├── logger.py        # log_connection() / log_credential() → JSON log + hooks
│   │   ├── cache.py         # Activity cache (LLM warm-up trigger)
│   │   ├── identity.py      # Node identity (NODE_ID env var)
│   │   ├── llm.py           # Generic LLM provider (ollama / openai / anthropic / openai_compatible)
│   │   ├── prompts.py       # LLM prompt cache / pre-generation
│   │   └── protocols/       # One file per protocol handler
│   ├── forwarders/
│   │   ├── __init__.py      # load() — discovers and instantiates all forwarders
│   │   └── http.py          # Batching HTTP forwarder → dashboard /api/ingest
│   ├── main.py              # Entry point: wires hooks, starts all listener threads
│   ├── pyproject.toml       # uv project config, ruff + mypy settings
│   ├── docker-compose.yml   # buoy service + buoy-net network
│   └── test/
│       ├── conftest.py      # --host / --timeout fixtures
│       └── test_protocols.py # Full protocol test suite (requires running buoy)
├── dashboard/               # Next.js 16 + React 19 + Tailwind 4 frontend
│   ├── src/app/             # Next.js App Router pages + API routes
│   ├── src/components/      # CredentialTable, EventFeed, ProtocolChart, StatCard, StatusBar, TopAttackers
│   ├── src/hooks/           # Custom React hooks
│   ├── src/lib/             # Shared utilities
│   └── docker-compose.yml   # dashboard service
├── deploy/
│   ├── ecs/                 # AWS ECS task definition + deploy script
│   └── k8s/                 # Kubernetes manifests (namespace, deployment, service, pvc)
└── .pre-commit-config.yaml  # ruff + ruff-format + standard pre-commit hooks
```

## Architecture

### Buoy (honeypot)

- Each protocol gets a dedicated `threading.Thread` (daemon), running a `start_listener` accept loop.
- On each accepted connection: `handle_connection()` logs the connection, then calls the protocol-specific handler.
- Protocol handlers call `log_connection()` and `log_credential()` from `logger.py`. These write a JSONL entry to `honeypot.log` and fan out to all registered event hooks.
- `forwarders/http.py` registers an event hook that batches events and POSTs them to the dashboard's `/api/ingest` endpoint (configurable flush interval + batch size).
- LLM responses are optionally generated per-protocol for more realistic honeypot behaviour. Controlled entirely by env vars; zero overhead when disabled.

### Dashboard

- Next.js App Router. The `/api/ingest` route receives batched events from the buoy forwarder.
- Real-time event stream delivered via WebSocket (or SSE) to frontend components.
- Components: `EventFeed`, `CredentialTable`, `TopAttackers`, `ProtocolChart`, `StatCard`, `StatusBar`.

## Protocols

19 protocols emulated on their standard ports:

| Port  | Protocol      |
|-------|---------------|
| 21    | FTP           |
| 22    | SSH           |
| 23    | Telnet        |
| 25    | SMTP          |
| 80    | HTTP          |
| 110   | POP3          |
| 143   | IMAP          |
| 389   | LDAP          |
| 443   | HTTPS         |
| 445   | SMB           |
| 3306  | MySQL         |
| 3389  | RDP           |
| 5432  | PostgreSQL    |
| 6379  | Redis         |
| 6443  | Kubernetes    |
| 8080  | Jenkins       |
| 9090  | Prometheus    |
| 9200  | Elasticsearch |
| 27017 | MongoDB       |

## Package managers

**Python — always use `uv`. Never use `pip`, `pip install`, `python -m pip`, or `poetry`.**

**JavaScript — always use `pnpm`. Never use `npm`, `npm install`, `yarn`, or `npx` (use `pnpm dlx` instead).**

These are hard rules. The lockfiles (`uv.lock`, `pnpm-lock.yaml`) and workspace configs are built for these tools. Using anything else will corrupt the lockfile or silently install the wrong versions.

## Development setup

### Buoy (Python)

Requires Python 3.14. Managed with `uv`.

```bash
cd buoy
uv sync                    # install all deps incl. dev group
uv run python main.py      # run the honeypot locally (binds all ports — needs root or port forwarding)
```

Pre-commit hooks (ruff lint+format, trailing whitespace, YAML/TOML checks):
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

Lint and type-check manually:
```bash
uv run ruff check .
uv run ruff format .
uv run mypy buoy/
```

### Dashboard (Next.js)

Requires Node ≥ 22. Managed with `pnpm`.

```bash
cd dashboard
pnpm install
pnpm dev        # Turbopack dev server
pnpm build
pnpm lint
```

## Testing

Protocol tests require a running buoy instance (docker or local). They are integration tests — not unit tests.

```bash
cd buoy
uv run pytest test/test_protocols.py -v                        # against localhost
uv run pytest test/test_protocols.py -v --host 1.2.3.4        # against remote host
uv run pytest test/test_protocols.py -v -k performance         # only performance suite
uv run pytest test/test_protocols.py -v -k "not nmap" --timeout 3
```

Do **not** mock the network stack in these tests — they must hit a real running buoy.

## Docker

### Buoy
```bash
cd buoy
docker compose up --build
```

Logs are written to `./logs/honeypot.log` (mounted as `/data` in the container).

### Full stack (buoy + dashboard)
Both services define their own `docker-compose.yml`. Run them on the same Docker network (`buoy-net`). The buoy forwarder POSTs to `http://network-buoy-dashboard:3000/api/ingest` by default.

## Environment variables

### Buoy

| Variable         | Default                          | Description                                      |
|-----------------|----------------------------------|--------------------------------------------------|
| `LLM_ENABLED`   | `"false"`                        | Set `"true"` to enable LLM response generation  |
| `LLM_PROVIDER`  | `"ollama"`                       | `ollama` / `openai` / `anthropic` / `openai_compatible` |
| `LLM_MODEL`     | provider default                 | Model name override                              |
| `LLM_BASE_URL`  | provider default                 | Base URL override (required for ollama + openai_compatible) |
| `LLM_API_KEY`   | `""`                             | API key (required for openai / anthropic)        |
| `NODE_ID`       | hostname                         | Identity label attached to forwarded events      |
| `INGEST_URL`    | `""`                             | Dashboard `/api/ingest` URL for the HTTP forwarder |
| `API_TOKEN`     | `""`                             | Bearer token for the ingest endpoint             |
| `FLUSH_INTERVAL`| `5` (seconds)                    | Forwarder flush interval                         |
| `BATCH_SIZE`    | `50`                             | Forwarder max batch size before early flush      |
| `HONEYPOT_LOG`  | `honeypot.log`                   | Path to the JSONL log file                       |

## Code style

- **Python**: ruff enforces pycodestyle (E/W), pyflakes (F), isort (I), pyupgrade (UP), bugbear (B), comprehensions (C4), simplify (SIM). Line length 110. Double quotes. mypy strict-ish (`warn_return_any`, `no_implicit_reexport`).
- **TypeScript**: ESLint via `eslint-config-next`. TypeScript 6. Strict mode.
- No comments unless the WHY is non-obvious. No docstrings.
- No unnecessary abstractions — three similar lines beats a premature helper.
- No error handling for impossible cases. Trust framework guarantees. Only validate at system boundaries.

## Adding a new protocol

1. Create `buoy/buoy/protocols/<name>.py` with a `handle_<name>(conn: socket.socket) -> None` function.
2. Export it from `buoy/buoy/protocols/__init__.py`.
3. Add a `(port, "Name", handle_<name>)` entry to `PROTOCOLS` in `buoy/buoy/config.py`.
4. Add the port to the `ports:` section in `buoy/docker-compose.yml`.
5. Add a `Test<Name>` class to `buoy/test/test_protocols.py`.

## Deployment

- **ECS**: see `deploy/ecs/` — task definition JSON + deploy shell script.
- **Kubernetes**: see `deploy/k8s/` — namespace, deployment, service, PVC, kustomization.
