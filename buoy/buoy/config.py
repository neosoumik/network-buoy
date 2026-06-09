import socket
from collections.abc import Callable

from .protocols import (
    handle_elasticsearch,
    handle_ftp,
    handle_http,
    handle_https,
    handle_imap,
    handle_jenkins,
    handle_kubernetes,
    handle_ldap,
    handle_mongodb,
    handle_mysql,
    handle_pop3,
    handle_postgresql,
    handle_prometheus,
    handle_rdp,
    handle_redis,
    handle_smb,
    handle_smtp,
    handle_ssh,
    handle_telnet,
)

BUFFER_SIZE = 4096

Handler = Callable[[socket.socket], None]

PROTOCOLS: list[tuple[int, str, Handler]] = [
    (22, "SSH", handle_ssh),
    (21, "FTP", handle_ftp),
    (23, "Telnet", handle_telnet),
    (25, "SMTP", handle_smtp),
    (110, "POP3", handle_pop3),
    (143, "IMAP", handle_imap),
    (389, "LDAP", handle_ldap),
    (80, "HTTP", handle_http),
    (443, "HTTPS", handle_https),
    (8080, "Jenkins", handle_jenkins),
    (3306, "MySQL", handle_mysql),
    (5432, "PostgreSQL", handle_postgresql),
    (6379, "Redis", handle_redis),
    (27017, "MongoDB", handle_mongodb),
    (9200, "Elasticsearch", handle_elasticsearch),
    (3389, "RDP", handle_rdp),
    (445, "SMB", handle_smb),
    (6443, "Kubernetes", handle_kubernetes),
    (9090, "Prometheus", handle_prometheus),
]
