import socket
from datetime import UTC, datetime

from ..logger import log_credential
from ..prompts import HTTP_BODY
from ._http_utils import parse_authorization, recv_request


def handle_http(conn: socket.socket) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            first_line, headers, _body = recv_request(conn)
            parts = first_line.split()
            version = parts[2] if len(parts) > 2 else "HTTP/1.1"

            scheme, username, secret = parse_authorization(headers)
            if scheme or username or secret:
                log_credential(
                    "HTTP",
                    ip_str,
                    username=username,
                    token=secret if scheme != "basic" else "",
                    password=secret if scheme == "basic" else "",
                    extra={"scheme": scheme, "path": parts[1] if len(parts) > 1 else ""},
                )

            body = HTTP_BODY.get().encode("utf-8", errors="replace")
            date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
            response = (
                f"{version} 200 OK\r\n"
                f"Date: {date}\r\n"
                f"Server: nginx/1.24.0 (Ubuntu)\r\n"
                f"Content-Type: text/html; charset=UTF-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode() + body

            conn.sendall(response)
        except OSError:
            pass
