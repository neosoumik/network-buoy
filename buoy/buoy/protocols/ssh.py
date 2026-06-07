import socket
import struct

from ..identity import SSH_COOKIE
from ..logger import log_credential
from ..prompts import SSH_MOTD

_SERVER_BANNER = b"SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.5\r\n"

_KEXINIT_ALGOS = (
    b"\x00\x00\x00\x9dcurve25519-sha256,curve25519-sha256@libssh.org,"
    b"ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,"
    b"diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,"
    b"diffie-hellman-group18-sha512,diffie-hellman-group14-sha256"
    b"\x00\x00\x00\x2frsa-sha2-512,rsa-sha2-256,ecdsa-sha2-nistp256,ssh-ed25519"
    b"\x00\x00\x00\x6cchacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,"
    b"aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com"
    b"\x00\x00\x00\x6cchacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,"
    b"aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com"
    b"\x00\x00\x00\x1aumac-64-etm@openssh.com,umac-128-etm@openssh.com"
    b"\x00\x00\x00\x1aumac-64-etm@openssh.com,umac-128-etm@openssh.com"
    b"\x00\x00\x00\x1anone,zlib@openssh.com,zlib"
    b"\x00\x00\x00\x1anone,zlib@openssh.com,zlib"
    b"\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00"
)
_KEXINIT = b"\x14" + SSH_COOKIE + _KEXINIT_ALGOS

_MSG_KEXINIT = 20
_MSG_SERVICE_REQUEST = 5
_MSG_SERVICE_ACCEPT = 6
_MSG_USERAUTH_REQUEST = 50
_MSG_USERAUTH_FAILURE = 51
_MSG_USERAUTH_SUCCESS = 52


def _read_packet(conn: socket.socket) -> bytes:
    header = b""
    while len(header) < 4:
        chunk = conn.recv(4 - len(header))
        if not chunk:
            return b""
        header += chunk
    pkt_len = struct.unpack(">I", header)[0]
    payload = b""
    remaining = pkt_len
    while remaining > 0:
        chunk = conn.recv(min(remaining, 4096))
        if not chunk:
            break
        payload += chunk
        remaining -= len(chunk)
    return payload[1:] if len(payload) > 1 else b""


def _make_packet(payload: bytes) -> bytes:
    padding = 6
    pkt_len = 1 + len(payload) + padding
    return struct.pack(">IB", pkt_len, padding) + payload + b"\x00" * padding


def _service_accept(service: str) -> bytes:
    name = service.encode()
    body = bytes([_MSG_SERVICE_ACCEPT]) + struct.pack(">I", len(name)) + name
    return _make_packet(body)


def _userauth_failure() -> bytes:
    methods = b"publickey,password"
    body = bytes([_MSG_USERAUTH_FAILURE]) + struct.pack(">I", len(methods)) + methods + b"\x00"
    return _make_packet(body)


def _userauth_success() -> bytes:
    return _make_packet(bytes([_MSG_USERAUTH_SUCCESS]))


def _extract_userauth(payload: bytes) -> tuple[str, str, str]:
    try:
        offset = 1
        ulen = struct.unpack(">I", payload[offset : offset + 4])[0]
        offset += 4
        username = payload[offset : offset + ulen].decode("utf-8", errors="replace")
        offset += ulen
        slen = struct.unpack(">I", payload[offset : offset + 4])[0]
        offset += 4
        offset += slen
        mlen = struct.unpack(">I", payload[offset : offset + 4])[0]
        offset += 4
        method = payload[offset : offset + mlen].decode("utf-8", errors="replace")
        offset += mlen
        password = ""
        if method == "password" and offset < len(payload):
            offset += 1
            plen = struct.unpack(">I", payload[offset : offset + 4])[0]
            offset += 4
            password = payload[offset : offset + plen].decode("utf-8", errors="replace")
        return username, method, password
    except Exception:
        return "", "", ""


def handle_ssh(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            conn.sendall(_SERVER_BANNER)
            conn.recv(256)

            conn.sendall(_make_packet(_KEXINIT))
            conn.recv(4096)

            attempts = 0
            for _ in range(20):
                payload = _read_packet(conn)
                if not payload:
                    break

                msg_type = payload[0] if payload else 0

                if msg_type == _MSG_SERVICE_REQUEST:
                    slen = struct.unpack(">I", payload[1:5])[0]
                    service = payload[5 : 5 + slen].decode("utf-8", errors="replace")
                    conn.sendall(_service_accept(service))

                elif msg_type == _MSG_USERAUTH_REQUEST:
                    username, method, password = _extract_userauth(payload)
                    log_credential(
                        "SSH",
                        ip_str,
                        username=username,
                        password=password,
                        extra={"method": method},
                    )
                    attempts += 1
                    if attempts < 2:
                        conn.sendall(_userauth_failure())
                    else:
                        conn.sendall(_userauth_success())
                        motd = SSH_MOTD.get()
                        if motd:
                            msg = motd.encode("utf-8", errors="replace")
                            payload = bytes([_MSG_SERVICE_ACCEPT]) + struct.pack(">I", len(msg)) + msg
                            conn.sendall(_make_packet(payload))
                        break

        except OSError:
            pass
