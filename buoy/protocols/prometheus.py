import socket
from datetime import UTC, datetime

from ..prompts import PROM_METRICS


def _recv_headers(conn: socket.socket) -> bytes:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf


def handle_prometheus(conn: socket.socket) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            raw = _recv_headers(conn)
            first_line = raw.split(b"\r\n")[0].decode("utf-8", errors="replace")
            parts = first_line.split()
            path = parts[1] if len(parts) > 1 else "/"
            version = parts[2] if len(parts) > 2 else "HTTP/1.1"

            if path.rstrip("/") == "/metrics":
                body = PROM_METRICS.get().encode("utf-8", errors="replace")
                content_type = "text/plain; version=0.0.4; charset=utf-8"
                status = "200 OK"
            else:
                body = b"<html><body><h1>Prometheus</h1><a href='/metrics'>Metrics</a></body></html>"
                content_type = "text/html; charset=utf-8"
                status = "200 OK"

            date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
            response = (
                f"{version} {status}\r\n"
                f"Date: {date}\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode() + body

            conn.sendall(response)
        except OSError:
            pass
