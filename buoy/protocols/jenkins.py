import socket
from datetime import UTC, datetime

from ..logger import log_credential
from ..prompts import JENKINS_PAGE
from ._http_utils import parse_authorization, parse_form_body, recv_request

_LOGIN_FORM = b"""<!DOCTYPE html>
<html><head><title>Sign in [Jenkins]</title></head>
<body><form method="POST" action="/j_spring_security_check">
<input name="j_username" type="text"/>
<input name="j_password" type="password"/>
<input name="Submit" type="submit" value="Sign in"/>
</form></body></html>"""


def handle_jenkins(conn: socket.socket) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            first_line, headers, body = recv_request(conn)
            parts = first_line.split()
            method = parts[0] if parts else "GET"
            path = parts[1] if len(parts) > 1 else "/"
            version = parts[2] if len(parts) > 2 else "HTTP/1.1"

            # Capture Basic/Bearer auth from headers
            scheme, username, secret = parse_authorization(headers)
            if scheme or username or secret:
                log_credential(
                    "Jenkins",
                    ip_str,
                    username=username,
                    password=secret if scheme == "basic" else "",
                    token=secret if scheme != "basic" else "",
                    extra={"scheme": scheme, "path": path},
                )

            # Capture form login POST to /j_spring_security_check
            if method == "POST" and "j_spring_security_check" in path:
                form = parse_form_body(body)
                j_user = form.get("j_username", "")
                j_pass = form.get("j_password", "")
                if j_user or j_pass:
                    log_credential("Jenkins", ip_str, username=j_user, password=j_pass, extra={"path": path})
                # Redirect back to login — looks like failed auth
                date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
                conn.sendall(
                    (
                        f"{version} 302 Found\r\n"
                        f"Date: {date}\r\n"
                        f"Location: /loginError\r\n"
                        f"X-Jenkins: 2.452.3\r\n"
                        f"Connection: close\r\n"
                        f"\r\n"
                    ).encode()
                )
                return

            # Serve login page (or main page if already hitting /api endpoints)
            if path.startswith("/api"):
                page = JENKINS_PAGE.get().encode("utf-8", errors="replace")
            else:
                page = _LOGIN_FORM

            date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
            response = (
                f"{version} 200 OK\r\n"
                f"Date: {date}\r\n"
                f"Server: Jetty(10.0.18)\r\n"
                f"Content-Type: text/html;charset=utf-8\r\n"
                f"Content-Length: {len(page)}\r\n"
                f"X-Content-Type-Options: nosniff\r\n"
                f"X-Hudson: 1.395\r\n"
                f"X-Jenkins: 2.452.3\r\n"
                f"X-Jenkins-Session: 3f8a1b2c\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode() + page

            conn.sendall(response)
        except OSError:
            pass
