import socket

from ..logger import log_credential
from ..prompts import FTP_LISTING, FTP_WELCOME

_FAKE_FILES = (
    "drwxr-xr-x  3 ftpuser ftpuser      4096 May 12 08:31 .\r\n"
    "drwxr-xr-x 18 root    root         4096 Jan  3 11:00 ..\r\n"
    "-rw-r--r--  1 ftpuser ftpuser 524288000 Apr 28 02:15 db_backup_2026-04-28.sql.gz\r\n"
    "-rw-r--r--  1 ftpuser ftpuser 1073741824 Mar 01 03:00 full_backup_2026-03-01.tar.gz\r\n"
    "-rw-------  1 ftpuser ftpuser      2048 Feb 14 16:44 deploy.sh\r\n"
    "-rw-r--r--  1 ftpuser ftpuser     98304 Jan 19 09:12 config_prod.tar.gz\r\n"
    "-rw-r--r--  1 ftpuser ftpuser      4096 Dec 03 22:01 .env.production\r\n"
)


def _recv_line(conn: socket.socket) -> str:
    buf = b""
    while True:
        byte = conn.recv(1)
        if not byte:
            break
        buf += byte
        if byte == b"\n":
            break
    return buf.decode("utf-8", errors="replace").strip()


def handle_ftp(conn: socket.socket) -> None:
    conn.settimeout(30.0)
    with conn:
        try:
            ip = conn.getpeername()
            ip_str = f"{ip[0]}:{ip[1]}"

            welcome = FTP_WELCOME.get().strip()
            if not welcome.startswith("220"):
                welcome = f"220 {welcome}"
            conn.sendall(f"{welcome}\r\n".encode())

            username = ""

            while True:
                line = _recv_line(conn)
                if not line:
                    break
                parts = line.split(None, 1)
                cmd = parts[0].upper() if parts else ""
                arg = parts[1] if len(parts) > 1 else ""

                if cmd == "USER":
                    username = arg
                    conn.sendall(b"331 Please specify the password.\r\n")

                elif cmd == "PASS":
                    # Accept — log the credential
                    log_credential("FTP", ip_str, username=username, password=arg)
                    conn.sendall(b"230 Login successful.\r\n")

                elif cmd == "SYST":
                    conn.sendall(b"215 UNIX Type: L8\r\n")

                elif cmd == "FEAT":
                    conn.sendall(
                        b"211-Features:\r\n"
                        b" EPRT\r\n EPSV\r\n MDTM\r\n PASV\r\n"
                        b" REST STREAM\r\n SIZE\r\n TVFS\r\n"
                        b"211 End\r\n"
                    )

                elif cmd == "PWD":
                    conn.sendall(b'257 "/data" is the current directory\r\n')

                elif cmd == "TYPE":
                    conn.sendall(b"200 Switching to Binary mode.\r\n")

                elif cmd == "PASV":
                    # Passive mode — point to a dead port, client can't actually connect
                    conn.sendall(b"227 Entering Passive Mode (127,0,0,1,19,136).\r\n")

                elif cmd == "LIST":
                    listing = FTP_LISTING.get()
                    listing_bytes = listing.replace("\r\n", "\n").replace("\n", "\r\n").encode()
                    conn.sendall(b"150 Here comes the directory listing.\r\n")
                    conn.sendall(listing_bytes)
                    conn.sendall(b"\r\n226 Directory send OK.\r\n")

                elif cmd in ("STOR", "DELE", "MKD", "RMD", "RNFR", "RNTO", "APPE"):
                    # Pretend to be read-only
                    conn.sendall(b"550 Permission denied.\r\n")

                elif cmd == "RETR":
                    conn.sendall(b"550 Failed to open file.\r\n")

                elif cmd == "QUIT":
                    conn.sendall(b"221 Goodbye.\r\n")
                    break

                else:
                    conn.sendall(b"500 Unknown command.\r\n")

        except OSError:
            pass
