import socket
import struct as _struct

# Best-effort binary greetings for protocols that require TLS or
# complex binary framing. Realistic enough to fingerprint correctly
# with nmap/masscan; we log the probe and close.

# TLS 1.2 ServerHello record (content_type=22, version=0x0303)
# followed by a minimal handshake — enough for scanners that do a
# partial TLS parse without completing the handshake.
_HTTPS_GREETING = (
    b"\x16\x03\x03"  # TLS handshake record, TLS 1.2
    b"\x00\x31"  # record length = 49
    b"\x02"  # HandshakeType: ServerHello
    b"\x00\x00\x2d"  # handshake length = 45
    b"\x03\x03"  # server version: TLS 1.2
    # 32-byte random
    b"\x52\x6e\x58\x61\x4e\x64\x4f\x6c"
    b"\x50\x71\x77\x62\x43\x4b\x73\x6e"
    b"\x52\x6e\x58\x61\x4e\x64\x4f\x6c"
    b"\x50\x71\x77\x62\x43\x4b\x73\x6e"
    b"\x00"  # session_id length = 0
    b"\xc0\x2b"  # cipher suite: TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
    b"\x00"  # compression method: null
    b"\x00\x05"  # extensions length = 5
    b"\xff\x01\x00\x01\x00"  # renegotiation_info extension (empty)
)

# RDP Connection Confirm PDU (X.224 TPDU CC)
# Scanners expect this in response to a Connection Request PDU.
_RDP_GREETING = (
    b"\x03\x00"  # TPKT header version=3, reserved=0
    b"\x00\x0b"  # total length = 11
    b"\x06"  # TPDU length indicator = 6
    b"\xd0"  # TPDU code: CC (Connection Confirm) = 0xD0
    b"\x00\x00"  # dst-ref = 0
    b"\x00\x00"  # src-ref = 0
    b"\x00"  # class = 0
)

# LDAP BindResponse (application 1) — success with empty fields.
# Encoded as BER: SEQUENCE { app[1] { enum(0), "", "" } }
_LDAP_GREETING = (
    b"\x30\x0c"  # SEQUENCE, length 12
    b"\x02\x01\x01"  # INTEGER messageID = 1
    b"\x61\x07"  # APPLICATION[1] BindResponse, length 7
    b"\x0a\x01\x00"  # ENUMERATED resultCode = success (0)
    b"\x04\x00"  # OCTET STRING matchedDN = ""
    b"\x04\x00"  # OCTET STRING diagnosticMessage = ""
)

# MongoDB Wire Protocol OP_REPLY (opcode 1) with isMaster-style response.
# Enough for pymongo / mongosh connection probes to see a valid server.


def _build_mongodb_greeting() -> bytes:
    # Minimal BSON document: { ok: 1.0 }
    bson_double = b"\x01ok\x00" + _struct.pack("<d", 1.0)
    bson_doc = _struct.pack("<i", 4 + 1 + len(bson_double) + 1) + b"\x01" + bson_double + b"\x00"

    # OP_REPLY header (§ MongoDB Wire Protocol)
    msg_length = 16 + 20 + len(bson_doc)  # header + reply fields + doc
    request_id = 1
    response_to = 1
    op_code = 1  # OP_REPLY
    response_flags = 8  # AwaitCapable
    cursor_id = 0
    starting_from = 0
    num_returned = 1

    header = _struct.pack(
        "<iiii",
        msg_length,
        request_id,
        response_to,
        op_code,
    )
    reply_fields = _struct.pack(
        "<iqii",
        response_flags,
        cursor_id,
        starting_from,
        num_returned,
    )
    return header + reply_fields + bson_doc


_MONGODB_GREETING = _build_mongodb_greeting()


def _greet(conn: socket.socket, data: bytes) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            conn.recv(4096)
            conn.sendall(data)
        except OSError:
            pass


def handle_https(conn: socket.socket) -> None:
    _greet(conn, _HTTPS_GREETING)


def handle_rdp(conn: socket.socket) -> None:
    _greet(conn, _RDP_GREETING)


def handle_ldap(conn: socket.socket) -> None:
    _greet(conn, _LDAP_GREETING)


def handle_mongodb(conn: socket.socket) -> None:
    _greet(conn, _MONGODB_GREETING)
