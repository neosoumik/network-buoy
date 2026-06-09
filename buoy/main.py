import threading

from buoy import PROTOCOLS, start_listener
from buoy.logger import register_event_hook
from buoy.prompts import start as start_cache
from forwarders import load as load_forwarders


def run() -> None:
    for hook in load_forwarders():
        register_event_hook(hook)

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
