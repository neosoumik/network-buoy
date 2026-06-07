import threading

from buoy import PROTOCOLS, start_listener
from buoy.prompts import start as start_cache


def run() -> None:
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
