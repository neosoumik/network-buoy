import contextlib
import json
import logging
import os
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from .cache import record_activity

LOG_FILE = Path(os.environ.get("HONEYPOT_LOG", "honeypot.log"))

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_log_lock = threading.Lock()
_hooks: list[Callable[[dict], None]] = []
_hooks_lock = threading.Lock()


def register_event_hook(fn: Callable[[dict], None]) -> None:
    with _hooks_lock:
        _hooks.append(fn)


def _write(entry: dict) -> None:
    record_activity()
    line = json.dumps(entry)
    with _log_lock, LOG_FILE.open("a") as f:
        f.write(line + "\n")
    with _hooks_lock:
        hooks = list(_hooks)
    for fn in hooks:
        with contextlib.suppress(Exception):
            fn(entry)


def log_connection(protocol: str, ip: str, data: bytes) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "connection",
        "protocol": protocol,
        "ip": ip,
        "data": data.decode("utf-8", errors="replace"),
    }
    _write(entry)
    logger.info("logged %s connection from %s", protocol, ip)


def log_credential(
    protocol: str,
    ip: str,
    *,
    username: str = "",
    password: str = "",
    token: str = "",
    extra: dict | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "credential",
        "protocol": protocol,
        "ip": ip,
    }
    if username:
        entry["username"] = username
    if password:
        entry["password"] = password
    if token:
        entry["token"] = token
    if extra:
        entry.update(extra)

    _write(entry)
    logger.info(
        "*** CREDENTIAL captured on %s from %s: user=%r token=%r",
        protocol,
        ip,
        username or token,
        password,
    )
