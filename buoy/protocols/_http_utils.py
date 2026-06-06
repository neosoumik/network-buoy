"""Shared HTTP parsing utilities for honeypot protocol handlers."""

import base64
import socket
from urllib.parse import parse_qs


def recv_request(conn: socket.socket, max_body: int = 8192) -> tuple[str, dict[str, str], bytes]:
    """Read a full HTTP request. Returns (first_line, headers, body)."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(4096)
        if not chunk:
            break
        buf += chunk

    if b"\r\n\r\n" not in buf:
        head_raw, body = buf, b""
    else:
        head_raw, body = buf.split(b"\r\n\r\n", 1)

    lines = head_raw.decode("utf-8", errors="replace").split("\r\n")
    first_line = lines[0] if lines else ""
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()

    content_length = int(headers.get("content-length", "0") or "0")
    while len(body) < min(content_length, max_body):
        chunk = conn.recv(min(content_length - len(body), 4096))
        if not chunk:
            break
        body += chunk

    return first_line, headers, body


def parse_authorization(headers: dict[str, str]) -> tuple[str, str, str]:
    """
    Parse Authorization header.
    Returns (scheme, username, secret) where secret is password for Basic,
    token string for Bearer/Token.
    """
    auth = headers.get("authorization", "")
    if not auth:
        return "", "", ""

    scheme, _, value = auth.partition(" ")
    scheme = scheme.lower()

    if scheme == "basic":
        try:
            decoded = base64.b64decode(value + "==").decode("utf-8", errors="replace")
            user, _, passwd = decoded.partition(":")
            return "basic", user, passwd
        except Exception:
            return "basic", "", value

    if scheme in ("bearer", "token"):
        return scheme, "", value.strip()

    return scheme, "", value.strip()


def parse_form_body(body: bytes) -> dict[str, str]:
    """Parse application/x-www-form-urlencoded body into a dict."""
    try:
        parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True)
        return {k: v[0] for k, v in parsed.items()}
    except Exception:
        return {}
