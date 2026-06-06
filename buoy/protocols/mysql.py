import socket
import struct

from ..identity import MYSQL_AUTH_NONCE_1, MYSQL_AUTH_NONCE_2, MYSQL_CONNECTION_ID
from ..logger import log_credential

_VERSION = b"8.0.36\x00"
_AUTH_PLUGIN = b"mysql_native_password\x00"


def _build_handshake() -> bytes:
    auth_data_1 = MYSQL_AUTH_NONCE_1 + b"\x00"
    auth_data_2 = MYSQL_AUTH_NONCE_2 + b"\x00"
    payload = (
        b"\x0a"
        + _VERSION
        + struct.pack("<I", MYSQL_CONNECTION_ID)
        + auth_data_1
        + struct.pack("<H", 0xFFFF)  # capabilities_lo
        + struct.pack("B", 0x21)  # charset utf8
        + struct.pack("<H", 0x0002)  # status: autocommit
        + struct.pack("<H", 0xC1FF)  # capabilities_hi
        + struct.pack("B", 21)  # auth_plugin_data_len
        + b"\x00" * 10  # reserved
        + auth_data_2
        + _AUTH_PLUGIN
    )
    header = struct.pack("<I", len(payload))[:3] + b"\x00"
    return header + payload


def _ok_packet() -> bytes:
    # OK packet: seq=2, payload = 0x00 affected=0 insert_id=0 status=0x0002 warnings=0
    payload = b"\x00\x00\x00\x02\x00\x00\x00"
    header = struct.pack("<I", len(payload))[:3] + b"\x02"
    return header + payload


def _err_packet(code: int, msg: str) -> bytes:
    payload = b"\xff" + struct.pack("<H", code) + b"#HY000" + msg.encode()
    header = struct.pack("<I", len(payload))[:3] + b"\x03"
    return header + payload


def _extract_username(data: bytes) -> str:
    """Pull the username string from a MySQL client HandshakeResponse41."""
    try:
        # Skip 4-byte header + 4 caps + 4 max_pkt + 1 charset + 23 filler = 36 bytes
        offset = 4 + 4 + 4 + 1 + 23
        if len(data) <= offset:
            return ""
        null = data.index(b"\x00", offset)
        return data[offset:null].decode("utf-8", errors="replace")
    except ValueError, UnicodeDecodeError:
        return ""


def handle_mysql(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            conn.sendall(_build_handshake())

            data = conn.recv(4096)
            if not data:
                return

            username = _extract_username(data)
            log_credential("MySQL", ip_str, username=username)

            # Send OK — client thinks they're authenticated
            conn.sendall(_ok_packet())

            # Wait for a query, then return "table doesn't exist" and disconnect
            conn.recv(4096)
            conn.sendall(_err_packet(1049, "Unknown database 'prod'"))

        except OSError:
            pass
