"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { DisplayEvent, BuoyEvent } from "@/lib/types";
import { normalize } from "@/lib/normalize";

const MAX_EVENTS = 500;

export type StreamStatus = "connecting" | "connected" | "disconnected";

export function useEventStream() {
  const [events, setEvents] = useState<DisplayEvent[]>([]);
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const esRef = useRef<EventSource | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const retryDelay = useRef(1000);
  const connectRef = useRef<() => void>(() => {});

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    esRef.current?.close();
    if (retryRef.current) clearTimeout(retryRef.current);

    const es = new EventSource("/api/events");
    esRef.current = es;
    setStatus("connecting");

    es.onopen = () => {
      if (mountedRef.current) {
        setStatus("connected");
        retryDelay.current = 1000;
      }
    };

    es.onmessage = (ev: MessageEvent<string>) => {
      if (!mountedRef.current) return;
      try {
        const raw = JSON.parse(ev.data) as BuoyEvent;
        const display = normalize(raw);
        setEvents((prev) => {
          const next = [display, ...prev];
          return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
        });
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      es.close();
      if (!mountedRef.current) return;
      setStatus("disconnected");
      retryDelay.current = Math.min(retryDelay.current * 2, 10_000);
      retryRef.current = setTimeout(() => connectRef.current(), retryDelay.current);
    };
  }, []);

  // Keep connectRef in sync without triggering a render cycle
  useLayoutEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  const reconnect = useCallback(() => {
    setEvents([]);
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      esRef.current?.close();
    };
  }, [connect]);

  return { events, status, reconnect };
}
