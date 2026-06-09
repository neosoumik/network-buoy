"use client";

type Props = {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "cyan" | "red" | "yellow" | "green";
};

const ACCENT: Record<NonNullable<Props["accent"]>, string> = {
  cyan: "text-cyan-400 drop-shadow-[0_0_8px_#22d3ee]",
  red: "text-red-400 drop-shadow-[0_0_8px_#f87171]",
  yellow: "text-yellow-400 drop-shadow-[0_0_8px_#facc15]",
  green: "text-green-400 drop-shadow-[0_0_8px_#4ade80]",
};

export function StatCard({ label, value, sub, accent = "cyan" }: Props) {
  return (
    <div className="border border-blue-900/60 bg-[#030d1a] rounded p-4 flex flex-col gap-1">
      <span className="text-blue-500 text-xs font-mono uppercase tracking-widest">{label}</span>
      <span className={`text-3xl font-mono font-bold ${ACCENT[accent]}`}>{value}</span>
      {sub && <span className="text-blue-600 text-xs font-mono">{sub}</span>}
    </div>
  );
}
