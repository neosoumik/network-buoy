"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import { useEventStream } from "@/hooks/useEventStream";
import { isCredentialEvent } from "@/lib/normalize";
import { StatusBar } from "@/components/StatusBar";
import { StatCard } from "@/components/StatCard";
import { EventFeed } from "@/components/EventFeed";
import { ProtocolChart } from "@/components/ProtocolChart";
import { CredentialTable } from "@/components/CredentialTable";
import { TopAttackers } from "@/components/TopAttackers";
import type { DisplayEvent } from "@/lib/types";

type TimeWindow = "5m" | "15m" | "1h" | "6h" | "all";
const TIME_WINDOWS: { label: string; value: TimeWindow; ms: number | null }[] = [
  { label: "5m",  value: "5m",  ms: 5 * 60 * 1000 },
  { label: "15m", value: "15m", ms: 15 * 60 * 1000 },
  { label: "1h",  value: "1h",  ms: 60 * 60 * 1000 },
  { label: "6h",  value: "6h",  ms: 6 * 60 * 60 * 1000 },
  { label: "ALL", value: "all", ms: null },
];

type SeverityFilter = "all" | "critical" | "warning";

function filterByTime(events: DisplayEvent[], window: TimeWindow): DisplayEvent[] {
  const entry = TIME_WINDOWS.find((w) => w.value === window);
  if (!entry?.ms) return events;
  const cutoff = Date.now() - entry.ms;
  return events.filter((e) => new Date(e.timestamp).getTime() >= cutoff);
}

function filterBySeverity(events: DisplayEvent[], sev: SeverityFilter): DisplayEvent[] {
  if (sev === "all") return events;
  if (sev === "critical") return events.filter((e) => e.severity === "E_CRITICAL");
  return events.filter((e) => e.severity === "E_WARNING" || e.severity === "E_ERROR");
}

function filterByProtocol(events: DisplayEvent[], protos: Set<string>): DisplayEvent[] {
  if (protos.size === 0) return events;
  return events.filter((e) => protos.has(e.protocol));
}

function useClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return now;
}

function useRefreshSpin(status: string) {
  const [spinning, setSpinning] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSpinning(status === "connecting"), 0);
    if (status !== "connecting") {
      return () => clearTimeout(t);
    }
    const off = setTimeout(() => setSpinning(false), 400);
    return () => {
      clearTimeout(t);
      clearTimeout(off);
    };
  }, [status]);
  return spinning;
}

export default function Dashboard() {
  const { events, status, reconnect } = useEventStream();
  const now = useClock();
  const spinning = useRefreshSpin(status);

  const [timeWindow, setTimeWindow] = useState<TimeWindow>("all");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [selectedProtocols, setSelectedProtocols] = useState<Set<string>>(new Set());

  const allProtocols = useMemo(() => {
    const s = new Set(events.map((e) => e.protocol));
    return [...s].sort();
  }, [events]);

  const toggleProtocol = useCallback((proto: string) => {
    setSelectedProtocols((prev) => {
      const next = new Set(prev);
      if (next.has(proto)) next.delete(proto);
      else next.add(proto);
      return next;
    });
  }, []);

  const clearFilters = useCallback(() => {
    setTimeWindow("all");
    setSeverityFilter("all");
    setSelectedProtocols(new Set());
  }, []);

  const filtered = useMemo(() => {
    let ev = filterByTime(events, timeWindow);
    ev = filterBySeverity(ev, severityFilter);
    ev = filterByProtocol(ev, selectedProtocols);
    return ev;
  }, [events, timeWindow, severityFilter, selectedProtocols]);

  const stats = useMemo(() => {
    const credentials = filtered.filter(isCredentialEvent).length;
    const uniqueIps = new Set(filtered.map((e) => e.srcIp.split(":")[0])).size;
    const topProto = Object.entries(
      filtered.reduce<Record<string, number>>((acc, e) => {
        acc[e.protocol] = (acc[e.protocol] ?? 0) + 1;
        return acc;
      }, {}),
    ).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";
    return { credentials, uniqueIps, topProto };
  }, [filtered]);

  const filtersActive =
    timeWindow !== "all" || severityFilter !== "all" || selectedProtocols.size > 0;

  return (
    <div className="flex flex-col h-full relative z-10">

      <header className="px-6 py-3 border-b border-blue-900/50 bg-[#020814] flex items-center gap-4">
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="shrink-0">
            <circle cx="14" cy="14" r="12" stroke="#22d3ee" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="6" stroke="#3b82f6" strokeWidth="1" />
            <line x1="14" y1="2"  x2="14" y2="8"  stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="14" y1="20" x2="14" y2="26" stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="2"  y1="14" x2="8"  y2="14" stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="20" y1="14" x2="26" y2="14" stroke="#22d3ee" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="2" fill="#22d3ee" />
          </svg>
          <div>
            <h1 className="text-sm font-mono font-bold text-cyan-400 tracking-widest uppercase leading-none">
              Network Buoy
            </h1>
            <p className="text-xs font-mono text-blue-700 leading-none mt-0.5">
              Threat Intelligence Feed
            </p>
          </div>
        </div>

        <div className="flex-1" />

        <button
          onClick={reconnect}
          title="Reconnect stream"
          className="flex items-center gap-1.5 px-3 py-1 border border-blue-800/60 rounded text-xs font-mono text-blue-400 hover:text-cyan-400 hover:border-cyan-800 transition-colors"
        >
          <svg
            width="12" height="12" viewBox="0 0 12 12" fill="none"
            className={spinning ? "animate-spin" : ""}
          >
            <path
              d="M10 6A4 4 0 1 1 6 2V0L9 3 6 6V4A3 3 0 1 0 9 6h1z"
              fill="currentColor"
            />
          </svg>
          REFRESH
        </button>

        <div className="flex flex-col items-end font-mono text-xs tabular-nums leading-tight">
          <span className="text-blue-500 tracking-widest">
            {now.toUTCString().replace(/:\d\d GMT$/, (m) => m.replace("GMT", "UTC"))}
          </span>
          <span className="text-blue-800 tracking-widest">
            LOCAL {now.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
            {" "}{Intl.DateTimeFormat().resolvedOptions().timeZone}
          </span>
        </div>
      </header>

      <StatusBar status={status} events={filtered} totalEvents={events.length} />

      <div className="flex flex-wrap items-center gap-3 px-4 py-2 border-b border-blue-900/30 bg-[#020c18]">
        <div className="flex items-center gap-1">
          <span className="text-blue-700 text-xs font-mono mr-1 uppercase tracking-widest">Window</span>
          {TIME_WINDOWS.map((w) => (
            <button
              key={w.value}
              onClick={() => setTimeWindow(w.value)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors border ${
                timeWindow === w.value
                  ? "bg-cyan-900/40 border-cyan-700 text-cyan-400"
                  : "border-blue-900/50 text-blue-600 hover:text-blue-400 hover:border-blue-700"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>

        <div className="text-blue-900">|</div>

        <div className="flex items-center gap-1">
          <span className="text-blue-700 text-xs font-mono mr-1 uppercase tracking-widest">Severity</span>
          {(["all", "critical", "warning"] as SeverityFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-2 py-0.5 rounded text-xs font-mono transition-colors border ${
                severityFilter === s
                  ? s === "critical"
                    ? "bg-red-900/40 border-red-700 text-red-400"
                    : s === "warning"
                      ? "bg-yellow-900/30 border-yellow-700 text-yellow-400"
                      : "bg-cyan-900/40 border-cyan-700 text-cyan-400"
                  : "border-blue-900/50 text-blue-600 hover:text-blue-400 hover:border-blue-700"
              }`}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>

        {allProtocols.length > 0 && (
          <>
            <div className="text-blue-900">|</div>
            <div className="flex flex-wrap items-center gap-1">
              <span className="text-blue-700 text-xs font-mono mr-1 uppercase tracking-widest">Proto</span>
              {allProtocols.map((p) => (
                <button
                  key={p}
                  onClick={() => toggleProtocol(p)}
                  className={`px-2 py-0.5 rounded text-xs font-mono transition-colors border ${
                    selectedProtocols.has(p)
                      ? "bg-blue-800/50 border-blue-500 text-blue-200"
                      : "border-blue-900/40 text-blue-700 hover:text-blue-400 hover:border-blue-700"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </>
        )}

        {filtersActive && (
          <button
            onClick={clearFilters}
            className="ml-auto text-xs font-mono text-blue-700 hover:text-red-400 transition-colors border border-blue-900/40 hover:border-red-900/60 px-2 py-0.5 rounded"
          >
            ✕ CLEAR
          </button>
        )}

        {filtersActive && (
          <span className="text-xs font-mono text-blue-700">
            {filtered.length} / {events.length} events
          </span>
        )}
      </div>

      <div className="grid grid-cols-4 gap-3 px-4 py-3 border-b border-blue-900/30">
        <StatCard label="Total Events"         value={filtered.length} sub={filtersActive ? `of ${events.length} total` : "since session start"} accent="cyan" />
        <StatCard label="Credentials Captured" value={stats.credentials} sub="unique auth attempts"  accent="red"    />
        <StatCard label="Unique Attackers"     value={stats.uniqueIps}   sub="distinct source IPs"   accent="yellow" />
        <StatCard label="Top Protocol"         value={stats.topProto}    sub="most targeted service"  accent="green"  />
      </div>

      <div className="flex-1 grid grid-cols-12 gap-3 p-4 overflow-hidden min-h-0">
        <div className="col-span-5 overflow-hidden flex flex-col min-h-0">
          <EventFeed events={filtered} />
        </div>
        <div className="col-span-7 grid grid-rows-3 gap-3 min-h-0">
          <div className="row-span-1 min-h-0"><ProtocolChart events={filtered} /></div>
          <div className="row-span-1 min-h-0"><TopAttackers events={filtered} /></div>
          <div className="row-span-1 min-h-0"><CredentialTable events={filtered} /></div>
        </div>
      </div>
    </div>
  );
}
