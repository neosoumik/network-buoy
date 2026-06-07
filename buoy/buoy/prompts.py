"""
LLM prompt definitions and cache registration for every protocol.

Each prompt is seeded with the stable node identity so the LLM produces
content consistent with *this* node across retries and restarts.
"""

from . import cache, llm
from .identity import (
    COMPANY,
    ES_CLUSTER_NAME,
    ES_CLUSTER_UUID,
    ES_NODE_NAME,
    HOSTNAME,
    INTERNAL_IP,
    JENKINS_SESSION,
    K8S_CLUSTER,
    LAST_LOGIN_DATE,
    LAST_LOGIN_IP,
    PROM_INSTANCE,
    REDIS_CLIENTS,
    REDIS_CMDS,
    REDIS_MEMORY,
    REDIS_UPTIME,
)


def _gen(prompt: str, max_tokens: int = 200) -> str:
    return llm.generate(prompt, max_tokens)


# ── SSH ───────────────────────────────────────────────────────────────────────

SSH_MOTD = cache.register(
    "ssh_motd",
    lambda: _gen(
        f"Generate a realistic Linux SSH message-of-the-day for server '{HOSTNAME}' ({INTERNAL_IP}). "
        f"Last login was {LAST_LOGIN_DATE} from {LAST_LOGIN_IP}. "
        "Include the last login line, a security warning, and maybe system load. "
        "Plain text, 4-6 lines, no markdown, no quotes.",
        120,
    ),
    fallback=(
        f"Last login: {LAST_LOGIN_DATE} from {LAST_LOGIN_IP}\r\n"
        f"Welcome to {HOSTNAME}. Unauthorized access is prohibited.\r\n"
        "System information as of today:\r\n"
        "  Load average: 0.42, 0.38, 0.35\r\n"
    ),
)

# ── FTP ───────────────────────────────────────────────────────────────────────

FTP_LISTING = cache.register(
    "ftp_listing",
    lambda: _gen(
        f"Generate a realistic FTP directory listing (ls -la style) for server '{HOSTNAME}'. "
        "Include 8-12 files: mix of .tar.gz backups, .sql dumps, .conf files, .log files, shell scripts. "
        "Use realistic filenames, sizes, dates in 2024-2026, owner 'ftpuser'. "
        "Format exactly like Unix ls -la output. No markdown, no explanation.",
        220,
    ),
    fallback=(
        "drwxr-xr-x  3 ftpuser ftpuser 4096 May 12 08:31 .\r\n"
        "drwxr-xr-x 18 root    root    4096 Jan  3 11:00 ..\r\n"
        "-rw-r--r--  1 ftpuser ftpuser 524288000 Apr 28 02:15 db_backup_2026-04-28.sql.gz\r\n"
        "-rw-r--r--  1 ftpuser ftpuser 1073741824 Mar 01 03:00 full_backup_2026-03-01.tar.gz\r\n"
        "-rw-------  1 ftpuser ftpuser  2048 Feb 14 16:44 deploy.sh\r\n"
    ),
)

FTP_WELCOME = cache.register(
    "ftp_welcome",
    lambda: _gen(
        f"Write a realistic FTP server welcome message for '{HOSTNAME}'. "
        "One line, plain text, no markdown. Example style: 'FTP server ready. Authorized users only.'",
        40,
    ),
    fallback=f"220 {HOSTNAME} FTP server ready. Authorized users only.\r\n",
)

# ── SMTP ──────────────────────────────────────────────────────────────────────

SMTP_REJECT = cache.register(
    "smtp_reject",
    lambda: _gen(
        f"Write a realistic SMTP 550 rejection error for mail server '{HOSTNAME}'. "
        "One line, plain text, sounds like real postfix. "
        "Example: '550 5.1.1 <user@example.com>: Recipient address rejected: User unknown'",
        60,
    ),
    fallback="550 5.1.1 User unknown in virtual mailbox table.\r\n",
)

# ── POP3 ──────────────────────────────────────────────────────────────────────

POP3_BANNER = cache.register(
    "pop3_banner",
    lambda: _gen(
        f"Write a realistic POP3 server greeting for '{HOSTNAME}'. "
        "Start with '+OK', include server name and a timestamp token like real Dovecot. "
        "One line, no markdown.",
        50,
    ),
    fallback=f"+OK {HOSTNAME} Dovecot ready.\r\n",
)

# ── IMAP ──────────────────────────────────────────────────────────────────────

IMAP_BANNER = cache.register(
    "imap_banner",
    lambda: _gen(
        f"Write a realistic IMAP server greeting for '{HOSTNAME}'. "
        "Start with '* OK [CAPABILITY IMAP4rev1'. "
        "Include STARTTLS, AUTH=PLAIN, AUTH=LOGIN, IDLE, NAMESPACE. "
        "End with 'Dovecot ready.' One line, no markdown.",
        80,
    ),
    fallback=(
        f"* OK [CAPABILITY IMAP4rev1 STARTTLS AUTH=PLAIN AUTH=LOGIN IDLE NAMESPACE]"
        f" {HOSTNAME} Dovecot ready.\r\n"
    ),
)

# ── HTTP ──────────────────────────────────────────────────────────────────────

HTTP_BODY = cache.register(
    "http_body",
    lambda: _gen(
        f"Generate a realistic internal web app HTML login page for '{COMPANY}'. "
        "Include company name, username/password form fields, and a copyright footer. "
        "Under 800 chars, valid HTML, no markdown.",
        400,
    ),
    fallback=(
        f"<!DOCTYPE html><html><head><title>{COMPANY} Portal</title></head>"
        f"<body><h2>{COMPANY} — Employee Portal</h2>"
        "<form><input type='text' placeholder='Username'/><br/>"
        "<input type='password' placeholder='Password'/><br/>"
        "<button>Sign In</button></form>"
        f"<p>&copy; 2026 {COMPANY}. All rights reserved.</p></body></html>"
    ),
)

# ── TELNET ────────────────────────────────────────────────────────────────────

TELNET_BANNER = cache.register(
    "telnet_banner",
    lambda: _gen(
        f"Generate a realistic Linux telnet banner for server '{HOSTNAME}' running Debian bookworm. "
        "Include distro, kernel version, hostname, security notice. "
        "3-5 lines, plain text, no markdown.",
        100,
    ),
    fallback=(
        f"Debian GNU/Linux 12 (bookworm)\r\n"
        f"Kernel 6.1.0-21-amd64 on {HOSTNAME}\r\n"
        "WARNING: Unauthorized access to this system is prohibited.\r\n"
    ),
)

# ── REDIS ─────────────────────────────────────────────────────────────────────

REDIS_INFO = cache.register(
    "redis_info",
    lambda: _gen(
        f"Generate a realistic Redis INFO server section for a node named '{HOSTNAME}'. "
        f"Use: redis_version:7.2.4, uptime_in_seconds:{REDIS_UPTIME}, "
        f"connected_clients:{REDIS_CLIENTS}, used_memory_human:{REDIS_MEMORY}, "
        f"total_commands_processed:{REDIS_CMDS}, role:master. "
        "Plain text key:value pairs, one per line, no markdown.",
        200,
    ),
    fallback=(
        f"# Server\r\nredis_version:7.2.4\r\nuptime_in_seconds:{REDIS_UPTIME}\r\n"
        f"connected_clients:{REDIS_CLIENTS}\r\nused_memory_human:{REDIS_MEMORY}\r\n"
        f"total_commands_processed:{REDIS_CMDS}\r\nrole:master\r\n"
    ),
)

# ── MYSQL ─────────────────────────────────────────────────────────────────────

MYSQL_ERROR = cache.register(
    "mysql_error",
    lambda: _gen(
        f"Write a realistic MySQL access denied error for server '{HOSTNAME}'. "
        f"Format: ERROR 1045 (28000): Access denied for user 'X'@'{INTERNAL_IP}' (using password: YES). "
        "Use a realistic username. One line, no markdown.",
        60,
    ),
    fallback=f"Access denied for user 'root'@'{INTERNAL_IP}' (using password: YES)",
)

# ── ELASTICSEARCH ─────────────────────────────────────────────────────────────

ES_ROOT = cache.register(
    "es_root",
    lambda: _gen(
        f"Generate a realistic Elasticsearch root endpoint JSON response. "
        f"Use exactly: name='{ES_NODE_NAME}', cluster_name='{ES_CLUSTER_NAME}', "
        f"cluster_uuid='{ES_CLUSTER_UUID}', version.number='8.13.0', "
        "tagline='You Know, for Search'. Valid JSON only, no markdown.",
        150,
    ),
    fallback=(
        f'{{"name":"{ES_NODE_NAME}","cluster_name":"{ES_CLUSTER_NAME}",'
        f'"cluster_uuid":"{ES_CLUSTER_UUID}",'
        '"version":{"number":"8.13.0","build_flavor":"default","lucene_version":"9.10.0"},'
        '"tagline":"You Know, for Search"}'
    ),
)

# ── KUBERNETES API ────────────────────────────────────────────────────────────

K8S_UNAUTH = cache.register(
    "k8s_unauth",
    lambda: _gen(
        f"Generate a realistic Kubernetes API 401 Unauthorized JSON response for cluster '{K8S_CLUSTER}'. "
        "Include: kind 'Status', apiVersion 'v1', status 'Failure', "
        "message about bearer token required, reason 'Unauthorized', code 401. "
        "Valid JSON only, no markdown.",
        150,
    ),
    fallback=(
        '{"kind":"Status","apiVersion":"v1","metadata":{},'
        '"status":"Failure","message":"Unauthorized","reason":"Unauthorized",'
        '"code":401}'
    ),
)

# ── PROMETHEUS ────────────────────────────────────────────────────────────────

PROM_METRICS = cache.register(
    "prom_metrics",
    lambda: _gen(
        f"Generate realistic Prometheus /metrics for instance '{PROM_INSTANCE}' (a production web service). "
        "Include 10-15 metrics: http_requests_total with method/status/path labels, "
        "process_cpu_seconds_total, go_goroutines, process_resident_memory_bytes, "
        "custom business metrics like orders_processed_total. "
        "Use proper Prometheus text format with # HELP and # TYPE lines. No markdown.",
        350,
    ),
    fallback=(
        "# HELP http_requests_total Total HTTP requests\n"
        "# TYPE http_requests_total counter\n"
        'http_requests_total{method="GET",status="200",instance="' + PROM_INSTANCE + '"} 142938\n'
        "# HELP process_cpu_seconds_total CPU time\n"
        "# TYPE process_cpu_seconds_total counter\n"
        "process_cpu_seconds_total 4823.17\n"
        "# HELP go_goroutines Goroutine count\n"
        "# TYPE go_goroutines gauge\n"
        "go_goroutines 42\n"
    ),
)

# ── JENKINS ───────────────────────────────────────────────────────────────────

JENKINS_PAGE = cache.register(
    "jenkins_page",
    lambda: _gen(
        f"Generate a realistic Jenkins CI login page HTML for '{COMPANY}' Jenkins server. "
        "Include: Jenkins logo text, username/password form posting to /j_spring_security_check, "
        f"'Remember me' checkbox, Jenkins 2.452.3 in footer, session {JENKINS_SESSION}. "
        "Valid HTML under 900 chars, no markdown.",
        420,
    ),
    fallback=(
        f"<!DOCTYPE html><html><head><title>Jenkins [{COMPANY}]</title></head><body>"
        "<h1>Jenkins</h1>"
        "<form method='post' action='/j_spring_security_check'>"
        "<label>Username: <input name='j_username' type='text'/></label><br/>"
        "<label>Password: <input name='j_password' type='password'/></label><br/>"
        "<label><input type='checkbox' name='remember_me'/> Remember me</label><br/>"
        "<input type='submit' value='Sign In'/></form>"
        "<p>Jenkins 2.452.3</p></body></html>"
    ),
)

# ── POSTGRESQL ────────────────────────────────────────────────────────────────

PG_ERROR = cache.register(
    "pg_error",
    lambda: _gen(
        f"Write a realistic PostgreSQL authentication failure error for server '{HOSTNAME}'. "
        "Format: FATAL: password authentication failed for user 'X'. "
        "Use a realistic username. One line, no markdown.",
        60,
    ),
    fallback='FATAL: password authentication failed for user "postgres"',
)


def start() -> None:
    cache.start_all()
