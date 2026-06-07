"""
Minimal RFC 6455 WebSocket server for broadcasting honeypot events.

Runs on WS_PORT (default 4444). Clients connect and receive a stream of
JSON-encoded log events as they happen. No external dependencies.
"""

import base64
import hashlib
import json
import logging
import socket
import struct
import threading

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

logger = logging.getLogger(__name__)

_clients: set[socket.socket] = set()
_clients_lock = threading.Lock()


def _handshake(conn: socket.socket) -> bool:
    """Perform the HTTP → WebSocket upgrade handshake. Returns True on success."""
    try:
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                return False
            raw += chunk
            if len(raw) > 8192:
                return False

        headers: dict[str, str] = {}
        for line in raw.decode("utf-8", errors="replace").splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                headers[k.strip().lower()] = v.strip()

        key = headers.get("sec-websocket-key", "")
        if not key:
            return False

        accept = base64.b64encode(hashlib.sha1((key + WS_MAGIC).encode()).digest()).decode()

        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        conn.sendall(response.encode())
        return True
    except OSError:
        return False


def _frame(data: str) -> bytes:
    """Encode a text string as an unmasked WebSocket frame (opcode 0x1)."""
    payload = data.encode("utf-8")
    length = len(payload)
    if length <= 125:
        header = struct.pack("BB", 0x81, length)
    elif length <= 65535:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + payload


def _ping_frame() -> bytes:
    return struct.pack("BB", 0x89, 0)


def broadcast(event: dict) -> None:
    """Send a JSON-encoded event to all connected WebSocket clients."""
    frame = _frame(json.dumps(event))
    dead: list[socket.socket] = []
    with _clients_lock:
        for conn in _clients:
            try:
                conn.sendall(frame)
            except OSError:
                dead.append(conn)
        for conn in dead:
            _clients.discard(conn)


def _serve_client(conn: socket.socket) -> None:
    with conn:
        if not _handshake(conn):
            return
        with _clients_lock:
            _clients.add(conn)
        logger.info("dashboard client connected (%d total)", len(_clients))
        try:
            # Keep alive: drain any incoming frames (pings/close), detect disconnect
            conn.settimeout(30.0)
            while True:
                try:
                    header = conn.recv(2)
                    if not header or len(header) < 2:
                        break
                    opcode = header[0] & 0x0F
                    if opcode == 0x8:  # close frame
                        break
                    # consume any payload (masked client frames)
                    masked = bool(header[1] & 0x80)
                    length = header[1] & 0x7F
                    if length == 126:
                        length = struct.unpack("!H", conn.recv(2))[0]
                    elif length == 127:
                        length = struct.unpack("!Q", conn.recv(8))[0]
                    if masked:
                        conn.recv(4)  # masking key
                    if length:
                        conn.recv(length)  # payload
                except TimeoutError:
                    # send ping to keep alive
                    try:
                        conn.sendall(_ping_frame())
                    except OSError:
                        break
        except OSError:
            pass
        finally:
            with _clients_lock:
                _clients.discard(conn)
            logger.info("dashboard client disconnected (%d total)", len(_clients))


def start(port: int = 4444) -> None:
    """Start the WebSocket broadcast server in a daemon thread."""

    def _accept_loop() -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("0.0.0.0", port))
        srv.listen(32)
        logger.info("WebSocket broadcast server listening on :%d", port)
        while True:
            try:
                conn, _ = srv.accept()
                t = threading.Thread(target=_serve_client, args=(conn,), daemon=True)
                t.start()
            except OSError:
                break

    t = threading.Thread(target=_accept_loop, daemon=True)
    t.start()
