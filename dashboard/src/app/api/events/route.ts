import { NextResponse } from "next/server";
import { snapshot, subscribe } from "@/lib/store";
import type { BuoyEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

function encode(ev: BuoyEvent): string {
  return `data: ${JSON.stringify(ev)}\n\n`;
}

export async function GET(): Promise<NextResponse> {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const enc = new TextEncoder();

      for (const ev of snapshot().toReversed()) {
        controller.enqueue(enc.encode(encode(ev)));
      }

      const unsub = subscribe((ev) => {
        try {
          controller.enqueue(enc.encode(encode(ev)));
        } catch {
          unsub();
        }
      });

      const interval = setInterval(() => {
        try {
          controller.enqueue(enc.encode(": heartbeat\n\n"));
        } catch {
          clearInterval(interval);
          unsub();
        }
      }, 15_000);
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
