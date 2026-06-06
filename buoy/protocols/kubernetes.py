import socket
from datetime import UTC, datetime

from ..logger import log_credential
from ..prompts import K8S_UNAUTH
from ._http_utils import parse_authorization, recv_request


def handle_kubernetes(conn: socket.socket) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            # TLS ClientHello or plain HTTP may arrive — try to parse as HTTP first
            first_line, headers, _body = recv_request(conn)
            parts = first_line.split()
            path = parts[1] if len(parts) > 1 else "/"

            scheme, username, secret = parse_authorization(headers)
            if scheme or username or secret:
                log_credential(
                    "Kubernetes",
                    ip_str,
                    username=username,
                    token=secret,
                    extra={"scheme": scheme, "path": path},
                )

            body = K8S_UNAUTH.get().encode("utf-8", errors="replace")
            date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
            response = (
                f"HTTP/1.1 401 Unauthorized\r\n"
                f"Date: {date}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {len(body)}\r\n"
                f'Www-Authenticate: Bearer realm="https://k8s.corp.internal/openid/v1/jwks"\r\n'
                f"X-Content-Type-Options: nosniff\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode() + body

            conn.sendall(response)
        except OSError:
            pass
