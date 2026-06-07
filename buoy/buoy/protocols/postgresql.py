import socket
import struct

from ..logger import log_credential


def _extract_pg_params(data: bytes) -> dict[str, str]:
    params: dict[str, str] = {}
    try:
        offset = 8
        while offset < len(data) - 1:
            null = data.index(b"\x00", offset)
            key = data[offset:null].decode("utf-8", errors="replace")
            offset = null + 1
            null = data.index(b"\x00", offset)
            val = data[offset:null].decode("utf-8", errors="replace")
            offset = null + 1
            if key:
                params[key] = val
    except (ValueError, UnicodeDecodeError):
        pass
    return params


def _auth_ok() -> bytes:
    return b"R" + struct.pack("!II", 8, 0)


def _ready_for_query() -> bytes:
    return b"Z" + struct.pack("!I", 5) + b"I"


def _error_response(msg: str) -> bytes:
    fields = (
        b"S"
        + b"ERROR\x00"
        + b"V"
        + b"ERROR\x00"
        + b"C"
        + b"42P01\x00"
        + b"M"
        + msg.encode()
        + b"\x00"
        + b"\x00"
    )
    return b"E" + struct.pack("!I", 4 + len(fields)) + fields


def handle_postgresql(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            data = conn.recv(4096)
            if not data:
                return

            if len(data) >= 8 and struct.unpack("!II", data[:8]) == (8, 80877103):
                conn.sendall(b"N")
                data = conn.recv(4096)
                if not data:
                    return

            params = _extract_pg_params(data)
            username = params.get("user", "")
            database = params.get("database", "")
            log_credential("PostgreSQL", ip_str, username=username, extra={"database": database})

            conn.sendall(b"R" + struct.pack("!II", 8, 3))
            pwd_data = conn.recv(4096)
            password = ""
            if pwd_data and pwd_data[0:1] == b"p":
                try:
                    password = pwd_data[5:].rstrip(b"\x00").decode("utf-8", errors="replace")
                    log_credential(
                        "PostgreSQL",
                        ip_str,
                        username=username,
                        password=password,
                        extra={"database": database},
                    )
                except Exception:
                    pass

            conn.sendall(_auth_ok())
            conn.sendall(_ready_for_query())
            conn.recv(4096)
            conn.sendall(_error_response('relation "users" does not exist'))
            conn.sendall(_ready_for_query())

        except OSError:
            pass
