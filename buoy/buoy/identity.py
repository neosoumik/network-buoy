import hashlib
import os
import struct

NODE_ID = os.environ.get("NODE_ID", "buoy-default")


def _h(salt: str) -> bytes:
    return hashlib.sha256(f"{NODE_ID}:{salt}".encode()).digest()


def _hx(salt: str, n: int) -> str:
    return _h(salt)[:n].hex()


def _hi(salt: str) -> int:
    return int(struct.unpack(">I", _h(salt)[:4])[0])


def _pick(salt: str, options: list[str]) -> str:
    return options[_hi(salt) % len(options)]


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
)

_ip_b = _hi("ip_b") % 16
_ip_c = _hi("ip_c") % 256
_ip_d = (_hi("ip_d") % 254) + 1
INTERNAL_IP: str = f"10.{_ip_b}.{_ip_c}.{_ip_d}"

_ll_c = _hi("ll_c") % 256
_ll_d = (_hi("ll_d") % 254) + 1
LAST_LOGIN_IP: str = f"10.{_ip_b}.{_ll_c}.{_ll_d}"

_days_ago = (_hi("login_days") % 6) + 1
_hour = (_hi("login_hour") % 10) + 8
_min = _hi("login_min") % 60
_sec = _hi("login_sec") % 60
LAST_LOGIN_DATE: str = f"Fri Jun  {7 - _days_ago} {_hour:02d}:{_min:02d}:{_sec:02d} 2026"

MYSQL_CONNECTION_ID: int = (_hi("mysql_conn_id") % 9000) + 1000
MYSQL_AUTH_NONCE_1: bytes = _h("mysql_nonce_1")[:8]
MYSQL_AUTH_NONCE_2: bytes = _h("mysql_nonce_2")[:12]

SSH_COOKIE: bytes = _h("ssh_cookie")[:16]

ES_NODE_NAME: str = f"node-{_pick('es_node', ['1', '2', '3', '01', '02'])}"
ES_CLUSTER_NAME: str = (
    _pick("es_cluster_a", ["prod", "staging", "search", "logs", "data"])
    + "-"
    + _pick("es_cluster_b", ["search", "index", "store", "es", "cluster"])
)
ES_CLUSTER_UUID: str = _hx("es_uuid", 16)

REDIS_UPTIME: int = (_hi("redis_uptime") % 7_000_000) + 500_000
REDIS_CLIENTS: int = (_hi("redis_clients") % 45) + 5
REDIS_MEMORY: str = f"{(_hi('redis_mem') % 3000 + 500) / 1000:.2f}G"
REDIS_CMDS: int = (_hi("redis_cmds") % 90_000_000) + 1_000_000

K8S_CLUSTER: str = (
    _pick("k8s_cluster", ["k8s", "eks", "gke", "aks"])
    + "-"
    + _pick("k8s_env", ["prod", "staging", "us-east-1", "eu-west-1"])
)

JENKINS_SESSION: str = _hx("jenkins_session", 4)

PROM_INSTANCE: str = f"{HOSTNAME}:9090"

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
