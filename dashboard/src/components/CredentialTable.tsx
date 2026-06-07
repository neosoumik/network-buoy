"use client";

import { format } from "date-fns";
import type { DisplayEvent } from "@/lib/types";
import { isCredentialEvent } from "@/lib/normalize";

type Props = { events: DisplayEvent[] };

export function CredentialTable({ events }: Props) {
  const creds = events.filter(isCredentialEvent).slice(0, 50);

  return (
    <div className="border border-red-900/40 bg-[#0d0204] rounded flex flex-col h-full">
      <div className="px-4 py-2 border-b border-red-900/40 text-xs font-mono text-red-400 uppercase tracking-widest flex items-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
        Credential Harvest ({creds.length})
      </div>
      <div className="flex-1 overflow-y-auto">
        {creds.length === 0 ? (
          <div className="text-red-900 text-xs font-mono p-4 text-center">
            No credentials captured yet
          </div>
        ) : (
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-[#0d0204]">
              <tr className="text-red-800 border-b border-red-900/30">
                <th className="text-left px-3 py-1">TIME</th>
                <th className="text-left px-3 py-1">PROTO</th>
                <th className="text-left px-3 py-1">SRC IP</th>
                <th className="text-left px-3 py-1">USER</th>
                <th className="text-left px-3 py-1">SECRET</th>
              </tr>
            </thead>
            <tbody>
              {creds.map((ev) => (
                <tr
                  key={ev.id}
                  className="border-b border-red-950/30 hover:bg-red-950/20 transition-colors"
                >
                  <td className="px-3 py-0.5 text-red-900">
                    {format(new Date(ev.timestamp), "HH:mm:ss")}
                  </td>
                  <td className="px-3 py-0.5 text-red-400">{ev.protocol}</td>
                  <td className="px-3 py-0.5 text-red-300">{ev.srcIp.split(":")[0]}</td>
                  <td className="px-3 py-0.5 text-orange-300">{ev.username ?? "—"}</td>
                  <td className="px-3 py-0.5 text-red-500">{ev.secret ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
