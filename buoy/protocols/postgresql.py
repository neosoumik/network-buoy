import socket
import struct

from ..logger import log_credential


def _extract_pg_params(data: bytes) -> dict[str, str]:
    """Parse key=value pairs from a PostgreSQL StartupMessage."""
    params: dict[str, str] = {}
    try:
        # StartupMessage: int32 length + int32 protocol + null-term key\0value\0 pairs + \0
        offset = 8  # skip length + protocol version
        while offset < len(data) - 1:
            null = data.index(b"\x00", offset)
            key = data[offset:null].decode("utf-8", errors="replace")
            offset = null + 1
            null = data.index(b"\x00", offset)
            val = data[offset:null].decode("utf-8", errors="replace")
            offset = null + 1
            if key:
                params[key] = val
    except ValueError, UnicodeDecodeError:
        pass
    return params


def _auth_ok() -> bytes:
    # AuthenticationOk: 'R' + int32(8) + int32(0)
    return b"R" + struct.pack("!II", 8, 0)


def _ready_for_query() -> bytes:
    # ReadyForQuery: 'Z' + int32(5) + 'I' (idle)
    return b"Z" + struct.pack("!I", 5) + b"I"


def _error_response(msg: str) -> bytes:
    fields = (
        b"S"
        + b"ERROR\x00"
        + b"V"
        + b"ERROR\x00"
        + b"C"
        + b"42P01\x00"  # undefined_table
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

            # Handle SSLRequest: decline, client retries with plain StartupMessage
            if len(data) >= 8 and struct.unpack("!II", data[:8]) == (8, 80877103):
                conn.sendall(b"N")
                data = conn.recv(4096)
                if not data:
                    return

            params = _extract_pg_params(data)
            username = params.get("user", "")
            database = params.get("database", "")
            log_credential("PostgreSQL", ip_str, username=username, extra={"database": database})

            # Send AuthenticationCleartextPassword to get the actual password
            conn.sendall(b"R" + struct.pack("!II", 8, 3))  # AuthCleartextPassword

            # Read password message: 'p' + int32 length + password + \0
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

            # Accept authentication
            conn.sendall(_auth_ok())
            conn.sendall(_ready_for_query())

            # Read one query then drop with a plausible error
            conn.recv(4096)
            conn.sendall(_error_response('relation "users" does not exist'))
            conn.sendall(_ready_for_query())

        except OSError:
            pass
