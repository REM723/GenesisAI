"use client";

import { useEffect, useState } from "react";

import { api } from "./api";

export type RunEvent = {
  type: string; // start | complete | timeout | run_succeeded | run_failed | run_timeout
  run_id: string;
  agent?: string;
  status?: string;
  output?: string;
};

// EventSource cannot send an Authorization header, so we read the SSE body via fetch.
export function useRunStream(runId: string | null, token: string | null) {
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [finished, setFinished] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !token) return;
    setEvents([]);
    setFinished(null);
    const controller = new AbortController();

    (async () => {
      const res = await fetch(api.streamUrl(runId), {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      if (!res.body) return;
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const event = JSON.parse(line.slice(5).trim()) as RunEvent;
          setEvents((prev) => [...prev, event]);
          if (event.type.startsWith("run_")) setFinished(event.status ?? event.type);
        }
      }
    })().catch(() => {
      /* aborted or network closed; state already reflects last event */
    });

    return () => controller.abort();
  }, [runId, token]);

  return { events, finished };
}
