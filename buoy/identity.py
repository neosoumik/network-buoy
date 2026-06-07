"""
Stable node identity derived from NODE_ID env var.

All values are deterministic: same NODE_ID → same hostname, IPs, UUIDs,
server versions, cluster names across every restart and every replica.
Set NODE_ID to anything unique per deployment (e.g. an ECS task ARN
suffix, a K8s pod name, a random string you generate once at deploy time).
"""

import hashlib
import os
import struct

# The single source of truth. Override per deployment.
NODE_ID = os.environ.get("NODE_ID", "buoy-default")

# ── Internal helpers ──────────────────────────────────────────────────────────


def _h(salt: str) -> bytes:
    """Deterministic 32-byte hash of NODE_ID + salt."""
    return hashlib.sha256(f"{NODE_ID}:{salt}".encode()).digest()


def _hx(salt: str, n: int) -> str:
    """Hex string of first n bytes."""
    return _h(salt)[:n].hex()


def _hi(salt: str) -> int:
    """First 4 bytes as unsigned int."""
    return int(struct.unpack(">I", _h(salt)[:4])[0])


def _pick(salt: str, options: list[str]) -> str:
    return options[_hi(salt) % len(options)]


# ── Stable identity values ─────────────────────────────────────────────────────

# Hostname — looks like a real corp server name
_name_parts = [
    ["prod", "api", "db", "cache", "web", "app", "svc", "auth", "gw"],
    ["01", "02", "03", "04", "05", "06"],
]
HOSTNAME: str = (
    _pick("hostname_a", _name_parts[0])
    + "-"
    + _pick("hostname_b", _name_parts[0])
    + "-"
    + _pick("hostname_num", _name_parts[1])
)  # e.g. "prod-api-03"

# Internal IP (RFC1918 10.x.x.x)
_ip_b = _hi("ip_b") % 16  # 10.0–10.15
_ip_c = _hi("ip_c") % 256
_ip_d = (_hi("ip_d") % 254) + 1
INTERNAL_IP: str = f"10.{_ip_b}.{_ip_c}.{_ip_d}"

# Last-login source IP (looks like another internal host)
_ll_c = _hi("ll_c") % 256
_ll_d = (_hi("ll_d") % 254) + 1
LAST_LOGIN_IP: str = f"10.{_ip_b}.{_ll_c}.{_ll_d}"

# Last-login date — stable, recent-ish, not today
_days_ago = (_hi("login_days") % 6) + 1  # 1–6 days ago
_hour = (_hi("login_hour") % 10) + 8  # 08–17
_min = _hi("login_min") % 60
_sec = _hi("login_sec") % 60
LAST_LOGIN_DATE: str = f"Fri Jun  {7 - _days_ago} {_hour:02d}:{_min:02d}:{_sec:02d} 2026"

# MySQL connection_id and auth nonces
MYSQL_CONNECTION_ID: int = (_hi("mysql_conn_id") % 9000) + 1000
MYSQL_AUTH_NONCE_1: bytes = _h("mysql_nonce_1")[:8]  # 8 bytes for auth_data_1
MYSQL_AUTH_NONCE_2: bytes = _h("mysql_nonce_2")[:12]  # 12 bytes for auth_data_2

# SSH session cookie (16 bytes in KEXINIT)
SSH_COOKIE: bytes = _h("ssh_cookie")[:16]

# Elasticsearch node + cluster identity
ES_NODE_NAME: str = f"node-{_pick('es_node', ['1', '2', '3', '01', '02'])}"
ES_CLUSTER_NAME: str = (
    _pick("es_cluster_a", ["prod", "staging", "search", "logs", "data"])
    + "-"
    + _pick("es_cluster_b", ["search", "index", "store", "es", "cluster"])
)
ES_CLUSTER_UUID: str = _hx("es_uuid", 16)  # 32-char hex, realistic looking

# Redis uptime (stable large number, looks like it's been running a while)
REDIS_UPTIME: int = (_hi("redis_uptime") % 7_000_000) + 500_000  # ~6–86 days
REDIS_CLIENTS: int = (_hi("redis_clients") % 45) + 5
REDIS_MEMORY: str = f"{(_hi('redis_mem') % 3000 + 500) / 1000:.2f}G"
REDIS_CMDS: int = (_hi("redis_cmds") % 90_000_000) + 1_000_000

# K8s cluster domain
K8S_CLUSTER: str = (
    _pick("k8s_cluster", ["k8s", "eks", "gke", "aks"])
    + "-"
    + _pick("k8s_env", ["prod", "staging", "us-east-1", "eu-west-1"])
)

# Jenkins session token (stable per node)
JENKINS_SESSION: str = _hx("jenkins_session", 4)

# Prometheus instance label
PROM_INSTANCE: str = f"{HOSTNAME}:9090"

# Company name (for HTTP/Jenkins HTML)
COMPANY: str = _pick(
    "company",
    [
        "Acme Corp",
        "Initech Solutions",
        "Pinnacle Systems",
        "Nexus Technologies",
        "Meridian Analytics",
        "CoreStack Inc",
    ],
)
