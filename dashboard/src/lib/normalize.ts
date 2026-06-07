import type { BuoyEvent, DisplayEvent, SeverityLevel } from "@/lib/types";

// Map destination port numbers to protocol names when no label is given
const PORT_PROTO: Record<number, string> = {
  21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
  80: "HTTP", 110: "POP3", 143: "IMAP", 389: "LDAP",
  443: "HTTPS", 445: "SMB", 3306: "MySQL", 3389: "RDP",
  5432: "PostgreSQL", 6379: "Redis", 6443: "Kubernetes",
  8080: "Jenkins", 9090: "Prometheus", 9200: "Elasticsearch",
  27017: "MongoDB",
};

function resolveProtocol(ev: BuoyEvent): string {
  if (ev.Protocol) return ev.Protocol;
  if (ev.NetworkProtocol) return ev.NetworkProtocol;
  if (ev.DstPort && PORT_PROTO[ev.DstPort]) return PORT_PROTO[ev.DstPort];
  return ev.EventType;
}

export function normalize(ev: BuoyEvent): DisplayEvent {
  return {
    id: crypto.randomUUID(),
    timestamp: ev.EventTime,
    eventType: ev.EventType,
    severity: ev.SeverityLevel ?? "E_NOTICE",
    protocol: resolveProtocol(ev),
    srcIp: ev.SrcIP ?? "unknown",
    dstPort: ev.DstPort ?? null,
    username: ev.Username ?? null,
    secret: ev.Password ?? null,
    raw: ev,
  };
}

export function isCredentialEvent(ev: DisplayEvent): boolean {
  return (
    ev.eventType === "LOGIN" ||
    ev.username !== null ||
    ev.secret !== null
  );
}

export function severityColor(s: SeverityLevel): string {
  switch (s) {
    case "E_CRITICAL": return "text-red-400";
    case "E_ERROR":    return "text-orange-400";
    case "E_WARNING":  return "text-yellow-400";
    default:           return "text-blue-400";
  }
}
