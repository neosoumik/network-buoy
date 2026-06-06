import socket
import time

from ..identity import HOSTNAME, LAST_LOGIN_DATE, LAST_LOGIN_IP
from ..logger import log_credential
from ..prompts import TELNET_BANNER

IAC = b"\xff"
WILL = b"\xfb"
DO = b"\xfd"

OPT_ECHO = b"\x01"
OPT_SUPPRESS_GA = b"\x03"
OPT_TERMINAL_TYPE = b"\x18"
OPT_NAWS = b"\x1f"

_NEGOTIATION = (
    IAC + WILL + OPT_ECHO + IAC + WILL + OPT_SUPPRESS_GA + IAC + DO + OPT_TERMINAL_TYPE + IAC + DO + OPT_NAWS
)

_LOGIN_PROMPT = b"login: "
_PASSWD_PROMPT = b"Password: "
_FAILED = b"\r\nLogin incorrect\r\n\r\n"

# Commands the fake shell responds to
_SHELL_PROMPT = b"\r\n$ "
_FAKE_UNAME = f"Linux {HOSTNAME} 6.1.0-21-amd64 #1 SMP x86_64 GNU/Linux\r\n".encode()
_FAKE_WHOAMI = b"root\r\n"
_FAKE_ID = b"uid=0(root) gid=0(root) groups=0(root)\r\n"
_FAKE_LS = (
    b"bin  boot  dev  etc  home  lib  lib64  "
    b"media  mnt  opt  proc  root  run  sbin  "
    b"srv  sys  tmp  usr  var\r\n"
)


def _recv_line(conn: socket.socket) -> bytes:
    buf = b""
    while True:
        try:
            byte = conn.recv(1)
        except OSError:
            break
        if not byte:
            break
        if byte == b"\xff":
            conn.recv(2)  # skip IAC option negotiation
            continue
        buf += byte
        if byte in (b"\n", b"\r"):
            break
    return buf.strip()


def _fake_shell(conn: socket.socket) -> None:
    conn.sendall(f"\r\nLast login: {LAST_LOGIN_DATE} from {LAST_LOGIN_IP}\r\n".encode())
    conn.sendall(_SHELL_PROMPT)

    while True:
        line = _recv_line(conn).decode("utf-8", errors="replace").strip()
        if not line:
            conn.sendall(_SHELL_PROMPT)
            continue

        cmd = line.split()[0].lower() if line.split() else ""

        if cmd in ("exit", "logout", "quit"):
            conn.sendall(b"logout\r\n")
            break
        elif cmd == "uname":
            conn.sendall(_FAKE_UNAME)
        elif cmd == "whoami":
            conn.sendall(_FAKE_WHOAMI)
        elif cmd == "id":
            conn.sendall(_FAKE_ID)
        elif cmd == "ls":
            conn.sendall(_FAKE_LS)
        elif cmd == "pwd":
            conn.sendall(b"/root\r\n")
        elif cmd == "cat":
            conn.sendall(b"cat: permission denied\r\n")
        elif cmd == "wget" or cmd == "curl":
            # Stall — attacker trying to download tools
            time.sleep(5)
            conn.sendall(b"curl: (6) Could not resolve host\r\n")
        elif cmd == "":
            pass
        else:
            conn.sendall(f"{line}: command not found\r\n".encode())

        conn.sendall(_SHELL_PROMPT)


def handle_telnet(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            conn.sendall(_NEGOTIATION)
            banner = TELNET_BANNER.get()
            conn.sendall(("\r\n" + banner + "\r\n").encode())

            # Give attacker 2 attempts before accepting, 3rd always works
            for attempt in range(3):
                conn.sendall(_LOGIN_PROMPT)
                username = _recv_line(conn).decode("utf-8", errors="replace").strip()
                conn.sendall(_PASSWD_PROMPT)
                password = _recv_line(conn).decode("utf-8", errors="replace").strip()

                if attempt < 1:
                    # First attempt: fail to look real
                    conn.sendall(_FAILED)
                else:
                    # Accept on second attempt — log and drop into shell
                    log_credential("Telnet", ip_str, username=username, password=password)
                    _fake_shell(conn)
                    break

        except OSError:
            pass
