export type RoundState = "WAITING" | "FLYING" | "CRASHED";

export type RoundView = {
  round_id: string;
  state: RoundState;
  multiplier: number | null;
  timestamp: string | null;
  source: string | null;
};

export type ProbabilityView = {
  label: string;
  probability_score: number;
  confidence: number;
  rolling_median: number;
  volatility_index: number;
  low_streak: number;
  high_streak: number;
  buckets: Record<string, number>;
};

export type RecentRound = {
  timestamp: string;
  round_id: string;
  multiplier: number;
  state: RoundState;
  source: string;
};

export type StreamPayload = {
  status: "LIVE" | "NO_SIGNAL";
  source: "Connected via ADB" | "Connected via Browser" | "No Signal";
  state: RoundState;
  multiplier: number | null;
  confidence: number;
  current_round: RoundView;
  previous_round: RoundView;
  next_round: ProbabilityView;
  recent_rounds: RecentRound[];
  ocr: {
    raw_text: string;
    engine: string;
    color: string;
  };
};
