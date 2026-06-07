"use client";

import { format } from "date-fns";
import type { BuoyEvent } from "@/lib/types";

type Props = { events: BuoyEvent[] };

const PROTO_COLOR: Record<string, string> = {
  SSH: "text-cyan-400",
  FTP: "text-blue-400",
  Telnet: "text-purple-400",
  HTTP: "text-green-400",
  HTTPS: "text-green-300",
  SMTP: "text-orange-400",
  POP3: "text-orange-300",
  IMAP: "text-orange-200",
  MySQL: "text-yellow-400",
  PostgreSQL: "text-yellow-300",
  Redis: "text-red-400",
  Elasticsearch: "text-yellow-200",
  Jenkins: "text-orange-500",
  Kubernetes: "text-blue-300",
  Prometheus: "text-orange-400",
  MongoDB: "text-green-500",
  RDP: "text-pink-400",
  SMB: "text-purple-300",
  LDAP: "text-teal-400",
};

function protoColor(p: string): string {
  return PROTO_COLOR[p] ?? "text-white";
}

export function EventFeed({ events }: Props) {
  return (
    <div className="border border-blue-900/60 bg-[#020c18] rounded flex flex-col h-full">
      <div className="px-4 py-2 border-b border-blue-900/50 text-xs font-mono text-blue-400 uppercase tracking-widest flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
        Live Feed
      </div>
      <div className="flex-1 overflow-y-auto font-mono text-xs leading-5 p-2 space-y-0.5">
        {events.length === 0 && (
          <div className="text-blue-800 p-4 text-center">Awaiting contact...</div>
        )}
        {events.map((ev, i) => (
          <div
            key={i}
            className={`flex gap-2 px-2 py-0.5 rounded hover:bg-blue-950/30 transition-colors ${
              ev.event === "credential" ? "bg-red-950/20" : ""
            }`}
          >
            <span className="text-blue-700 shrink-0">
              {format(new Date(ev.timestamp), "HH:mm:ss")}
            </span>
            <span className={`shrink-0 w-16 ${protoColor(ev.protocol)}`}>{ev.protocol}</span>
            <span className="text-blue-300 shrink-0">{ev.ip.split(":")[0]}</span>
            {ev.event === "credential" ? (
              <span className="text-red-400">
                ⚡ CRED{" "}
                {ev.username && <span className="text-red-300">user={ev.username}</span>}
                {ev.password && (
                  <span className="text-red-500"> pass={ev.password}</span>
                )}
                {ev.token && <span className="text-red-300"> token={ev.token}</span>}
              </span>
            ) : (
              <span className="text-blue-600 truncate">{ev.data?.slice(0, 60)}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
