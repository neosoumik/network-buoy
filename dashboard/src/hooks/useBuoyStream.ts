"use client";

import { useEffect, useRef, useState } from "react";
import type { BuoyEvent } from "@/lib/types";

const MAX_EVENTS = 500;

export type StreamStatus = "connecting" | "connected" | "disconnected";

export function useBuoyStream() {
  const [events, setEvents] = useState<BuoyEvent[]>([]);
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;

    async function connect() {
      if (!mountedRef.current) return;

      try {
        const res = await fetch("/api/config");
        const { wsUrl } = (await res.json()) as { wsUrl: string };

        if (!mountedRef.current) return;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        setStatus("connecting");

        ws.onopen = () => {
          if (mountedRef.current) setStatus("connected");
        };

        ws.onmessage = (ev: MessageEvent<string>) => {
          if (!mountedRef.current) return;
          try {
            const event = JSON.parse(ev.data) as BuoyEvent;
            setEvents((prev) => {
              const next = [event, ...prev];
              return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
            });
          } catch {
            // malformed frame — ignore
          }
        };

        ws.onclose = () => {
          if (!mountedRef.current) return;
          setStatus("disconnected");
          // exponential backoff retry, capped at 10s
          retryRef.current = setTimeout(connect, Math.min(10000, 2000));
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        if (!mountedRef.current) return;
        setStatus("disconnected");
        retryRef.current = setTimeout(connect, 3000);
      }
    }

    void connect();

    return () => {
      mountedRef.current = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { events, status };
}
