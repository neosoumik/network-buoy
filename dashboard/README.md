# network-buoy dashboard (PoC)

A demo-only sci-fi HUD for local presentations. Not intended for production.

Runs a local ingest endpoint so you can point buoy at it and watch attacks visualise in real-time.

---

## Running

```bash
# From the project root — buoy must be up first (creates the shared Docker network)
docker compose -f docker-compose.buoy.yml up -d
docker compose -f dashboard/docker-compose.yml up -d
```

Dashboard at `http://localhost:3000`. Wire buoy to it:

```yaml
# docker-compose.buoy.yml
environment:
  INGEST_URL: "http://network-buoy-dashboard:3000/api/ingest"
```

---

## Ingest endpoint

```
POST /api/ingest
Content-Type: application/json
Authorization: ApiToken <token>   # only required if API_TOKEN is set on the dashboard
```

Accepts a single event or a JSON array. Each event must have `EventTime` and `EventType`:

```json
[
  {
    "EventTime": "2026-06-07T11:00:00.000Z",
    "EventType": "NETCONN",
    "SrcIP": "185.220.101.47",
    "DstPort": 22,
    "Protocol": "SSH",
    "SeverityLevel": "E_WARNING"
  },
  {
    "EventTime": "2026-06-07T11:00:01.000Z",
    "EventType": "LOGIN",
    "SrcIP": "185.220.101.47",
    "Protocol": "SSH",
    "Username": "root",
    "Password": "toor",
    "SeverityLevel": "E_CRITICAL"
  }
]
```

Returns `{"ingested": <count>}` on success.

---

## Event schema

| Field              | Type   | Description                                                    |
|--------------------|--------|----------------------------------------------------------------|
| `EventTime`        | string | ISO-8601 timestamp — **required**                              |
| `EventType`        | string | `NETCONN` `LOGIN` `PROCESS` `FILE` `DNS` `URL` — **required** |
| `SeverityLevel`    | string | `E_NOTICE` `E_WARNING` `E_ERROR` `E_CRITICAL`                  |
| `SrcIP`            | string | Source IP address                                              |
| `DstPort`          | number | Destination port — used to infer protocol label if absent      |
| `Protocol`         | string | Protocol label (`SSH`, `HTTP`, etc.) — overrides DstPort       |
| `Username`         | string | Captured username                                              |
| `Password`         | string | Captured password or token                                     |
| `NetworkDirection` | string | `INCOMING` or `OUTGOING`                                       |
| `ProcessName`      | string | Process name (for `PROCESS` events)                            |
| `DnsRequest`       | string | DNS query (for `DNS` events)                                   |
| `Url`              | string | URL (for `URL` events)                                         |
| `AgentId`          | string | Sensor / agent identifier                                      |
| `SiteName`         | string | Site or deployment name                                        |
| `RawData`          | string | Raw payload (honeypot-specific)                                |

---

## Environment variables

| Variable     | Default   | Description                                                           |
|--------------|-----------|-----------------------------------------------------------------------|
| `API_TOKEN`  | _(unset)_ | If set, requires `Authorization: ApiToken <token>` on ingest requests |
