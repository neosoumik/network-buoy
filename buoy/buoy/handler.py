import logging
import socket
from collections.abc import Callable

from .logger import log_connection

logger = logging.getLogger(__name__)


def handle_connection(conn: socket.socket, name: str, handler: Callable[[socket.socket], None]) -> None:
    try:
        ip = conn.getpeername()
        ip_str = f"{ip[0]}:{ip[1]}"
    except OSError:
        conn.close()
        return

    logger.info("%s connection from: %s", name, ip_str)
    log_connection(name, ip_str, b"")
    handler(conn)
