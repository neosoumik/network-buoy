"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { BuoyEvent } from "@/lib/types";

type Props = { events: BuoyEvent[] };

const BAR_COLORS = [
  "#22d3ee", "#3b82f6", "#8b5cf6", "#ec4899",
  "#f59e0b", "#10b981", "#f87171", "#a78bfa",
];

export function ProtocolChart({ events }: Props) {
  const counts: Record<string, number> = {};
  for (const ev of events) {
    counts[ev.protocol] = (counts[ev.protocol] ?? 0) + 1;
  }
  const data = Object.entries(counts)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 12);

  return (
    <div className="border border-blue-900/60 bg-[#020c18] rounded flex flex-col h-full">
      <div className="px-4 py-2 border-b border-blue-900/50 text-xs font-mono text-blue-400 uppercase tracking-widest">
        Protocol Hits
      </div>
      <div className="flex-1 p-2">
        {data.length === 0 ? (
          <div className="text-blue-800 text-xs font-mono p-4 text-center">No data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <XAxis
                dataKey="name"
                tick={{ fill: "#1e3a5f", fontSize: 10, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#1e3a5f", fontSize: 10, fontFamily: "monospace" }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#020c18",
                  border: "1px solid #1e3a5f",
                  borderRadius: 4,
                  fontFamily: "monospace",
                  fontSize: 11,
                  color: "#93c5fd",
                }}
                cursor={{ fill: "#0f172a" }}
              />
              <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                {data.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
