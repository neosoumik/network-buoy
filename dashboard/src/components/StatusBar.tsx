"use client";

import { formatDistanceToNow } from "date-fns";
import type { StreamStatus } from "@/hooks/useBuoyStream";
import type { BuoyEvent } from "@/lib/types";

type Props = {
  status: StreamStatus;
  events: BuoyEvent[];
};

const STATUS_COLORS: Record<StreamStatus, string> = {
  connected: "text-cyan-400",
  connecting: "text-yellow-400",
  disconnected: "text-red-500",
};

const STATUS_LABELS: Record<StreamStatus, string> = {
  connected: "LIVE",
  connecting: "CONNECTING",
  disconnected: "OFFLINE",
};

export function StatusBar({ status, events }: Props) {
  const credentials = events.filter((e) => e.event === "credential").length;
  const uniqueIps = new Set(events.map((e) => e.ip)).size;
  const last = events[0];

  return (
    <div className="flex items-center gap-6 px-6 py-2 border-b border-blue-900/50 bg-[#020814] text-xs font-mono">
      {/* Status indicator */}
      <div className="flex items-center gap-2">
        <span
          className={`inline-block w-2 h-2 rounded-full ${
            status === "connected"
              ? "bg-cyan-400 shadow-[0_0_6px_#22d3ee] animate-pulse"
              : status === "connecting"
                ? "bg-yellow-400 animate-pulse"
                : "bg-red-500"
          }`}
        />
        <span className={STATUS_COLORS[status]}>{STATUS_LABELS[status]}</span>
      </div>

      <div className="text-blue-500">|</div>

      <span className="text-blue-400">
        EVENTS: <span className="text-white">{events.length}</span>
      </span>
      <span className="text-blue-400">
        CREDS: <span className="text-red-400 font-bold">{credentials}</span>
      </span>
      <span className="text-blue-400">
        UNIQUE IPs: <span className="text-white">{uniqueIps}</span>
      </span>

      <div className="flex-1" />

      {last && (
        <span className="text-blue-600">
          LAST HIT:{" "}
          <span className="text-blue-300">
            {formatDistanceToNow(new Date(last.timestamp), { addSuffix: true })}
          </span>
        </span>
      )}

      <span className="text-blue-800">NETWORK-BUOY v0.1</span>
    </div>
  );
}
