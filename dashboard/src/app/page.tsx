"use client";

import { useMemo } from "react";
import { useBuoyStream } from "@/hooks/useBuoyStream";
import { StatusBar } from "@/components/StatusBar";
import { StatCard } from "@/components/StatCard";
import { EventFeed } from "@/components/EventFeed";
import { ProtocolChart } from "@/components/ProtocolChart";
import { CredentialTable } from "@/components/CredentialTable";
import { TopAttackers } from "@/components/TopAttackers";

export default function Dashboard() {
  const { events, status } = useBuoyStream();

  const stats = useMemo(() => {
    const credentials = events.filter((e) => e.event === "credential");
    const uniqueIps = new Set(events.map((e) => e.ip.split(":")[0])).size;
    const topProto = Object.entries(
      events.reduce<Record<string, number>>((acc, e) => {
        acc[e.protocol] = (acc[e.protocol] ?? 0) + 1;
        return acc;
      }, {}),
    ).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—";

    return { credentials: credentials.length, uniqueIps, topProto };
  }, [events]);

  return (
    <div className="flex flex-col h-full relative z-10">
      {/* Header */}
      <header className="px-6 py-3 border-b border-blue-900/50 bg-[#020814] flex items-center gap-4">
        <div className="flex items-center gap-3">
          {/* Buoy icon */}
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            className="shrink-0"
          >
            <circle cx="14" cy="14" r="12" stroke="#22d3ee" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="6" stroke="#3b82f6" strokeWidth="1" />
            <line x1="14" y1="2" x2="14" y2="8" stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="14" y1="20" x2="14" y2="26" stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="2" y1="14" x2="8" y2="14" stroke="#22d3ee" strokeWidth="1.5" />
            <line x1="20" y1="14" x2="26" y2="14" stroke="#22d3ee" strokeWidth="1.5" />
            <circle cx="14" cy="14" r="2" fill="#22d3ee" />
          </svg>
          <div>
            <h1 className="text-sm font-mono font-bold text-cyan-400 tracking-widest uppercase leading-none">
              Network Buoy
            </h1>
            <p className="text-xs font-mono text-blue-700 leading-none mt-0.5">
              Threat Intelligence Monitor
            </p>
          </div>
        </div>
        <div className="flex-1" />
        <div className="font-mono text-xs text-blue-700 tracking-widest">
          {new Date().toUTCString().split(" ").slice(0, 4).join(" ")} UTC
        </div>
      </header>

      {/* Status bar */}
      <StatusBar status={status} events={events} />

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-3 px-4 py-3 border-b border-blue-900/30">
        <StatCard
          label="Total Events"
          value={events.length}
          sub="since session start"
          accent="cyan"
        />
        <StatCard
          label="Credentials Captured"
          value={stats.credentials}
          sub="unique auth attempts"
          accent="red"
        />
        <StatCard
          label="Unique Attackers"
          value={stats.uniqueIps}
          sub="distinct source IPs"
          accent="yellow"
        />
        <StatCard
          label="Top Protocol"
          value={stats.topProto}
          sub="most targeted service"
          accent="green"
        />
      </div>

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-12 gap-3 p-4 overflow-hidden min-h-0">
        {/* Left: event feed (tall) */}
        <div className="col-span-5 overflow-hidden flex flex-col min-h-0">
          <EventFeed events={events} />
        </div>

        {/* Right: charts stacked */}
        <div className="col-span-7 grid grid-rows-3 gap-3 min-h-0">
          <div className="row-span-1 min-h-0">
            <ProtocolChart events={events} />
          </div>
          <div className="row-span-1 min-h-0">
            <TopAttackers events={events} />
          </div>
          <div className="row-span-1 min-h-0">
            <CredentialTable events={events} />
          </div>
        </div>
      </div>
    </div>
  );
}
