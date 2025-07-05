# Network Buoy

A network honeypot written in Go that monitors and logs connection attempts on multiple ports. This tool uses the same ideology as a tsunami buoy - when it gets hit by network activity, it records the event details.

![tsunami buoy map representation from movie battleship](https://www.artofvfx.com/BATTLESHIP/BS_PROLOGUE_VFX_09.jpg "tsunami buoy map points")

## What is Network Buoy?

Before diving into that question, did you watch the movie Battleship (2012)? If yes, good to meet a person who has great movie taste. If not, please watch it.

As we come back to the question of what is network buoy, it uses the same ideology as that of a tsunami buoy. As a tsunami buoy gets hit by a wave it records the event details, similarly this tool targets to deploy an equivalent which on getting hit by network movement records it.

## Features

- Listens on multiple common service ports
- Logs connection attempts with timestamp, protocol, IP, and data
- Responds with fake service banners to attract attackers
- Concurrent handling of multiple connections
- JSON-formatted logging

## Supported Protocols

- HTTP (port 80)
- HTTPS (port 443)
- RDP (port 3389)
- FTP (port 21)
- SMTP (port 25)
- POP3 (port 110)
- IMAP (port 143)
- Telnet (port 23)
- MySQL (port 3306)
- Redis (port 6379)
- LDAP (port 389)
- MongoDB (port 27017)

## Building and Running

```bash
# Build the application
go build -o network-buoy main.go

# Run the application
./network-buoy

# Or run directly with go
go run main.go
```

## Logging

The application logs all connection attempts to `honeypot.log` in JSON format:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "protocol": "HTTP",
  "ip": "192.168.1.100:12345",
  "data": "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
}
```

## Security Note

This is a honeypot application designed to attract and log malicious activity. Only run this on systems where you expect and want to monitor unauthorized access attempts.

## Contributing

Contributions are welcome! Please submit a pull request with your proposed changes, and ensure they adhere to the AGPL-3.0 guidelines.

## License

[GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.html)
