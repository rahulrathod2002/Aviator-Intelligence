import { StatCard } from "./components/StatCard";
import { useCaptureStream } from "./hooks/useCaptureStream";

function formatMultiplier(value: number | null | undefined) {
  return value == null ? "--" : `${value.toFixed(2)}x`;
}

export default function App() {
  const { payload, connection } = useCaptureStream();

  const liveValue =
    payload?.state === "CRASHED"
      ? payload?.previous_round.multiplier ?? payload.multiplier
      : payload?.current_round.multiplier ?? payload?.multiplier;

  const sourceTone =
    payload?.source === "Connected via ADB"
      ? "signal"
      : payload?.source === "Connected via Browser"
        ? "default"
        : "warn";

  return (
    <main className="min-h-screen bg-ink text-stone-100">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 py-6 lg:px-8">
        <header className="grid gap-4 rounded-[2rem] border border-white/10 bg-white/5 p-5 shadow-panel backdrop-blur md:grid-cols-[1fr_auto]">
          <div>
            <p className="font-display text-sm uppercase tracking-[0.35em] text-accent">Aviator Intelligence</p>
            <h1 className="mt-2 max-w-2xl font-display text-4xl leading-none text-panel">
              Production telemetry for real-time round state, source failover, and probability analytics.
            </h1>
            <p className="mt-3 max-w-3xl text-sm text-stone-300">
              Probability output is statistical only. It never represents a deterministic prediction.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 md:items-end">
            <span className="rounded-full border border-white/15 bg-black/20 px-4 py-2 text-xs uppercase tracking-[0.3em] text-stone-300">
              WebSocket {connection}
            </span>
            <span className="rounded-full border border-white/15 bg-black/20 px-4 py-2 text-xs uppercase tracking-[0.3em] text-stone-300">
              {payload?.source ?? "No Signal"}
            </span>
          </div>
        </header>

        <section className="mt-6 grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="grid gap-6">
            <div className="grid gap-6 md:grid-cols-2">
              <article className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-gradient-to-br from-white/10 via-white/5 to-transparent p-6">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-400">Live Round</p>
                <div className="mt-6 flex items-end gap-3">
                  <span className={`font-display text-7xl leading-none ${payload?.state === "CRASHED" ? "text-warn" : "text-panel"}`}>
                    {formatMultiplier(liveValue)}
                  </span>
                </div>
                <div className="mt-6 flex flex-wrap gap-3 text-xs uppercase tracking-[0.25em] text-stone-300">
                  <span className="rounded-full border border-white/10 bg-black/15 px-3 py-2">{payload?.state ?? "WAITING"}</span>
                  <span className="rounded-full border border-white/10 bg-black/15 px-3 py-2">
                    OCR {payload ? `${Math.round(payload.confidence * 100)}%` : "--"}
                  </span>
                </div>
              </article>

              <article className="rounded-[2rem] border border-white/10 bg-panel p-6 text-ink">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.3em] text-muted">Next Probability</p>
                  <span className="rounded-full bg-ink px-3 py-1 text-[10px] uppercase tracking-[0.25em] text-panel">
                    Probability
                  </span>
                </div>
                <p className="mt-5 font-display text-6xl leading-none text-signal">
                  {payload ? `${Math.round(payload.next_round.probability_score * 100)}%` : "--"}
                </p>
                <p className="mt-4 text-sm text-muted">{payload?.next_round.label ?? "Awaiting historical data."}</p>
                <p className="mt-3 text-xs uppercase tracking-[0.25em] text-muted">
                  Confidence {payload ? `${Math.round(payload.next_round.confidence * 100)}%` : "--"}
                </p>
              </article>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <StatCard
                label="Last Result"
                value={formatMultiplier(payload?.previous_round.multiplier)}
                hint={payload?.previous_round.state ?? "CRASHED"}
                tone="warn"
              />
              <StatCard
                label="Current Source"
                value={payload?.source ?? "No Signal"}
                hint={payload?.status ?? "NO_SIGNAL"}
                tone={sourceTone}
              />
              <StatCard
                label="OCR Engine"
                value={payload?.ocr.engine ?? "unknown"}
                hint={payload?.ocr.raw_text || "No OCR sample"}
              />
            </div>

            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <div className="flex items-center justify-between">
                <p className="text-xs uppercase tracking-[0.3em] text-stone-400">Recent Crashes</p>
                <p className="text-xs uppercase tracking-[0.25em] text-stone-500">Backend CSV history</p>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                {(payload?.recent_rounds ?? []).slice().reverse().map((round) => (
                  <div
                    key={round.round_id}
                    className={`rounded-full border px-4 py-2 font-mono text-sm ${
                      round.multiplier >= 10
                        ? "border-accent/40 bg-accent/10 text-accent"
                        : round.multiplier >= 2
                          ? "border-signal/40 bg-signal/10 text-green-200"
                          : "border-warn/40 bg-warn/10 text-red-200"
                    }`}
                  >
                    {round.multiplier.toFixed(2)}x
                  </div>
                ))}
              </div>
            </div>
          </div>

          <aside className="grid gap-4">
            <StatCard
              label="Rolling Median"
              value={payload ? `${payload.next_round.rolling_median.toFixed(2)}x` : "--"}
              hint="Median of recent crashed rounds"
            />
            <StatCard
              label="Volatility Index"
              value={payload ? payload.next_round.volatility_index.toFixed(2) : "--"}
              hint="Standard deviation window"
              tone={payload && payload.next_round.volatility_index > 6 ? "warn" : "default"}
            />
            <StatCard label="Low Streak" value={payload ? `${payload.next_round.low_streak}` : "--"} hint="Consecutive rounds below 2x" />
            <StatCard label="High Streak" value={payload ? `${payload.next_round.high_streak}` : "--"} hint="Consecutive rounds at or above 10x" />
            <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6">
              <p className="text-xs uppercase tracking-[0.3em] text-stone-400">Distribution Buckets</p>
              <div className="mt-4 grid gap-3">
                {Object.entries(payload?.next_round.buckets ?? {}).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between rounded-2xl bg-black/15 px-4 py-3 text-sm text-stone-200">
                    <span>{key}</span>
                    <span className="font-mono">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}
