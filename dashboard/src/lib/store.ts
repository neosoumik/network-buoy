import type { BuoyEvent } from "@/lib/types";

const MAX_EVENTS = 500;

// Module-level singleton — survives across route handler invocations in the
// same Node.js process (Next.js reuses the module between requests).
const events: BuoyEvent[] = [];
const subscribers = new Set<(ev: BuoyEvent) => void>();

export function push(ev: BuoyEvent): void {
  events.unshift(ev);
  if (events.length > MAX_EVENTS) events.length = MAX_EVENTS;
  for (const cb of subscribers) cb(ev);
}

export function snapshot(): BuoyEvent[] {
  return [...events];
}

export function subscribe(cb: (ev: BuoyEvent) => void): () => void {
  subscribers.add(cb);
  return () => subscribers.delete(cb);
}
