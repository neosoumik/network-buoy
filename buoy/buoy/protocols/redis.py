import socket

from ..logger import log_credential
from ..prompts import REDIS_INFO


def _parse_command(buf: bytearray) -> tuple[list[str], int]:
    """Parse one RESP command from buf. Returns (args, bytes_consumed).
    Returns ([], 0) if buf doesn't yet contain a complete command."""
    s = bytes(buf)
    if not s:
        return [], 0

    if s[0:1] == b"*":
        # RESP multi-bulk
        crlf = s.find(b"\r\n")
        if crlf < 0:
            return [], 0
        try:
            argc = int(s[1:crlf])
        except ValueError:
            return [], len(s)  # discard malformed
        pos = crlf + 2
        args = []
        for _ in range(argc):
            if pos >= len(s) or s[pos : pos + 1] != b"$":
                return [], 0  # incomplete
            crlf2 = s.find(b"\r\n", pos)
            if crlf2 < 0:
                return [], 0
            try:
                arglen = int(s[pos + 1 : crlf2])
            except ValueError:
                return [], len(s)
            start = crlf2 + 2
            end = start + arglen
            if end + 2 > len(s):
                return [], 0  # incomplete
            args.append(s[start:end].decode("utf-8", errors="replace"))
            pos = end + 2  # skip trailing \r\n
        return args, pos
    else:
        # inline command
        crlf = s.find(b"\r\n")
        if crlf < 0:
            return [], 0
        line = s[:crlf].decode("utf-8", errors="replace").strip()
        return line.split() if line else [], crlf + 2


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
            buf = bytearray()

            while True:
                # try to parse a command from what we already have
                parts, consumed = _parse_command(buf)
                if not parts and consumed == 0:
                    # need more data
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf.extend(chunk)
                    continue

                del buf[:consumed]

                if not parts:
                    continue

                cmd = parts[0].upper()

                if cmd == "PING":
                    arg = parts[1] if len(parts) > 1 else None
                    conn.sendall(_ok(arg if arg else "PONG"))

                elif cmd == "AUTH":
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
                        conn.sendall(b"*0\r\n")
                    else:
                        conn.sendall(_err("ERR Unknown subcommand"))

                elif cmd == "DBSIZE":
                    conn.sendall(_int(0))

                elif cmd == "KEYS":
                    conn.sendall(b"*0\r\n")

                elif cmd == "GET":
                    conn.sendall(b"$-1\r\n")

                elif cmd == "SET" or cmd == "SELECT":
                    conn.sendall(_ok())

                elif cmd == "QUIT":
                    conn.sendall(_ok())
                    break

                else:
                    conn.sendall(_err(f"unknown command '{cmd}'"))

        except OSError:
            pass
