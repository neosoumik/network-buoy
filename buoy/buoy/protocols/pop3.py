import socket

from ..logger import log_credential
from ..prompts import POP3_BANNER


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


def handle_pop3(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            banner = POP3_BANNER.get().strip()
            if not banner.startswith("+OK"):
                banner = f"+OK {banner}"
            conn.sendall(f"{banner}\r\n".encode())

            username = ""

            while True:
                line = _recv_line(conn)
                if not line:
                    break
                parts = line.split(None, 1)
                cmd = parts[0].upper() if parts else ""
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "CAPA":
                    conn.sendall(b"+OK Capability list follows\r\nTOP\r\nUSER\r\nUIDL\r\nRESP-CODES\r\n.\r\n")

                elif cmd == "USER":
                    username = arg
                    conn.sendall(b"+OK User accepted\r\n")

                elif cmd == "PASS":
                    log_credential("POP3", ip_str, username=username, password=arg)
                    conn.sendall(b"+OK Logged in.\r\n")

                elif cmd == "APOP":
                    apop_parts = arg.split(None, 1)
                    apop_user = apop_parts[0] if apop_parts else arg
                    apop_digest = apop_parts[1] if len(apop_parts) > 1 else ""
                    log_credential("POP3", ip_str, username=apop_user, extra={"apop_digest": apop_digest})

                    conn.sendall(b"+OK Logged in.\r\n")

                elif cmd == "STAT":
                    conn.sendall(b"+OK 0 0\r\n")

                elif cmd == "LIST":
                    conn.sendall(b"+OK 0 messages (0 octets)\r\n.\r\n")

                elif cmd == "UIDL":
                    conn.sendall(b"+OK\r\n.\r\n")

                elif cmd == "RETR" or cmd == "DELE":
                    conn.sendall(b"-ERR No such message.\r\n")

                elif cmd == "NOOP" or cmd == "RSET":
                    conn.sendall(b"+OK\r\n")

                elif cmd == "QUIT":
                    conn.sendall(b"+OK Goodbye.\r\n")
                    break

                else:
                    conn.sendall(b"-ERR Unknown command.\r\n")

        except OSError:
            pass
