import { useEffect, useMemo, useRef, useState } from "react";
import type { StreamPayload } from "../types";

const SOCKET_URL = "ws://localhost:8765";

type StreamState = {
  payload: StreamPayload | null;
  connection: "connecting" | "live" | "offline";
};

export function useCaptureStream() {
  const [state, setState] = useState<StreamState>({
    payload: null,
    connection: "connecting"
  });
  const retryRef = useRef<number>();
  const delayRef = useRef(1000);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;

    const connect = () => {
      socket = new WebSocket(SOCKET_URL);
      socket.onopen = () => {
        if (!active) return;
        delayRef.current = 1000;
        setState((current) => ({ ...current, connection: "live" }));
      };
      socket.onmessage = (event) => {
        if (!active) return;
        const payload = JSON.parse(event.data) as StreamPayload;
        setState({ payload, connection: "live" });
      };
      socket.onerror = () => {
        if (!active) return;
        setState((current) => ({ ...current, connection: "offline" }));
      };
      socket.onclose = () => {
        if (!active) return;
        setState((current) => ({ ...current, connection: "offline" }));
        const delay = delayRef.current;
        delayRef.current = Math.min(delay * 1.5, 5000);
        retryRef.current = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      active = false;
      if (retryRef.current) window.clearTimeout(retryRef.current);
      socket?.close();
    };
  }, []);

  return useMemo(() => state, [state]);
}
