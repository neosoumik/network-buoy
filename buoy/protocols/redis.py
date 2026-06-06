import socket

from ..logger import log_credential
from ..prompts import REDIS_INFO


def _recv_command(conn: socket.socket) -> list[str]:
    buf = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return []
        buf += chunk
        if b"\r\n" in buf:
            break

    line = buf.split(b"\r\n")[0].decode("utf-8", errors="replace").strip()
    if not line:
        return []

    if not line.startswith("*"):
        return line.split()

    parts = buf.decode("utf-8", errors="replace").split("\r\n")
    words = [p[1:] for p in parts if p and not p[0].isdigit() and p[0] not in ("*", "$", "-", "+", ":")]
    return [w for w in words if w]


def _err(msg: str) -> bytes:
    return f"-ERR {msg}\r\n".encode()


def _ok(msg: str = "OK") -> bytes:
    return f"+{msg}\r\n".encode()


def _bulk(data: str) -> bytes:
    enc = data.encode()
    return f"${len(enc)}\r\n".encode() + enc + b"\r\n"


def _int(n: int) -> bytes:
    return f":{n}\r\n".encode()


def handle_redis(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            while True:
                parts = _recv_command(conn)
                if not parts:
                    break
                cmd = parts[0].upper()

                if cmd == "PING":
                    arg = parts[1] if len(parts) > 1 else None
                    conn.sendall(_ok(arg if arg else "PONG"))

                elif cmd == "AUTH":
                    # May be: AUTH password  OR  AUTH username password
                    if len(parts) >= 3:
                        username, password = parts[1], parts[2]
                    else:
                        username, password = "", parts[1] if len(parts) > 1 else ""
                    log_credential("Redis", ip_str, username=username, token=password)
                    conn.sendall(_ok())

                elif cmd == "INFO":
                    conn.sendall(_bulk(REDIS_INFO.get()))

                elif cmd == "CLIENT":
                    sub = parts[1].upper() if len(parts) > 1 else ""
                    if sub == "SETNAME":
                        conn.sendall(_ok())
                    elif sub == "GETNAME":
                        conn.sendall(b"$0\r\n\r\n")
                    elif sub == "INFO":
                        conn.sendall(_bulk("id=1 addr=127.0.0.1:6379 cmd=client"))
                    else:
                        conn.sendall(_ok())

                elif cmd == "COMMAND":
                    conn.sendall(_ok())

                elif cmd == "CONFIG":
                    sub = parts[1].upper() if len(parts) > 1 else ""
                    if sub == "GET":
                        # Return empty array
                        conn.sendall(b"*0\r\n")
                    else:
                        conn.sendall(_err("ERR Unknown subcommand"))

                elif cmd == "DBSIZE":
                    conn.sendall(_int(0))

                elif cmd == "KEYS":
                    conn.sendall(b"*0\r\n")

                elif cmd == "GET":
                    conn.sendall(b"$-1\r\n")  # nil

                elif cmd == "SET" or cmd == "SELECT":
                    conn.sendall(_ok())

                elif cmd == "QUIT":
                    conn.sendall(_ok())
                    break

                else:
                    conn.sendall(_err(f"unknown command '{cmd}'"))

        except OSError:
            pass
