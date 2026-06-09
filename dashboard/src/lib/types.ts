export type EventType =
  | "NETCONN"
  | "PROCESS"
  | "FILE"
  | "REGKEY"
  | "DNS"
  | "URL"
  | "LOGIN"
  | "LOGOUT"
  | "INDICATOR";

export type SeverityLevel = "E_NOTICE" | "E_WARNING" | "E_ERROR" | "E_CRITICAL";

export type BuoyEvent = {
  EventTime: string;
  EventType: EventType;
  SeverityLevel?: SeverityLevel;
  AgentId?: string;
  SiteName?: string;
  SrcIP?: string;
  SrcPort?: number;
  DstIP?: string;
  DstPort?: number;
  NetworkDirection?: "INCOMING" | "OUTGOING";
  NetworkProtocol?: string;
  Username?: string;
  Password?: string;
  ObjectType?: string;
  ProcessName?: string;
  CmdLine?: string;
  Md5?: string;
  Sha256?: string;
  FileFullName?: string;
  TgtFilePath?: string;
  DnsRequest?: string;
  Url?: string;
  RawData?: string;
  Protocol?: string;
};

export type DisplayEvent = {
  id: string;
  timestamp: string;
  eventType: EventType;
  severity: SeverityLevel;
  protocol: string;
  srcIp: string;
  dstPort: number | null;
  username: string | null;
  secret: string | null;
  raw: BuoyEvent;
};
