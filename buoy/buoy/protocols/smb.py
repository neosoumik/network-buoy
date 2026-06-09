import socket

# SMB2 Negotiate Response — enough for scanners (nmap, masscan, CrackMapExec)
# to fingerprint a real Windows Server SMB endpoint.
#
# Layout: NetBIOS session header (4) + SMB2 header (64) + Negotiate body.

_SMB2_HEADER = (
    b"\xfeSMB"  # ProtocolId
    b"\x40\x00"  # StructureSize = 64
    b"\x00\x00"  # CreditCharge
    b"\x00\x00\x00\x00"  # Status = SUCCESS
    b"\x00\x00"  # Command = NEGOTIATE (0)
    b"\x01\x00"  # CreditResponse
    b"\x00\x00\x00\x00"  # Flags
    b"\x00\x00\x00\x00"  # NextCommand
    + b"\x00" * 8  # MessageId
    + b"\x00\x00\x00\x00"  # Reserved
    + b"\x00\x00\x00\x00"  # TreeId
    + b"\x00" * 8  # SessionId
    + b"\x00" * 16  # Signature
)

_NEGOTIATE_BODY = (
    b"\x41\x00"  # StructureSize = 65
    b"\x01\x00"  # SecurityMode: signing enabled
    b"\x11\x03"  # DialectRevision: SMB 3.1.1
    b"\x00\x00"  # NegotiateContextCount
    b"\x6f\x2a\x4e\x71\x4b\x52\x41\x4e\x78\x63\x4d\x70\x56\x74\x44\x63"  # ServerGuid
    b"\x7f\x00\x00\x00"  # Capabilities
    b"\x00\x00\x10\x00"  # MaxTransactSize
    b"\x00\x00\x10\x00"  # MaxReadSize
    b"\x00\x00\x10\x00"  # MaxWriteSize
    + b"\x00" * 8  # SystemTime
    + b"\x00" * 8  # ServerStartTime
    + b"\x80\x00"  # SecurityBufferOffset
    b"\x00\x00"  # SecurityBufferLength
    b"\x00\x00\x00\x00"  # NegotiateContextOffset
)


def _build_smb2_negotiate() -> bytes:
    body = _SMB2_HEADER + _NEGOTIATE_BODY
    nb_header = b"\x00" + len(body).to_bytes(3, "big")
    return nb_header + body


_RESPONSE = _build_smb2_negotiate()


def handle_smb(conn: socket.socket) -> None:
    conn.settimeout(10.0)
    with conn:
        try:
            conn.recv(4096)
            conn.sendall(_RESPONSE)
        except OSError:
            pass
