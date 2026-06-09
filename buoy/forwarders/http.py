import json
import threading
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime

_FLUSH_INTERVAL = 5.0
_BATCH_SIZE = 50


def _to_event(entry: dict) -> dict:
    event_type = "LOGIN" if entry.get("event") == "credential" else "NETCONN"
    ev: dict = {
        "EventTime": entry.get("timestamp", datetime.now(UTC).isoformat()),
        "EventType": event_type,
        "SeverityLevel": "E_CRITICAL" if event_type == "LOGIN" else "E_WARNING",
        "Protocol": entry.get("protocol", ""),
        "SrcIP": entry.get("ip", ""),
        "RawData": entry.get("data", ""),
    }
    if entry.get("username"):
        ev["Username"] = entry["username"]
    if entry.get("password"):
        ev["Password"] = entry["password"]
    if entry.get("token"):
        ev["Password"] = entry["token"]
    return ev


class _Forwarder:
    def __init__(self, url: str, token: str, flush_interval: float, batch_size: int) -> None:
        self._url = url
        self._token = token
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._batch: list[dict] = []
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def __call__(self, entry: dict) -> None:
        with self._lock:
            self._batch.append(_to_event(entry))
            full = len(self._batch) >= self._batch_size

        if full:
            self._flush()
        else:
            self._schedule()

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(self._flush_interval, self._flush)
                self._timer.daemon = True
                self._timer.start()

    def _flush(self) -> None:
        with self._lock:
            batch = self._batch.copy()
            self._batch.clear()
            self._timer = None
        if not batch:
            return
        body = json.dumps(batch).encode()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"ApiToken {self._token}"
        req = urllib.request.Request(self._url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception:
            pass  # never crash the honeypot on network issues


def make(
    url: str,
    token: str = "",
    flush_interval: float = _FLUSH_INTERVAL,
    batch_size: int = _BATCH_SIZE,
) -> Callable[[dict], None]:
    return _Forwarder(url, token, flush_interval, batch_size)
