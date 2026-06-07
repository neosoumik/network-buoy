# network-buoy

What is network buoy? before diving into that question, did you watch the movie Battleship (2012).\
If yes, good to meet a person who has great movie taste. If not please watch it.

As we comeback to the question of what is network buoy, it uses same ideology as that of tsunami buoy.\
As tsunami buoy gets hit by a wave it records the event details, similarly this tool targets to deploy equivalent which on getting hit by movement records it.\
![tsunami buoy map repesentation from movie battleship](https://www.artofvfx.com/BATTLESHIP/BS_PROLOGUE_VFX_09.jpg "tsunami buoy map points")

And now it doesn't just record — it **captures credentials**. Something authenticates → it accepts the creds, logs them, then fails gracefully. The attacker thinks they found a real target. You get their keys.

---

## 🎯 What it does

Spins up 19 fake protocol listeners across the most-scanned ports on the internet. When anything connects, it:

1. **Speaks the real protocol** — sends proper banners, negotiates auth, behaves like the real thing
2. **Captures credentials** — accepts logins, decodes auth tokens, extracts passwords from binary wire formats
3. **Stalls and misleads** — accepts auth, serves plausible fake data, then fails quietly
4. **Logs everything** to `honeypot.log` as newline-delimited JSON — two event types: `connection` and `credential`
5. **Generates dynamic content** via a local LLM (Ollama + gemma3:1b) — banners and listings are unique per node, consistent across retries (seeded from `NODE_ID`)

---

## 🗺️ Ports & Protocols

| Port  | Protocol      | Emulation                                                                       |
|-------|---------------|---------------------------------------------------------------------------------|
| 22    | SSH           | RFC 4253 banner + KEXINIT, captures username + password from USERAUTH_REQUEST   |
| 21    | FTP           | Full USER/PASS flow, LLM directory listing, denies writes                       |
| 23    | Telnet        | IAC negotiation, fails first login (realistic), accepts second, fake root shell |
| 25    | SMTP          | EHLO/AUTH PLAIN+LOGIN, decodes base64, captures username + password             |
| 80    | HTTP          | nginx headers, LLM HTML body, captures Basic auth + Bearer tokens               |
| 110   | POP3          | Full USER/PASS + APOP, serves empty mailbox                                     |
| 143   | IMAP          | LOGIN + AUTHENTICATE PLAIN, serves empty INBOX                                  |
| 389   | LDAP          | BER BindResponse                                                                |
| 443   | HTTPS         | TLS 1.2 ServerHello bytes                                                       |
| 445   | SMB           | SMB2 Negotiate Response with NetBIOS header                                     |
| 3306  | MySQL         | HandshakeV10, extracts username from binary HandshakeResponse41                 |
| 3389  | RDP           | X.224 CC TPDU                                                                   |
| 5432  | PostgreSQL    | SSLRequest → StartupMessage → AuthCleartextPassword challenge → plaintext capture |
| 6379  | Redis         | AUTH (password + user:password forms), full RESP command set                    |
| 6443  | Kubernetes    | 401 + `Www-Authenticate` Bearer challenge, captures Bearer tokens               |
| 8080  | Jenkins       | Login page + POST `/j_spring_security_check` form capture, Basic auth           |
| 9090  | Prometheus    | LLM-generated `/metrics` output                                                 |
| 9200  | Elasticsearch | LLM cluster JSON, captures Basic + Bearer tokens                                |
| 27017 | MongoDB       | OP_REPLY with BSON `{ok:1.0}`                                                   |

---

## 📋 Log format

Two event types, newline-delimited JSON in `honeypot.log`:

```json
{"timestamp": "2026-06-07T14:23:01+00:00", "event": "connection", "protocol": "SSH", "ip": "45.33.32.156:52741"}
{"timestamp": "2026-06-07T14:23:03+00:00", "event": "credential", "protocol": "SSH", "ip": "45.33.32.156:52741", "username": "root", "password": "changeme123", "method": "password"}
{"timestamp": "2026-06-07T14:23:08+00:00", "event": "credential", "protocol": "PostgreSQL", "ip": "10.0.0.5:44123", "username": "admin", "password": "postgres", "database": "prod"}
{"timestamp": "2026-06-07T14:23:12+00:00", "event": "credential", "protocol": "Jenkins", "ip": "185.220.101.9:61200", "username": "admin", "password": "admin123"}
```

---

## ⚡ Stack

| Layer        | Choice                                              |
|--------------|-----------------------------------------------------|
| Language     | Python 3.14t — GIL disabled, real OS-level threads  |
| Package mgmt | [uv](https://github.com/astral-sh/uv) — handles interpreter + venv + deps |
| LLM          | Ollama + gemma3:1b — local inference, dynamic content |
| Container    | Docker — single image, Debian + uv + Ollama bundled |

---

## 🐳 Running with Docker (recommended)

```bash
docker compose up --build

# Tail logs
tail -f logs/honeypot.log | python3 -m json.tool

# Credential captures only
grep '"event": "credential"' logs/honeypot.log | python3 -m json.tool
```

First boot pulls `gemma3:1b` (~800 MB). Subsequent starts use the cached volume.

---

## 🚀 Running locally (dev)

```bash
uv run main.py
```

Without Ollama running, all banners fall back to static strings.

---

## 🔧 Environment variables

| Variable       | Default                  | Description                              |
|----------------|--------------------------|------------------------------------------|
| `NODE_ID`      | `buoy-default`           | Seeds all fake identity — hostname, IPs, banners. Set once per deployment, never change it |
| `HONEYPOT_LOG` | `honeypot.log`           | Log file path (`/data/honeypot.log` in container) |
| `OLLAMA_URL`   | `http://localhost:11434` | Ollama API base URL                      |
| `OLLAMA_MODEL` | `gemma3:1b`              | Model for dynamic content generation     |

---

## 🚢 Deployment

- [**ECS Fargate**](deploy/ecs/README.md) — single task, EFS for logs, SSM for NODE_ID
- [**Kubernetes**](deploy/k8s/README.md) — Deployment + NLB Service, works on EKS/GKE/AKS

---

## 🗂️ Project layout

```
network-buoy/
├── main.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── deploy/
│   ├── ecs/             ← ECS Fargate manifests + deploy script
│   └── k8s/             ← Kubernetes manifests (kustomize)
└── buoy/
    ├── identity.py      ← stable node identity seeded from NODE_ID
    ├── config.py        ← PROTOCOLS list
    ├── logger.py        ← thread-safe JSON logging
    ├── llm.py           ← Ollama client
    ├── cache.py         ← pre-warmed LLM response pool
    ├── prompts.py       ← per-protocol LLM prompts
    └── protocols/       ← one file per protocol
```

---

## Contributing

Contributions are welcome! Please submit a pull request with your proposed changes, and ensure they adhere to the AGPL-3.0 guidelines.

## License

[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html)
