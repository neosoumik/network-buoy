"""
network-buoy protocol test suite — pure pytest.
Requires the buoy to be running (docker compose up or uv run main.py).

Run:
    uv run pytest test/test_protocols.py -v
    uv run pytest test/test_protocols.py -v --host 1.2.3.4
    uv run pytest test/test_protocols.py -v -k performance
    uv run pytest test/test_protocols.py -v -k "not nmap" --timeout 3
"""

import base64
import json
import shutil
import socket
import struct
import subprocess
import time

import pytest

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tcp_connect(host: str, port: int, timeout: float = 5.0) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((host, port))
    return s


def recv_until(s: socket.socket, sentinel: bytes, max_bytes: int = 8192) -> bytes:
    buf = b""
    while sentinel not in buf and len(buf) < max_bytes:
        chunk = s.recv(256)
        if not chunk:
            break
        buf += chunk
    return buf


def recv_line(s: socket.socket) -> bytes:
    return recv_until(s, b"\n")


def send_line(s: socket.socket, line: str) -> None:
    s.sendall((line + "\r\n").encode())


def http_get(
    host: str, port: int, path: str = "/", headers: dict | None = None, timeout: float = 5.0
) -> tuple[int, dict, bytes]:
    hdrs = {"Host": host, "Connection": "close"}
    if headers:
        hdrs.update(headers)
    raw_hdrs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
    request = f"GET {path} HTTP/1.1\r\n{raw_hdrs}\r\n"
    s = tcp_connect(host, port, timeout)
    s.sendall(request.encode())
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    header_part, _, body = buf.partition(b"\r\n\r\n")
    lines = header_part.split(b"\r\n")
    status = int(lines[0].split()[1])
    resp_hdrs = {}
    for line in lines[1:]:
        if b": " in line:
            k, _, v = line.partition(b": ")
            resp_hdrs[k.decode().lower()] = v.decode()
    return status, resp_hdrs, body


def http_post(
    host: str,
    port: int,
    path: str,
    body: str,
    content_type: str = "application/x-www-form-urlencoded",
    headers: dict | None = None,
    timeout: float = 5.0,
) -> tuple[int, dict, bytes]:
    hdrs = {
        "Host": host,
        "Connection": "close",
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
    }
    if headers:
        hdrs.update(headers)
    raw_hdrs = "".join(f"{k}: {v}\r\n" for k, v in hdrs.items())
    request = f"POST {path} HTTP/1.1\r\n{raw_hdrs}\r\n{body}"
    s = tcp_connect(host, port, timeout)
    s.sendall(request.encode())
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    header_part, _, resp_body = buf.partition(b"\r\n\r\n")
    lines = header_part.split(b"\r\n")
    status = int(lines[0].split()[1])
    resp_hdrs = {}
    for line in lines[1:]:
        if b": " in line:
            k, _, v = line.partition(b": ")
            resp_hdrs[k.decode().lower()] = v.decode()
    return status, resp_hdrs, resp_body


# ---------------------------------------------------------------------------
# Pre-flight: all ports reachable
# ---------------------------------------------------------------------------

ALL_PORTS = [
    21,
    22,
    23,
    25,
    80,
    110,
    143,
    389,
    443,
    445,
    3306,
    3389,
    5432,
    6379,
    6443,
    8080,
    9090,
    9200,
    27017,
]


class TestPreflight:
    @pytest.mark.parametrize("port", ALL_PORTS)
    def test_port_open(self, host, timeout, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        assert result == 0, f"Port {port} not reachable on {host}"


# ---------------------------------------------------------------------------
# nmap fingerprinting (skipped if nmap not installed)
# ---------------------------------------------------------------------------


class TestNmap:
    @pytest.fixture(autouse=True)
    def require_nmap(self):
        if not shutil.which("nmap"):
            pytest.skip("nmap not installed")

    @pytest.fixture(scope="class")
    def nmap_output(self, host):
        ports = ",".join(str(p) for p in ALL_PORTS)
        result = subprocess.run(
            ["nmap", "-sV", "-T4", "--open", f"-p{ports}", host],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.stdout

    @pytest.mark.parametrize(
        "port,pattern",
        [
            (22, "OpenSSH"),
            (25, "smtp|postfix"),
            (80, "nginx"),
            (3306, "mysql|MySQL"),
            (3389, "rdp|xrdp|ms-wbt"),
            (8080, "jetty|http|jenkins"),
            (9200, "http|rtsp|elastic|tcpwrapped"),
        ],
    )
    def test_service_fingerprint(self, nmap_output, port, pattern):
        import re

        line = next((ln for ln in nmap_output.splitlines() if f"{port}/tcp" in ln), "")
        assert line, f"Port {port} not in nmap output"
        assert re.search(pattern, line, re.IGNORECASE), f"Port {port}: expected '{pattern}' in: {line}"


# ---------------------------------------------------------------------------
# SSH
# ---------------------------------------------------------------------------


class TestSSH:
    PORT = 22

    def test_banner(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert "SSH-2.0" in banner

    def test_banner_openssh(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert "OpenSSH" in banner

    def test_kexinit_sent(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        recv_line(s)  # consume banner
        s.sendall(b"SSH-2.0-OpenSSH_8.9\r\n")
        data = s.recv(4096)
        s.close()
        # KEXINIT packet type = 20 (0x14)
        # payload starts at byte 5 (4-byte length + 1 byte padding)
        assert len(data) > 5
        msg_type = data[5]
        assert msg_type == 20, f"Expected KEXINIT (20), got {msg_type}"

    def test_concurrent_connections(self, host, timeout):
        import threading

        results = []

        def grab():
            try:
                s = tcp_connect(host, self.PORT, timeout)
                b = recv_line(s)
                s.close()
                results.append(b"SSH-2.0" in b)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=grab) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) >= 15, f"Only {sum(results)}/20 SSH connections got banner"


# ---------------------------------------------------------------------------
# FTP
# ---------------------------------------------------------------------------


class TestFTP:
    PORT = 21

    def _session(self, host, timeout, *commands):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")  # consume banner
        responses = []
        for cmd in commands:
            send_line(s, cmd)
            time.sleep(0.1)
            data = s.recv(4096).decode("utf-8", errors="replace")
            responses.append(data)
        s.close()
        return responses

    def test_banner_220(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert banner.startswith("220")

    def test_user_pass_credential_capture(self, host, timeout):
        resps = self._session(host, timeout, "USER hackerman", "PASS p@ssw0rd123")
        assert "331" in resps[0]
        assert "230" in resps[1]

    def test_anonymous_login(self, host, timeout):
        resps = self._session(host, timeout, "USER anonymous", "PASS anon@anon.org")
        assert "331" in resps[0]
        assert "230" in resps[1]

    def test_syst(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "SYST")
        assert "215" in resps[2]
        assert "UNIX" in resps[2].upper()

    def test_feat(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "FEAT")
        assert "211" in resps[2]

    def test_pwd(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "PWD")
        assert "257" in resps[2]

    def test_list(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "LIST")
        assert "150" in resps[2]

    def test_stor_denied(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "STOR malware.exe")
        assert "550" in resps[2]

    def test_dele_denied(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "DELE important.txt")
        assert "550" in resps[2]

    def test_retr_denied(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "RETR /etc/passwd")
        assert "550" in resps[2]

    def test_quit(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "QUIT")
        assert "221" in resps[2]

    def test_unknown_command(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "BLAH")
        assert "500" in resps[2]

    def test_pasv(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "PASV")
        assert "227" in resps[2]


# ---------------------------------------------------------------------------
# Telnet
# ---------------------------------------------------------------------------


class TestTelnet:
    PORT = 23

    def test_iac_negotiation(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(b"\xff\xfd\x18\xff\xfd\x1f")  # DO TERMINAL-TYPE, DO NAWS
        data = s.recv(4096)
        s.close()
        assert len(data) > 0

    def test_login_prompt(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        data = b""
        for _ in range(5):
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk
            if b"login" in data.lower() or b":" in data:
                break
            time.sleep(0.3)
        s.close()
        assert len(data) > 0

    def test_fake_shell_commands(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout * 4)
        s.settimeout(timeout * 4)
        # drain banner + negotiation
        time.sleep(0.5)
        s.recv(4096)
        # first login attempt (fails)
        s.sendall(b"admin\r")
        time.sleep(0.2)
        s.recv(1024)
        s.sendall(b"badpass\r")
        time.sleep(0.3)
        s.recv(1024)
        # second attempt (succeeds)
        s.sendall(b"admin\r")
        time.sleep(0.2)
        s.recv(1024)
        s.sendall(b"correctpass\r")
        time.sleep(0.5)
        s.recv(4096)
        # send shell commands
        s.sendall(b"whoami\r")
        time.sleep(0.3)
        out = s.recv(1024)
        s.sendall(b"id\r")
        time.sleep(0.3)
        out += s.recv(1024)
        s.sendall(b"exit\r")
        s.close()
        assert b"root" in out or b"uid" in out

    def test_uname(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout * 4)
        s.settimeout(timeout * 4)
        time.sleep(0.5)
        s.recv(4096)
        for cred in [b"admin\r", b"pw\r", b"admin\r", b"pw\r"]:
            s.sendall(cred)
            time.sleep(0.3)
            s.recv(1024)
        time.sleep(0.3)
        s.sendall(b"uname\r")
        time.sleep(0.3)
        out = s.recv(1024)
        s.sendall(b"exit\r")
        s.close()
        assert b"Linux" in out or b"linux" in out.lower()


# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------


class TestSMTP:
    PORT = 25

    def _session(self, host, timeout, *commands):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")  # banner
        responses = []
        for cmd in commands:
            s.sendall((cmd + "\r\n").encode())
            time.sleep(0.1)
            data = s.recv(4096).decode("utf-8", errors="replace")
            responses.append(data)
        s.close()
        return responses

    def test_banner_220(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert banner.startswith("220")
        assert "ESMTP" in banner or "Postfix" in banner

    def test_ehlo(self, host, timeout):
        resps = self._session(host, timeout, "EHLO attacker.com")
        assert "250" in resps[0]
        assert "AUTH" in resps[0]

    def test_auth_plain(self, host, timeout):
        token = base64.b64encode(b"\x00admin\x00hunter2").decode()
        resps = self._session(host, timeout, "EHLO x", f"AUTH PLAIN {token}")
        assert "235" in resps[1]

    def test_auth_plain_two_step(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")
        send_line(s, "EHLO x")
        recv_until(s, b"DSN\r\n")
        send_line(s, "AUTH PLAIN")
        challenge = recv_line(s)
        assert b"334" in challenge
        token = base64.b64encode(b"\x00user2\x00pass2").decode()
        send_line(s, token)
        resp = recv_line(s)
        s.close()
        assert b"235" in resp

    def test_auth_login(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")
        send_line(s, "EHLO x")
        recv_until(s, b"DSN\r\n")
        send_line(s, "AUTH LOGIN")
        recv_line(s)  # 334 Username:
        send_line(s, base64.b64encode(b"loginuser").decode())
        recv_line(s)  # 334 Password:
        send_line(s, base64.b64encode(b"loginpass").decode())
        resp = recv_line(s)
        s.close()
        assert b"235" in resp

    def test_vrfy(self, host, timeout):
        resps = self._session(host, timeout, "EHLO x", "VRFY root")
        assert "252" in resps[1]

    def test_noop(self, host, timeout):
        resps = self._session(host, timeout, "EHLO x", "NOOP")
        assert "250" in resps[1]

    def test_rset(self, host, timeout):
        resps = self._session(host, timeout, "EHLO x", "RSET")
        assert "250" in resps[1]

    def test_data_flow(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")
        for cmd in ["EHLO x", "MAIL FROM:<a@b.com>", "RCPT TO:<c@d.com>"]:
            send_line(s, cmd)
            recv_until(s, b"\r\n")
        send_line(s, "DATA")
        resp = recv_until(s, b"\r\n")
        assert b"354" in resp
        # send body line by line so _recv_line gets one line per recv()
        for line in [b"Subject: test\r\n", b"\r\n", b"hello world\r\n", b".\r\n"]:
            s.sendall(line)
            time.sleep(0.05)
        time.sleep(0.3)
        resp = recv_until(s, b"\r\n")
        s.close()
        assert b"250" in resp

    def test_unknown_command(self, host, timeout):
        resps = self._session(host, timeout, "EHLO x", "BLAHBLAH")
        assert "502" in resps[1]

    def test_quit(self, host, timeout):
        resps = self._session(host, timeout, "EHLO x", "QUIT")
        assert "221" in resps[1]


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


class TestHTTP:
    PORT = 80

    def test_get_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 200

    def test_server_header_nginx(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "nginx" in hdrs.get("server", "").lower()

    def test_html_body(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        assert b"<html" in body.lower() or b"<!doctype" in body.lower()

    def test_basic_auth_captured(self, host, timeout):
        creds = base64.b64encode(b"admin:supersecret").decode()
        status, _, _ = http_get(host, self.PORT, headers={"Authorization": f"Basic {creds}"}, timeout=timeout)
        assert status == 200

    def test_bearer_token_captured(self, host, timeout):
        status, _, _ = http_get(
            host,
            self.PORT,
            headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.prod.sig"},
            timeout=timeout,
        )
        assert status == 200

    @pytest.mark.parametrize("path", ["/admin", "/login", "/api/v1", "/wp-admin", "/.env", "/phpmyadmin"])
    def test_paths_return_200(self, host, timeout, path):
        status, _, _ = http_get(host, self.PORT, path, timeout=timeout)
        assert status == 200

    def test_http10(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(b"GET / HTTP/1.0\r\nHost: localhost\r\n\r\n")
        data = s.recv(4096)
        s.close()
        assert b"200" in data

    def test_no_auth_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 200

    def test_concurrent_requests(self, host, timeout):
        import threading

        results = []

        def req():
            try:
                s, h, b = http_get(host, self.PORT, timeout=timeout)
                results.append(s == 200)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=req) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) >= 45, f"Only {sum(results)}/50 concurrent HTTP requests succeeded"


# ---------------------------------------------------------------------------
# POP3
# ---------------------------------------------------------------------------


class TestPOP3:
    PORT = 110

    def _session(self, host, timeout, *commands):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")  # banner
        responses = []
        for cmd in commands:
            send_line(s, cmd)
            time.sleep(0.1)
            data = s.recv(4096).decode("utf-8", errors="replace")
            responses.append(data)
        s.close()
        return responses

    def test_banner_ok(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert banner.startswith("+OK")

    def test_capa(self, host, timeout):
        resps = self._session(host, timeout, "CAPA")
        assert "+OK" in resps[0]
        assert "USER" in resps[0]

    def test_user_pass(self, host, timeout):
        resps = self._session(host, timeout, "USER alice", "PASS secret123")
        assert "+OK" in resps[0]
        assert "+OK" in resps[1] and "Logged" in resps[1]

    def test_apop(self, host, timeout):
        resps = self._session(host, timeout, "APOP bob <ts@h> md5digest")
        assert "+OK" in resps[0]

    def test_stat(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "STAT")
        assert "+OK 0 0" in resps[2]

    def test_list(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "LIST")
        assert "+OK" in resps[2]

    def test_uidl(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "UIDL")
        assert "+OK" in resps[2]

    def test_retr_no_message(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "RETR 1")
        assert "-ERR" in resps[2]

    def test_noop(self, host, timeout):
        resps = self._session(host, timeout, "USER a", "PASS b", "NOOP")
        assert "+OK" in resps[2]

    def test_quit(self, host, timeout):
        resps = self._session(host, timeout, "QUIT")
        assert "+OK" in resps[0]

    def test_unknown_command(self, host, timeout):
        resps = self._session(host, timeout, "BLAH")
        assert "-ERR" in resps[0]


# ---------------------------------------------------------------------------
# IMAP
# ---------------------------------------------------------------------------


class TestIMAP:
    PORT = 143

    def _session(self, host, timeout, *tagged_commands):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")  # banner
        responses = {}
        for tag_cmd in tagged_commands:
            s.sendall((tag_cmd + "\r\n").encode())
            time.sleep(0.1)
            data = s.recv(4096).decode("utf-8", errors="replace")
            tag = tag_cmd.split()[0]
            responses[tag] = data
        s.close()
        return responses

    def test_banner_ok(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        banner = recv_line(s).decode("utf-8", errors="replace")
        s.close()
        assert banner.startswith("* OK")

    def test_capability(self, host, timeout):
        resps = self._session(host, timeout, "a0 CAPABILITY", "a1 LOGOUT")
        assert "IMAP4rev1" in resps["a0"]
        assert "AUTH=PLAIN" in resps["a0"]
        assert "a0 OK" in resps["a0"]

    def test_login(self, host, timeout):
        resps = self._session(host, timeout, "a1 LOGIN alice hunter2", "a2 LOGOUT")
        assert "a1 OK" in resps["a1"]

    def test_login_quoted_creds(self, host, timeout):
        resps = self._session(host, timeout, 'b1 LOGIN "bob@corp.com" "p@$$w0rd!"', "b2 LOGOUT")
        assert "b1 OK" in resps["b1"]

    def test_authenticate_plain(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        recv_until(s, b"\r\n")
        send_line(s, "c1 AUTHENTICATE PLAIN")
        challenge = recv_line(s)
        assert b"+" in challenge
        token = base64.b64encode(b"\x00imap_user\x00imap_pass").decode()
        send_line(s, token)
        resp = recv_line(s)
        s.sendall(b"c2 LOGOUT\r\n")
        s.close()
        assert b"c1 OK" in resp

    def test_select_inbox_after_login(self, host, timeout):
        resps = self._session(host, timeout, "d1 LOGIN user pw", "d2 SELECT INBOX", "d3 LOGOUT")
        assert "d2 OK" in resps["d2"]
        assert "EXISTS" in resps["d2"]

    def test_select_without_auth_rejected(self, host, timeout):
        resps = self._session(host, timeout, "e1 SELECT INBOX", "e2 LOGOUT")
        assert "NO" in resps["e1"] or "BAD" in resps["e1"]

    def test_list(self, host, timeout):
        resps = self._session(host, timeout, "f1 LOGIN u p", 'f2 LIST "" "*"', "f3 LOGOUT")
        assert "f2 OK" in resps["f2"]

    def test_noop(self, host, timeout):
        resps = self._session(host, timeout, "g1 NOOP", "g2 LOGOUT")
        assert "g1 OK" in resps["g1"]

    def test_starttls(self, host, timeout):
        resps = self._session(host, timeout, "h1 STARTTLS")
        assert "h1 OK" in resps["h1"]

    def test_logout(self, host, timeout):
        resps = self._session(host, timeout, "z1 LOGOUT")
        assert "z1 OK" in resps["z1"]
        assert "BYE" in resps["z1"]

    def test_unknown_command(self, host, timeout):
        resps = self._session(host, timeout, "x1 BLAH foo", "x2 LOGOUT")
        assert "x1 BAD" in resps["x1"]


# ---------------------------------------------------------------------------
# LDAP
# ---------------------------------------------------------------------------


class TestLDAP:
    PORT = 389

    def test_responds_to_bind(self, host, timeout):
        # minimal anonymous BindRequest BER
        bind_req = bytes.fromhex("300c020101600702010304000080 00".replace(" ", ""))
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(bind_req)
        data = s.recv(256)
        s.close()
        assert len(data) > 0

    def test_returns_ber_sequence(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(bytes.fromhex("300c020101600702010304000080 00".replace(" ", "")))
        data = s.recv(256)
        s.close()
        assert data[0] == 0x30  # SEQUENCE tag


# ---------------------------------------------------------------------------
# HTTPS
# ---------------------------------------------------------------------------


class TestHTTPS:
    PORT = 443

    def test_tls_serverhello(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        # HTTPS handler reads first, so send something before recv
        s.sendall(b"\x16\x03\x01\x00\x00")
        data = s.recv(1024)
        s.close()
        assert len(data) > 0

    def test_tls_record_header(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        # Send a ClientHello-ish probe
        s.sendall(b"\x16\x03\x01\x00\x00")
        data = s.recv(256)
        s.close()
        if data:
            assert data[0] == 0x16  # TLS content type: handshake
            assert data[1] == 0x03  # TLS major version

    def test_raw_probe_gets_response(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(b"\x00" * 4)
        data = s.recv(256)
        s.close()
        assert len(data) > 0


# ---------------------------------------------------------------------------
# SMB
# ---------------------------------------------------------------------------


class TestSMB:
    PORT = 445

    SMB_NEGOTIATE = (
        b"\x00\x00\x00\x2f"  # NetBIOS length
        b"\xff\x53\x4d\x42"  # SMB1 header
        b"\x72"  # command: Negotiate
        b"\x00\x00\x00\x00"  # status
        b"\x18\x01\x28\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\xff\xfe\x00\x00\x00\x00"
        b"\x00\x00\x11\x02\x00\x00\x00\x00\x00\x00\x00\x00"
    )

    def test_responds_to_probe(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SMB_NEGOTIATE)
        data = s.recv(256)
        s.close()
        assert len(data) > 0

    def test_smb2_response_header(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SMB_NEGOTIATE)
        data = s.recv(256)
        s.close()
        # SMB2 ProtocolId: \xfeSMB at offset 4 (after NetBIOS 4-byte header)
        if len(data) >= 8:
            assert data[4:8] == b"\xfeSMB" or data[0:4] == b"\x00\x00\x00\x80"


# ---------------------------------------------------------------------------
# MySQL
# ---------------------------------------------------------------------------


class TestMySQL:
    PORT = 3306

    def test_handshake_banner(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        data = s.recv(256)
        s.close()
        assert b"8.0" in data

    def test_handshake_version_string(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        data = s.recv(256)
        s.close()
        # HandshakeV10: protocol version byte = 0x0a at offset 4
        assert data[4] == 0x0A

    def test_accepts_handshake_response(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.recv(256)  # consume handshake
        # Minimal HandshakeResponse41
        user = b"root\x00"
        reserved = b"\x00" * 23
        caps = struct.pack("<I", 0x01_86_A6_8D)
        max_pkt = struct.pack("<I", 1)
        charset = b"\x21"
        body = caps + max_pkt + charset + reserved + user + b"\x00"  # no auth data
        header = struct.pack("<I", len(body))[:3] + b"\x01"
        s.sendall(header + body)
        resp = s.recv(256)
        s.close()
        assert len(resp) > 0  # got an OK or error


# ---------------------------------------------------------------------------
# RDP
# ---------------------------------------------------------------------------


class TestRDP:
    PORT = 3389

    CR_PDU = (
        b"\x03\x00"  # TPKT version + reserved
        b"\x00\x13"  # total length = 19
        b"\x0e"  # TPDU length indicator
        b"\xe0"  # TPDU code: CR (Connection Request)
        b"\x00\x00"  # dst-ref
        b"\x00\x00"  # src-ref
        b"\x00"  # class
        b"\x01\x00\x08\x00\x03\x00\x00\x00"  # RDP negotiation request
    )

    def test_tpkt_response(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.CR_PDU)
        data = s.recv(256)
        s.close()
        assert len(data) > 0
        assert data[0] == 0x03  # TPKT

    def test_connection_confirm_pdu(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.CR_PDU)
        data = s.recv(256)
        s.close()
        # TPDU code at byte 5: 0xd0 = CC (Connection Confirm)
        assert len(data) >= 6
        assert data[5] == 0xD0


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------


class TestPostgreSQL:
    PORT = 5432

    SSL_REQUEST = struct.pack("!II", 8, 80877103)

    def _startup(self, user: str = "hacker", database: str = "prod") -> bytes:
        params = f"user\x00{user}\x00database\x00{database}\x00\x00".encode()
        length = 4 + 4 + len(params)
        return struct.pack("!II", length, 196608) + params  # 196608 = 0x0003_0000

    def test_ssl_request_denied(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SSL_REQUEST)
        resp = s.recv(1)
        s.close()
        assert resp == b"N"

    def test_startup_triggers_auth(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self._startup())
        data = s.recv(256)
        s.close()
        # R = AuthenticationRequest
        assert data[0:1] == b"R"
        # AuthenticationCleartextPassword = type 3
        auth_type = struct.unpack("!I", data[5:9])[0]
        assert auth_type == 3

    def test_ssl_then_startup(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SSL_REQUEST)
        s.recv(1)  # N
        s.sendall(self._startup("testuser", "testdb"))
        data = s.recv(256)
        s.close()
        assert data[0:1] == b"R"

    def test_password_accepted(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SSL_REQUEST)
        s.recv(1)
        s.sendall(self._startup())
        s.recv(256)  # auth req
        pw = b"hunter2\x00"
        s.sendall(b"p" + struct.pack("!I", 4 + len(pw)) + pw)
        time.sleep(0.3)
        data = s.recv(256)
        s.close()
        assert b"R" in data or b"Z" in data

    def test_ready_for_query(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.SSL_REQUEST)
        s.recv(1)
        s.sendall(self._startup())
        s.recv(256)
        pw = b"anypass\x00"
        s.sendall(b"p" + struct.pack("!I", 4 + len(pw)) + pw)
        time.sleep(0.3)  # auth_ok and ready_for_query may arrive in separate packets
        data = s.recv(512)
        s.close()
        assert b"Z" in data  # ReadyForQuery


# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------


class TestRedis:
    PORT = 6379

    def _cmd(self, host, timeout, *args) -> str:
        s = tcp_connect(host, self.PORT, timeout)
        parts = [f"*{len(args)}\r\n"]
        for a in args:
            parts.append(f"${len(a)}\r\n{a}\r\n")
        s.sendall("".join(parts).encode())
        data = s.recv(4096)
        s.close()
        return data.decode("utf-8", errors="replace")

    def test_ping(self, host, timeout):
        assert "+PONG" in self._cmd(host, timeout, "PING")

    def test_ping_with_message(self, host, timeout):
        assert "+hello" in self._cmd(host, timeout, "PING", "hello")

    def test_auth_password_only(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "AUTH", "secretpassword")

    def test_auth_user_password(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "AUTH", "admin", "password123")

    def test_info(self, host, timeout):
        out = self._cmd(host, timeout, "INFO", "server")
        assert "redis_version" in out

    def test_get_nil(self, host, timeout):
        assert "$-1" in self._cmd(host, timeout, "GET", "nonexistent_key")

    def test_set(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "SET", "k", "v")

    def test_dbsize(self, host, timeout):
        assert ":0" in self._cmd(host, timeout, "DBSIZE")

    def test_keys(self, host, timeout):
        assert "*0" in self._cmd(host, timeout, "KEYS", "*")

    def test_client_setname(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "CLIENT", "SETNAME", "myconn")

    def test_command(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "COMMAND")

    def test_select(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "SELECT", "0")

    def test_quit(self, host, timeout):
        assert "+OK" in self._cmd(host, timeout, "QUIT")

    def test_unknown_command(self, host, timeout):
        out = self._cmd(host, timeout, "BLAHBLAH")
        assert out.startswith("-ERR")

    def test_inline_ping(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(b"PING\r\n")
        data = s.recv(64)
        s.close()
        assert b"+PONG" in data

    def test_pipeline(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        pipeline = b"PING\r\nPING\r\nPING\r\nPING\r\nPING\r\n"
        s.sendall(pipeline)
        time.sleep(0.3)
        data = s.recv(4096)
        s.close()
        assert data.count(b"+PONG") >= 4

    def test_concurrent_connections(self, host, timeout):
        import threading

        results = []

        def ping():
            try:
                out = self._cmd(host, timeout, "PING")
                results.append("+PONG" in out)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=ping) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) >= 25


# ---------------------------------------------------------------------------
# Elasticsearch
# ---------------------------------------------------------------------------


class TestElasticsearch:
    PORT = 9200

    def test_root_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 200

    def test_cluster_name(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        data = json.loads(body)
        assert "cluster_name" in data

    def test_version_8(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        data = json.loads(body)
        assert data["version"]["number"].startswith("8.")

    def test_tagline(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        data = json.loads(body)
        assert "You Know" in data.get("tagline", "")

    def test_elastic_product_header(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "elasticsearch" in hdrs.get("x-elastic-product", "").lower()

    def test_basic_auth_captured(self, host, timeout):
        creds = base64.b64encode(b"elastic:elastic123").decode()
        status, _, _ = http_get(host, self.PORT, headers={"Authorization": f"Basic {creds}"}, timeout=timeout)
        assert status == 200

    def test_bearer_token_captured(self, host, timeout):
        status, _, _ = http_get(
            host,
            self.PORT,
            headers={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.prod.token"},
            timeout=timeout,
        )
        assert status == 200

    @pytest.mark.parametrize("path", ["/_cat/indices", "/_cluster/health", "/_nodes", "/_search"])
    def test_api_paths(self, host, timeout, path):
        status, _, _ = http_get(host, self.PORT, path, timeout=timeout)
        assert status == 200


# ---------------------------------------------------------------------------
# Kubernetes
# ---------------------------------------------------------------------------


class TestKubernetes:
    PORT = 6443

    def test_401_without_auth(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 401

    def test_www_authenticate_bearer(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "bearer" in hdrs.get("www-authenticate", "").lower()

    def test_unauthorized_body(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        assert b"Unauthorized" in body

    def test_bearer_token_captured(self, host, timeout):
        status, _, body = http_get(
            host,
            self.PORT,
            headers={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.k8s.token"},
            path="/api/v1/pods",
            timeout=timeout,
        )
        assert status == 401  # still 401 — token captured but not accepted (correct)

    @pytest.mark.parametrize("path", ["/api", "/api/v1", "/healthz", "/version"])
    def test_common_paths(self, host, timeout, path):
        status, _, _ = http_get(host, self.PORT, path, timeout=timeout)
        assert status in (200, 401, 403)

    def test_x_content_type_options(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "nosniff" in hdrs.get("x-content-type-options", "").lower()


# ---------------------------------------------------------------------------
# Jenkins
# ---------------------------------------------------------------------------


class TestJenkins:
    PORT = 8080

    def test_get_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 200

    def test_server_jetty(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "jetty" in hdrs.get("server", "").lower()

    def test_x_jenkins_header(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "x-jenkins" in hdrs or "x-hudson" in hdrs

    def test_login_form(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        assert b"j_username" in body or b"j_password" in body or b"Jenkins" in body

    def test_post_credential_capture(self, host, timeout):
        status, hdrs, _ = http_post(
            host,
            self.PORT,
            "/j_spring_security_check",
            "j_username=admin&j_password=jenkins123&Submit=Sign+in",
            timeout=timeout,
        )
        assert status == 302
        assert "loginerror" in hdrs.get("location", "").lower()

    def test_basic_auth_captured(self, host, timeout):
        creds = base64.b64encode(b"deploy:deploy-token-abc").decode()
        status, _, _ = http_get(
            host, self.PORT, "/api/json", headers={"Authorization": f"Basic {creds}"}, timeout=timeout
        )
        assert status == 200

    def test_x_jenkins_session(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, timeout=timeout)
        assert "x-jenkins-session" in hdrs

    @pytest.mark.parametrize("path", ["/api/json", "/job/production", "/people", "/manage"])
    def test_paths(self, host, timeout, path):
        status, _, _ = http_get(host, self.PORT, path, timeout=timeout)
        assert status == 200


# ---------------------------------------------------------------------------
# Prometheus
# ---------------------------------------------------------------------------


class TestPrometheus:
    PORT = 9090

    def test_root_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, timeout=timeout)
        assert status == 200

    def test_root_html_body(self, host, timeout):
        _, _, body = http_get(host, self.PORT, timeout=timeout)
        assert b"Prometheus" in body

    def test_metrics_200(self, host, timeout):
        status, _, _ = http_get(host, self.PORT, "/metrics", timeout=timeout)
        assert status == 200

    def test_metrics_content_type(self, host, timeout):
        _, hdrs, _ = http_get(host, self.PORT, "/metrics", timeout=timeout)
        assert "text/plain" in hdrs.get("content-type", "")

    def test_metrics_help_lines(self, host, timeout):
        _, _, body = http_get(host, self.PORT, "/metrics", timeout=timeout)
        assert b"# HELP" in body

    def test_metrics_type_lines(self, host, timeout):
        _, _, body = http_get(host, self.PORT, "/metrics", timeout=timeout)
        assert b"# TYPE" in body

    def test_metrics_has_counters(self, host, timeout):
        _, _, body = http_get(host, self.PORT, "/metrics", timeout=timeout)
        assert b"counter" in body or b"gauge" in body


# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------


class TestMongoDB:
    PORT = 27017

    def _build_op_reply_greeting(self) -> bytes:
        bson_doc = struct.pack("<i", 18) + b"\x10ok\x00\x01\x00\x00\x00\x00"
        msg_len = 16 + 20 + len(bson_doc)
        header = struct.pack("<iiii", msg_len, 1, 1, 1)
        reply_fields = struct.pack("<iqii", 8, 0, 0, 1)
        return header + reply_fields + bson_doc

    # MongoDB handler reads first before sending OP_REPLY, so we send a probe.
    OP_MSG = (
        b"\x48\x00\x00\x00"  # length
        b"\x01\x00\x00\x00"  # requestId
        b"\x00\x00\x00\x00"  # responseTo
        b"\xdd\x07\x00\x00"  # opCode: OP_MSG
        b"\x00\x00\x00\x00"  # flagBits
        b"\x00"  # section kind 0
        b"\x21\x00\x00\x00"
        b"\x10ismaster\x00\x01\x00\x00\x00"
        b"\x02\x24\x64\x62\x00\x06\x00\x00\x00admin\x00"
        b"\x00"
    )

    def test_responds_on_connect(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.OP_MSG)
        data = s.recv(256)
        s.close()
        assert len(data) > 0

    def test_op_reply_ok(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.OP_MSG)
        data = s.recv(256)
        s.close()
        # OP_REPLY opcode = 1, at bytes 12-15
        if len(data) >= 16:
            opcode = struct.unpack("<i", data[12:16])[0]
            assert opcode == 1

    def test_responds_to_op_msg(self, host, timeout):
        s = tcp_connect(host, self.PORT, timeout)
        s.sendall(self.OP_MSG)
        data = s.recv(256)
        s.close()
        assert len(data) > 0


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_http_100_sequential(self, host, timeout):
        start = time.monotonic()
        errors = 0
        for _ in range(100):
            try:
                status, _, _ = http_get(host, 80, timeout=timeout)
                if status != 200:
                    errors += 1
            except Exception:
                errors += 1
        elapsed = time.monotonic() - start
        rps = 100 / elapsed
        assert errors < 5, f"{errors} errors in 100 HTTP requests"
        assert rps > 5, f"Too slow: {rps:.1f} req/s (expected >5)"

    def test_redis_pipeline_200(self, host, timeout):
        s = tcp_connect(host, 6379, timeout * 5)
        pipeline = b"PING\r\n" * 200
        s.sendall(pipeline)
        time.sleep(1.0)
        data = b""
        s.settimeout(2.0)
        try:
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
        except TimeoutError:
            pass
        s.close()
        pongs = data.count(b"+PONG")
        assert pongs >= 190, f"Only {pongs}/200 PONGs in pipeline"

    def test_concurrent_http_50(self, host, timeout):
        import threading

        results = []

        def req():
            try:
                status, _, _ = http_get(host, 80, timeout=timeout)
                results.append(status == 200)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=req) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) >= 45

    def test_concurrent_redis_30(self, host, timeout):
        import threading

        results = []

        def ping():
            try:
                s = tcp_connect(host, 6379, timeout)
                s.sendall(b"PING\r\n")
                data = s.recv(64)
                s.close()
                results.append(b"+PONG" in data)
            except Exception:
                results.append(False)

        threads = [threading.Thread(target=ping) for _ in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sum(results) >= 25

    def test_all_ports_respond_concurrently(self, host, timeout):
        import threading

        ports = [
            21,
            22,
            23,
            25,
            80,
            110,
            143,
            389,
            443,
            445,
            3306,
            3389,
            5432,
            6379,
            6443,
            8080,
            9090,
            9200,
            27017,
        ]
        results = {}

        def check(port):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((host, port))
            s.close()
            results[port] = result == 0

        threads = [threading.Thread(target=check, args=(p,)) for p in ports]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        failed = [p for p, ok in results.items() if not ok]
        assert len(failed) == 0, f"Ports not reachable: {failed}"

    def test_http_response_time(self, host, timeout):
        times = []
        for _ in range(10):
            start = time.monotonic()
            http_get(host, 80, timeout=timeout)
            times.append(time.monotonic() - start)
        avg = sum(times) / len(times)
        assert avg < 1.0, f"HTTP avg response {avg:.3f}s too slow (>1s)"

    def test_redis_response_time(self, host, timeout):
        times = []
        for _ in range(20):
            s = tcp_connect(host, 6379, timeout)
            start = time.monotonic()
            s.sendall(b"PING\r\n")
            s.recv(64)
            times.append(time.monotonic() - start)
            s.close()
        avg = sum(times) / len(times)
        assert avg < 0.1, f"Redis avg response {avg:.4f}s too slow (>100ms)"


# ---------------------------------------------------------------------------
# Log integration
# ---------------------------------------------------------------------------


class TestLogIntegration:
    def _get_log_stats(self):
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "network-buoy",
                    ".venv/bin/python",
                    "-c",
                    """
import json, collections
conn = collections.Counter()
cred = collections.Counter()
with open('/data/honeypot.log') as f:
    for line in f:
        try:
            e = json.loads(line)
            if e['event'] == 'connection': conn[e['protocol']] += 1
            elif e['event'] == 'credential': cred[e['protocol']] += 1
        except: pass
import sys, json
json.dump({'conn': dict(conn), 'cred': dict(cred)}, sys.stdout)
""",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return json.loads(result.stdout)
        except Exception:
            return {"conn": {}, "cred": {}}

    def test_connections_logged(self):
        stats = self._get_log_stats()
        total = sum(stats["conn"].values())
        assert total > 0, "No connection events in log"

    def test_credentials_logged(self):
        stats = self._get_log_stats()
        total = sum(stats["cred"].values())
        assert total > 0, "No credential events in log"

    @pytest.mark.parametrize("proto", ["HTTP", "FTP", "Redis", "PostgreSQL", "IMAP", "POP3", "Jenkins"])
    def test_protocol_credential_captured(self, proto):
        stats = self._get_log_stats()
        assert stats["cred"].get(proto, 0) > 0, f"No credentials captured for {proto}"
