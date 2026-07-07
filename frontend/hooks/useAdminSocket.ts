"use client";

import { useEffect } from "react";
import { WS_URL } from "@/lib/api";
import { useAdminStore } from "@/store/admin";

export function useAdminSocket() {
  const addEvent = useAdminStore((s) => s.addEvent);
  const setConnected = useAdminStore((s) => s.setConnected);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry: ReturnType<typeof setTimeout>;

    const connect = () => {
      ws = new WebSocket(`${WS_URL}/ws/admin`);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (msg) => addEvent(JSON.parse(msg.data));
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = setTimeout(connect, 2000);
      };
    };
    connect();

    return () => {
      closed = true;
      clearTimeout(retry);
      ws?.close();
    };
  }, [addEvent, setConnected]);
}
