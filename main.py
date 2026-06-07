import os
import threading

from buoy import PROTOCOLS, start_listener
from buoy.prompts import start as start_cache
from buoy.ws_broadcast import start as start_ws


def run() -> None:
    # Start WebSocket broadcast server for the dashboard
    ws_port = int(os.environ.get("WS_PORT", "4444"))
    start_ws(ws_port)

    # Kick off background LLM pre-warm threads before binding any ports
    start_cache()

    listeners = [
        threading.Thread(
            target=start_listener,
            args=(port, name, handler),
            daemon=True,
            name=f"listener-{name}",
        )
        for port, name, handler in PROTOCOLS
    ]
    for t in listeners:
        t.start()
    for t in listeners:
        t.join()


if __name__ == "__main__":
    run()
