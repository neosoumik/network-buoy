"""
Forwarder loader. Set INGEST_URL to activate.
All destinations speak the same honeypot event JSON schema.
"""

import os
from collections.abc import Callable

from forwarders.http import make

_FLUSH_INTERVAL = float(os.environ.get("FLUSH_INTERVAL", "5"))
_BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "50"))


def load() -> list[Callable[[dict], None]]:
    url = os.environ.get("INGEST_URL", "")
    if not url:
        return []
    token = os.environ.get("API_TOKEN", "")
    return [make(url, token, _FLUSH_INTERVAL, _BATCH_SIZE)]
