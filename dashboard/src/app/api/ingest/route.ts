import { NextRequest, NextResponse } from "next/server";
import { push } from "@/lib/store";
import type { BuoyEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

function unauthorized() {
  return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
}

function badRequest(msg: string) {
  return NextResponse.json({ error: msg }, { status: 400 });
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const apiToken = process.env.API_TOKEN;
  if (apiToken) {
    const auth = req.headers.get("authorization") ?? "";
    const token = auth.startsWith("ApiToken ") ? auth.slice(9) : "";
    if (token !== apiToken) return unauthorized();
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return badRequest("Invalid JSON");
  }

  const events: BuoyEvent[] = Array.isArray(body)
    ? (body as BuoyEvent[])
    : [body as BuoyEvent];

  if (events.length === 0) return badRequest("Empty payload");

  for (const ev of events) {
    if (!ev.EventTime || !ev.EventType) {
      return badRequest("Each event must have EventTime and EventType");
    }
    push(ev);
  }

  return NextResponse.json({ ingested: events.length });
}
