import type { AnalyticsSnapshot, MultiplierPoint } from "../types";

function median(values: number[]) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

function stdDev(values: number[]) {
  if (values.length < 2) return 0;
  const avg = values.reduce((sum, v) => sum + v, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + (v - avg) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function iqrFilter(values: number[]) {
  if (values.length < 4) return { filtered: values, outliers: 0 };
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const low = q1 - 1.5 * iqr;
  const high = q3 + 1.5 * iqr;
  const filtered = values.filter((v) => v >= low && v <= high);
  return { filtered, outliers: values.length - filtered.length };
}

export function markOutliers(values: number[]) {
  if (values.length < 4) return values.map(() => false);
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  const iqr = q3 - q1;
  const low = q1 - 1.5 * iqr;
  const high = q3 + 1.5 * iqr;
  return values.map((v) => v < low || v > high);
}

function buckets(values: number[]) {
  return values.reduce(
    (acc, value) => {
      if (value < 2) acc["1-2x"] += 1;
      else if (value < 5) acc["2-5x"] += 1;
      else if (value < 10) acc["5-10x"] += 1;
      else acc["10x+"] += 1;
      return acc;
    },
    { "1-2x": 0, "2-5x": 0, "5-10x": 0, "10x+": 0 }
  );
}

function percentile(values: number[], p: number) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.round((p / 100) * (sorted.length - 1))));
  return sorted[idx];
}

export function computeAnalytics(points: MultiplierPoint[]): AnalyticsSnapshot {
  const values = points.map((p) => p.smoothed);
  const { filtered, outliers } = iqrFilter(values);
  const rollingMedian50 = median(filtered.slice(-50));
  const rollingMedian100 = median(filtered.slice(-100));
  const volatility = stdDev(filtered.slice(-100));
  const streakLow = streak(points, (p) => p.smoothed < 2);
  const streakHigh = streak(points, (p) => p.smoothed > 5);
  const momentum = rollingMedian50 > rollingMedian100 + 0.1 ? "rising" : rollingMedian50 < rollingMedian100 - 0.1 ? "falling" : "flat";
  const volatilityPhase = volatility < 2 ? "stable" : volatility < 6 ? "volatile" : "chaotic";
  const lastWindow = filtered.slice(-100);
  const probAbove2x = lastWindow.length ? lastWindow.filter((v) => v >= 2).length / lastWindow.length : 0;
  const p25 = percentile(lastWindow, 25);
  const p50 = percentile(lastWindow, 50);
  const p75 = percentile(lastWindow, 75);
  const p90 = percentile(lastWindow, 90);

  return {
    rollingMedian50,
    rollingMedian100,
    volatility,
    streakLow,
    streakHigh,
    momentum,
    buckets: buckets(filtered),
    outlierCount: outliers,
    volatilityPhase,
    probAbove2x,
    p25,
    p50,
    p75,
    p90
  };
}

function streak(points: MultiplierPoint[], predicate: (p: MultiplierPoint) => boolean) {
  let count = 0;
  for (let i = points.length - 1; i >= 0; i -= 1) {
    if (!predicate(points[i])) break;
    count += 1;
  }
  return count;
}
