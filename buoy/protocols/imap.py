import base64
import socket

from ..logger import log_credential
from ..prompts import IMAP_BANNER


def _recv_line(conn: socket.socket) -> str:
    buf = b""
    while True:
        byte = conn.recv(1)
        if not byte:
            break
        buf += byte
        if byte == b"\n":
            break
    return buf.decode("utf-8", errors="replace").strip()


def handle_imap(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            banner = IMAP_BANNER.get().strip()
            if not banner.startswith("* OK"):
                banner = f"* OK {banner}"
            conn.sendall(f"{banner}\r\n".encode())

            authed = False

            while True:
                line = _recv_line(conn)
                if not line:
                    break

                parts = line.split(None, 2)
                if len(parts) < 2:
                    continue
                tag, cmd = parts[0], parts[1].upper()
                arg = parts[2] if len(parts) > 2 else ""

                if cmd == "CAPABILITY":
                    conn.sendall(
                        b"* CAPABILITY IMAP4rev1 STARTTLS AUTH=PLAIN AUTH=LOGIN IDLE NAMESPACE\r\n"
                        + f"{tag} OK Capability completed.\r\n".encode()
                    )

                elif cmd == "LOGIN":
                    # arg = "username password" (quoted or bare)
                    cred_parts = arg.replace('"', "").split(None, 1)
                    username = cred_parts[0] if cred_parts else ""
                    password = cred_parts[1] if len(cred_parts) > 1 else ""
                    log_credential("IMAP", ip_str, username=username, password=password)
                    authed = True
                    conn.sendall(f"{tag} OK [CAPABILITY IMAP4rev1] LOGIN completed.\r\n".encode())

                elif cmd == "AUTHENTICATE":
                    mechanism = arg.upper()
                    conn.sendall(b"+ \r\n")
                    token = _recv_line(conn)
                    try:
                        decoded = base64.b64decode(token + "==").decode("utf-8", errors="replace")
                        cred_parts = decoded.split("\x00")
                        username = cred_parts[1] if len(cred_parts) >= 3 else decoded
                        password = cred_parts[2] if len(cred_parts) >= 3 else ""
                    except Exception:
                        username, password = token, ""
                    log_credential(
                        "IMAP",
                        ip_str,
                        username=username,
                        password=password,
                        extra={"mechanism": mechanism},
                    )
                    authed = True
                    conn.sendall(f"{tag} OK AUTHENTICATE completed.\r\n".encode())

                elif cmd == "SELECT":
                    if authed:
                        # Pretend to select but serve empty mailbox
                        conn.sendall(
                            b"* 0 EXISTS\r\n"
                            b"* 0 RECENT\r\n"
                            b"* OK [UNSEEN 0]\r\n"
                            b"* OK [UIDVALIDITY 1]\r\n"
                            b"* OK [UIDNEXT 1]\r\n" + f"{tag} OK [READ-WRITE] SELECT completed.\r\n".encode()
                        )
                    else:
                        conn.sendall(f"{tag} NO Not authenticated.\r\n".encode())

                elif cmd == "EXAMINE":
                    conn.sendall(
                        b"* 0 EXISTS\r\n* 0 RECENT\r\n"
                        + f"{tag} OK [READ-ONLY] EXAMINE completed.\r\n".encode()
                    )

                elif cmd in ("FETCH", "SEARCH", "STORE", "COPY", "UID"):
                    conn.sendall(f"{tag} OK Completed.\r\n".encode())

                elif cmd == "LIST":
                    conn.sendall(
                        b'* LIST (\\HasNoChildren) "/" INBOX\r\n' + f"{tag} OK LIST completed.\r\n".encode()
                    )

                elif cmd == "LSUB":
                    conn.sendall(f"{tag} OK LSUB completed.\r\n".encode())

                elif cmd == "STARTTLS":
                    conn.sendall(f"{tag} OK Begin TLS negotiation.\r\n".encode())
                    break

                elif cmd == "NOOP":
                    conn.sendall(f"{tag} OK NOOP completed.\r\n".encode())

                elif cmd == "LOGOUT":
                    conn.sendall(b"* BYE Logging out.\r\n")
                    conn.sendall(f"{tag} OK LOGOUT completed.\r\n".encode())
                    break

                else:
                    conn.sendall(f"{tag} BAD Unknown command.\r\n".encode())

        except OSError:
            pass
