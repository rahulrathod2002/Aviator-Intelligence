import { useEffect, useMemo, useRef, useState } from "react";
import type { AnalyticsSnapshot, AiInsight, MultiplierPoint, OcrDebug } from "../types";
import { computeAnalytics, markOutliers } from "../lib/analytics";
import { loadRecentPoints, storePoints } from "../lib/storage";

const WS_URL = "ws://localhost:8765";
const MAX_POINTS = 300;

type StreamState = {
  points: MultiplierPoint[];
  analytics: AnalyticsSnapshot | null;
  aiInsight: AiInsight | null;
  aiStatus: "idle" | "missing_key" | "error" | "waiting" | "live";
  status: "connecting" | "live" | "offline";
  ocrDebug: OcrDebug | null;
  roundsCount?: { count: number; required: number };
};

export function useCaptureStream() {
  const [state, setState] = useState<StreamState>({
    points: [],
    analytics: null,
    aiInsight: null,
    aiStatus: "idle",
    status: "connecting",
    ocrDebug: null,
    roundsCount: { count: 0, required: 5 }
  });
  const retryRef = useRef<number>();
  const retryDelayRef = useRef(800);
  const socketRef = useRef<WebSocket | null>(null);
  const pendingKeyRef = useRef<string | null>(null);
  const lastAiAtRef = useRef<number | null>(null);
  const [lastAiAt, setLastAiAt] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;

    loadRecentPoints(MAX_POINTS)
      .then((points) => {
        if (!active) return;
        const normalized: MultiplierPoint[] = points.map((p) => ({
          value: p.value,
          smoothed: p.value,
          timestamp: p.timestamp,
          confidence: p.confidence,
          isOutlier: false
        }));
        const outliers = markOutliers(normalized.map((p) => p.value));
        const withOutliers = normalized.map((p, index) => ({ ...p, isOutlier: outliers[index] }));
        setState((current) => ({
          ...current,
          points: withOutliers,
          analytics: computeAnalytics(withOutliers)
        }));
      })
      .catch(() => {
        if (active) {
          setState((current) => ({ ...current, status: "offline" }));
        }
      });

    const connect = () => {
      socket = new WebSocket(WS_URL);
      socketRef.current = socket;
      socket.onopen = () => {
        if (!active) return;
        retryDelayRef.current = 800;
        setState((current) => ({ ...current, status: "live" }));
        if (pendingKeyRef.current) {
          socket?.send(JSON.stringify({ type: "groq_key", key: pendingKeyRef.current }));
        }
      };
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === "rounds_count") {
          setState((current) => ({ ...current, roundsCount: { count: payload.count, required: payload.required } }));
          return;
        }
        if (payload.type === "ai_insight" && payload.value) {
          lastAiAtRef.current = payload.timestamp ?? Date.now();
          setLastAiAt(lastAiAtRef.current);
          setState((current) => ({ ...current, aiInsight: payload.value as AiInsight, aiStatus: "live" }));
          return;
        }
        if (payload.type !== "multiplier") return;
        const nextPoint: MultiplierPoint = {
          value: payload.value,
          smoothed: payload.value,
          timestamp: payload.timestamp,
          confidence: payload.confidence,
          isOutlier: false,
          state: payload.state,
          roundMax: payload.roundMax
        };

        setState((current) => {
          const points = [...current.points, nextPoint].slice(-MAX_POINTS);
          const outliers = markOutliers(points.map((p) => p.value));
          const withOutliers = points.map((p, index) => ({ ...p, isOutlier: outliers[index] }));
          const analytics = computeAnalytics(withOutliers);
          const ocrDebug: OcrDebug | null = payload.rawText
            ? {
              rawText: payload.rawText,
              confidence: payload.confidence,
              roi: payload.roi ?? null,
              timestamp: payload.timestamp,
              engine: payload.engine
            }
            : current.ocrDebug;
          return { ...current, points: withOutliers, analytics, status: "live", ocrDebug };
        });

        storePoints([{ timestamp: payload.timestamp, value: payload.value, confidence: payload.confidence }]);

      };
      socket.onerror = () => {
        if (!active) return;
        setState((current) => ({ ...current, status: "offline" }));
      };
      socket.onclose = () => {
        if (!active) return;
        setState((current) => ({ ...current, status: "offline" }));
        const delay = retryDelayRef.current;
        retryDelayRef.current = Math.min(delay * 1.4, 5000);
        retryRef.current = window.setTimeout(connect, delay);
      };
    };

    retryRef.current = window.setTimeout(connect, 300);

    return () => {
      active = false;
      if (retryRef.current) window.clearTimeout(retryRef.current);
      socket?.close();
    };
  }, []);

  const sendGroqKey = (key: string) => {
    const trimmed = key.trim();
    pendingKeyRef.current = trimmed || null;
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: "groq_key", key: trimmed }));
    }
    setState((current) => ({
      ...current,
      aiStatus: trimmed ? "waiting" : "missing_key"
    }));
  };

  return useMemo(() => ({ ...state, sendGroqKey, lastAiAt }), [state, lastAiAt]);
}
