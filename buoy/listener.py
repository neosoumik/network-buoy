import logging
import socket
import threading
from collections.abc import Callable

from .handler import handle_connection

logger = logging.getLogger(__name__)


def start_listener(port: int, name: str, handler: Callable[[socket.socket], None]) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("0.0.0.0", port))
        except OSError as e:
            logger.error("failed to bind port %d (%s): %s", port, name, e)
            return

        srv.listen()
        logger.info("listening on port %d (%s)...", port, name)

        while True:
            try:
                conn, _ = srv.accept()
            except OSError as e:
                logger.error("accept error on port %d: %s", port, e)
                continue

            threading.Thread(
                target=handle_connection,
                args=(conn, name, handler),
                daemon=True,
            ).start()
