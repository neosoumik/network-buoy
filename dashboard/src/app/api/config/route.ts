import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  // BUOY_WS_URL is a server-side env var; we expose only what the browser needs.
  // Default falls back to localhost for local dev without Docker.
  const wsUrl = process.env.BUOY_WS_URL ?? "ws://localhost:4444";
  return NextResponse.json({ wsUrl });
}
