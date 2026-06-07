"use client";

import type { DisplayEvent } from "@/lib/types";

type Props = { events: DisplayEvent[] };

export function TopAttackers({ events }: Props) {
  const counts: Record<string, number> = {};
  for (const ev of events) {
    const ip = ev.srcIp.split(":")[0];
    counts[ip] = (counts[ip] ?? 0) + 1;
  }
  const top = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const max = top[0]?.[1] ?? 1;

  return (
    <div className="border border-blue-900/60 bg-[#020c18] rounded flex flex-col h-full">
      <div className="px-4 py-2 border-b border-blue-900/50 text-xs font-mono text-blue-400 uppercase tracking-widest">
        Top Attackers
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {top.length === 0 && (
          <div className="text-blue-800 text-xs font-mono text-center pt-4">No data yet</div>
        )}
        {top.map(([ip, count], i) => (
          <div key={ip} className="flex items-center gap-2 font-mono text-xs">
            <span className="text-blue-800 w-4 shrink-0">{i + 1}</span>
            <span className="text-blue-300 w-32 shrink-0 truncate">{ip}</span>
            <div className="flex-1 h-1.5 bg-blue-950 rounded overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-cyan-400 rounded transition-all duration-500"
                style={{ width: `${(count / max) * 100}%` }}
              />
            </div>
            <span className="text-cyan-400 w-8 text-right shrink-0">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
