# network-buoy

Before diving in — have you watched Battleship (2012)? If yes, great taste. If not, fix that first.

As a tsunami buoy gets hit by a wave and records it, network-buoy deploys the same idea on a network: anything that hits it gets recorded. But it doesn't just record — it **captures credentials**. Something authenticates → it accepts the creds, logs them, then fails gracefully. The attacker thinks they found a real target. You get their keys.

![tsunami buoy map from Battleship](https://www.artofvfx.com/BATTLESHIP/BS_PROLOGUE_VFX_09.jpg)

---

## What it does

Spins up 19 fake protocol listeners across the most-scanned ports on the internet. When anything connects, it:

1. **Speaks the real protocol** — sends proper banners, negotiates auth, behaves like the real service
2. **Captures credentials** — accepts logins, decodes auth tokens, extracts passwords from binary wire formats
3. **Stalls and misleads** — accepts auth, serves plausible fake data, then fails quietly
4. **Logs everything** to `honeypot.log` as newline-delimited JSON
5. **Generates dynamic content** via LLM (opt-in) — banners and listings are unique per node, consistent across retries (seeded from `NODE_ID`)
6. **Forwards events** to any HTTP ingest endpoint — one URL swap, no code changes

---

## Ports & Protocols

| Port  | Protocol      | Emulation                                                                         |
|-------|---------------|-----------------------------------------------------------------------------------|
| 22    | SSH           | RFC 4253 banner + KEXINIT, captures username + password from USERAUTH_REQUEST     |
| 21    | FTP           | Full USER/PASS flow, LLM directory listing, denies writes                         |
| 23    | Telnet        | IAC negotiation, fails first login (realistic), accepts second, fake root shell   |
| 25    | SMTP          | EHLO/AUTH PLAIN+LOGIN, decodes base64, captures username + password               |
| 80    | HTTP          | nginx headers, LLM HTML body, captures Basic auth + Bearer tokens                 |
| 110   | POP3          | Full USER/PASS + APOP, serves empty mailbox                                       |
| 143   | IMAP          | LOGIN + AUTHENTICATE PLAIN, serves empty INBOX                                    |
| 389   | LDAP          | BER BindResponse                                                                  |
| 443   | HTTPS         | TLS 1.2 ServerHello bytes                                                         |
| 445   | SMB           | SMB2 Negotiate Response with NetBIOS header                                       |
| 3306  | MySQL         | HandshakeV10, extracts username from binary HandshakeResponse41                   |
| 3389  | RDP           | X.224 CC TPDU                                                                     |
| 5432  | PostgreSQL    | SSLRequest → StartupMessage → AuthCleartextPassword → plaintext capture           |
| 6379  | Redis         | AUTH (password + user:password forms), full RESP command set, pipeline support    |
| 6443  | Kubernetes    | 401 + `Www-Authenticate` Bearer challenge, captures Bearer tokens                 |
| 8080  | Jenkins       | Login page + POST `/j_spring_security_check` form capture, Basic auth             |
| 9090  | Prometheus    | LLM-generated `/metrics` output                                                   |
| 9200  | Elasticsearch | LLM cluster JSON, captures Basic + Bearer tokens                                  |
| 27017 | MongoDB       | OP_REPLY with BSON `{ok:1.0}`                                                     |

---

## Log format

Two event types, newline-delimited JSON in `honeypot.log`:

```json
{"timestamp": "2026-06-07T14:23:01+00:00", "event": "connection", "protocol": "SSH", "ip": "45.33.32.156:52741"}
{"timestamp": "2026-06-07T14:23:03+00:00", "event": "credential", "protocol": "SSH", "ip": "45.33.32.156:52741", "username": "root", "password": "changeme123", "method": "password"}
{"timestamp": "2026-06-07T14:23:08+00:00", "event": "credential", "protocol": "PostgreSQL", "ip": "10.0.0.5:44123", "username": "admin", "password": "postgres", "database": "prod"}
{"timestamp": "2026-06-07T14:23:12+00:00", "event": "credential", "protocol": "Jenkins", "ip": "185.220.101.9:61200", "username": "admin", "password": "admin123"}
```

---

## Stack

| Layer        | Choice                                                                     |
|--------------|----------------------------------------------------------------------------|
| Language     | Python 3.14t — free-threaded CPython, GIL disabled, real OS-level threads  |
| Package mgmt | [uv](https://github.com/astral-sh/uv) — interpreter + venv + deps         |
| Lint / types | ruff + mypy                                                                |
| LLM          | Any provider via `LLM_PROVIDER` — Ollama, OpenAI, Anthropic, or any OpenAI-compatible endpoint |
| Container    | Docker — single image, Debian + uv                                         |
| Dashboard    | Next.js — PoC sci-fi HUD, local ingest endpoint for demos                  |

---

## Running with Docker

```bash
# Start the honeypot
docker compose -f buoy/docker-compose.yml up -d

# Start the dashboard (optional)
docker compose -f dashboard/docker-compose.yml up -d

# Tail logs
tail -f buoy/logs/honeypot.log | python3 -m json.tool

# Credential captures only
grep '"event": "credential"' buoy/logs/honeypot.log | python3 -m json.tool
```

---

## Running locally (dev)

```bash
cd buoy
uv run main.py
```

Without LLM configured, all banners fall back to static strings — zero CPU overhead.

---

## Environment variables

### Buoy

| Variable         | Default              | Description                                                                |
|------------------|----------------------|----------------------------------------------------------------------------|
| `NODE_ID`        | `buoy-default`       | Seeds all fake identity — hostname, IPs, banners. Set once, never change   |
| `HONEYPOT_LOG`   | `honeypot.log`       | Log file path (`/data/honeypot.log` in container)                          |
| `LLM_ENABLED`    | _(unset)_            | Set to `true` to enable LLM-generated dynamic content                      |
| `LLM_PROVIDER`   | `ollama`             | `ollama` \| `openai` \| `anthropic` \| `openai_compatible`                |
| `LLM_MODEL`      | _(provider default)_ | Model name — e.g. `gemma4:latest`, `gpt-4o-mini`, `claude-haiku-4-5-20251001` |
| `LLM_BASE_URL`   | _(provider default)_ | API base URL — required for `ollama` and `openai_compatible`              |
| `LLM_API_KEY`    | _(unset)_            | API key — required for `openai`, `anthropic`, and secured endpoints        |
| `INGEST_URL`     | _(unset)_            | Activates event forwarding to any HTTP endpoint                            |
| `API_TOKEN`      | _(unset)_            | Sent as `Authorization: ApiToken <token>` — leave blank if not required   |
| `FLUSH_INTERVAL` | `5`                  | Seconds between batch flushes to ingest endpoint                           |
| `BATCH_SIZE`     | `50`                 | Events per flush                                                           |

### Dashboard

| Variable     | Default   | Description                                                                   |
|--------------|-----------|-------------------------------------------------------------------------------|
| `API_TOKEN`  | _(unset)_ | If set, requires `Authorization: ApiToken <token>` on `POST /api/ingest`     |

---

## Event forwarding

Set `INGEST_URL` in `buoy/docker-compose.yml` to activate forwarding. Point it at the local dashboard, a SIEM, or any HTTP endpoint that accepts JSON arrays:

```yaml
# buoy/docker-compose.yml
environment:
  # Local dashboard
  INGEST_URL: "http://network-buoy-dashboard:3000/api/ingest"

  # Any HTTP ingest endpoint
  # INGEST_URL: "https://<your-endpoint>/..."
  # API_TOKEN:  "your-token"
```

The forwarder batches events and POSTs them as JSON arrays. The schema is stable — no code changes when switching destinations.

---

## Dashboard (PoC)

A demo-only sci-fi HUD for local presentations. Spins up an ingest endpoint (`POST /api/ingest`) so you can point buoy at it and watch attacks visualise in real-time.

See [dashboard/README.md](dashboard/README.md) for setup.

---

## Deployment

- [**ECS Fargate**](deploy/ecs/README.md) — single task, EFS for logs, SSM for NODE_ID
- [**Kubernetes**](deploy/k8s/README.md) — Deployment + NLB Service, works on EKS/GKE/AKS

---

## Project layout

```
network-buoy/
├── buoy/                        ← honeypot — self-contained Python image
│   ├── buoy/                    ← source package
│   │   ├── identity.py          ← stable node identity seeded from NODE_ID
│   │   ├── config.py            ← PROTOCOLS list
│   │   ├── logger.py            ← thread-safe JSON logging + event hooks
│   │   ├── llm.py               ← generic LLM client (multi-provider)
│   │   ├── cache.py             ← pre-warmed LLM response pool
│   │   ├── prompts.py           ← per-protocol LLM prompts
│   │   └── protocols/           ← one file per protocol
│   ├── forwarders/
│   │   └── http.py              ← generic HTTP forwarder
│   ├── test/                    ← pytest suite (186 tests, all protocols)
│   ├── main.py                  ← wires forwarders + starts listeners
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── pyproject.toml
├── dashboard/                   ← self-contained Next.js app
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── src/
│       ├── app/api/ingest/      ← POST — receives events from buoy
│       ├── app/api/events/      ← GET SSE — streams events to browser
│       └── ...
└── deploy/
    ├── ecs/                     ← ECS Fargate manifests + deploy script
    └── k8s/                     ← Kubernetes manifests (kustomize)
```

---

## License

[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html)
