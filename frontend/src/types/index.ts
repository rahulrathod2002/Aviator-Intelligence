export type GameState = "idle" | "waiting" | "flying" | "crashed";

export type MultiplierPoint = {
  value: number;
  timestamp: number;
  confidence: number;
  smoothed: number;
  isOutlier: boolean;
  state?: GameState;
  roundMax?: number;
};

export type OcrDebug = {
  rawText: string;
  confidence: number;
  roi?: { x: number; y: number; w: number; h: number };
  timestamp: number;
  engine?: string;
};

export type AnalyticsSnapshot = {
  rollingMedian50: number;
  rollingMedian100: number;
  volatility: number;
  streakLow: number;
  streakHigh: number;
  momentum: "rising" | "falling" | "flat";
  buckets: Record<string, number>;
  outlierCount: number;
  volatilityPhase: "stable" | "volatile" | "chaotic";
};

export type AiInsight = {
  signal_strength: "low" | "medium" | "high";
  market_phase?: "stable" | "volatile" | "chaotic";
  insight: string;
  confidence: number;
  range_estimate?: [number, number];
  next_round_prob?: string;
};
