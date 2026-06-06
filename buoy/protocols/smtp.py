import base64
import socket

from ..logger import log_credential
from ..prompts import SMTP_REJECT

_HOSTNAME = "mail.corp.internal"


def _recv_line(conn: socket.socket) -> str:
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = conn.recv(256)
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", errors="replace").strip()


def _decode_auth(mechanism: str, first_token: str, conn: socket.socket) -> tuple[str, str]:
    """Return (username, password) decoded from AUTH exchange, best-effort."""
    try:
        if mechanism == "PLAIN":
            # AUTH PLAIN [initial-response] — base64("\x00user\x00pass")
            token = first_token or _recv_line(conn)
            decoded = base64.b64decode(token + "==").decode("utf-8", errors="replace")
            parts = decoded.split("\x00")
            # format: [authzid] \x00 authcid \x00 passwd
            if len(parts) >= 3:
                return parts[1], parts[2]
            if len(parts) == 2:
                return parts[0], parts[1]

        elif mechanism == "LOGIN":
            # Server sends "Username:" challenge, client replies base64(user)
            conn.sendall(b"334 VXNlcm5hbWU6\r\n")  # "Username:" in b64
            user_b64 = _recv_line(conn)
            conn.sendall(b"334 UGFzc3dvcmQ6\r\n")  # "Password:" in b64
            pass_b64 = _recv_line(conn)
            username = base64.b64decode(user_b64 + "==").decode("utf-8", errors="replace")
            password = base64.b64decode(pass_b64 + "==").decode("utf-8", errors="replace")
            return username.strip(), password.strip()

    except Exception:
        pass
    return first_token, ""


def handle_smtp(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            conn.sendall(f"220 {_HOSTNAME} ESMTP Postfix\r\n".encode())

            while True:
                line = _recv_line(conn)
                if not line:
                    break
                parts = line.split(None, 2)
                cmd = parts[0].upper() if parts else ""

                if cmd in ("EHLO", "HELO"):
                    conn.sendall(
                        (
                            f"250-{_HOSTNAME}\r\n"
                            "250-PIPELINING\r\n"
                            "250-SIZE 10240000\r\n"
                            "250-VRFY\r\n"
                            "250-ETRN\r\n"
                            "250-STARTTLS\r\n"
                            "250-AUTH PLAIN LOGIN\r\n"
                            "250-AUTH=PLAIN LOGIN\r\n"
                            "250-ENHANCEDSTATUSCODES\r\n"
                            "250-8BITMIME\r\n"
                            "250 DSN\r\n"
                        ).encode()
                    )

                elif cmd == "AUTH":
                    mechanism = parts[1].upper() if len(parts) > 1 else ""
                    first_token = parts[2] if len(parts) > 2 else ""

                    if mechanism == "LOGIN":
                        username, password = _decode_auth("LOGIN", first_token, conn)
                    else:
                        if not first_token:
                            conn.sendall(b"334 \r\n")
                            first_token = _recv_line(conn)
                        username, password = _decode_auth(mechanism, first_token, conn)

                    log_credential("SMTP", ip_str, username=username, password=password)
                    # Accept — attacker thinks they authenticated
                    conn.sendall(b"235 2.7.0 Authentication successful\r\n")

                elif cmd == "MAIL":
                    conn.sendall(b"250 2.1.0 Ok\r\n")

                elif cmd == "RCPT":
                    reject = SMTP_REJECT.get().strip()
                    if not reject.startswith("550"):
                        reject = f"550 5.1.1 {reject}"
                    conn.sendall(f"{reject}\r\n".encode())

                elif cmd == "DATA":
                    conn.sendall(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                    while True:
                        chunk = _recv_line(conn)
                        if chunk == ".":
                            break
                    conn.sendall(b"250 2.0.0 Ok: queued as 4F3A2B1C\r\n")

                elif cmd == "QUIT":
                    conn.sendall(b"221 2.0.0 Bye\r\n")
                    break

                elif cmd in ("VRFY", "EXPN"):
                    conn.sendall(b"252 2.0.0 Cannot VRFY user\r\n")

                elif cmd in ("NOOP", "RSET"):
                    conn.sendall(b"250 2.0.0 Ok\r\n")

                else:
                    conn.sendall(b"502 5.5.2 Error: command not recognized\r\n")

        except OSError:
            pass
