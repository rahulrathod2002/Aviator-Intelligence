import { StatCard } from "./components/StatCard";
import { useCaptureStream } from "./hooks/useCaptureStream";

export default function App() {
  const { points, analytics, status, ocrDebug } = useCaptureStream();
  const currentPoint = points.length ? points[points.length - 1] : null;
  const latest = currentPoint?.value;
  const gameState = currentPoint?.state ?? "idle";
  const finalResult = gameState === "crashed" && currentPoint?.roundMax ? currentPoint.roundMax : latest;

  return (
    <main className="h-screen flex flex-col bg-[#0a0a0c] text-slate-200 overflow-hidden font-sans selection:bg-purple-500/30">
      <header className="flex-none p-3 lg:p-4 flex flex-col md:flex-row items-center justify-between gap-4 border-b border-white/5 bg-white/[0.02] backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <span className="text-white font-bold text-xl">A</span>
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
              Aviator Intelligence <span className="text-xs font-mono text-purple-500 ml-1">v2.1</span>
            </h1>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`w-1.5 h-1.5 rounded-full ${status === "live" ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
              <p className="text-[10px] uppercase tracking-widest text-slate-500 font-medium">
                Stream: {status} | {gameState.toUpperCase()}
              </p>
            </div>
          </div>
        </div>
        <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500 bg-white/5 px-3 py-2 rounded-full">
          Local analytics only
        </div>
      </header>

      <div className="flex-1 min-h-0 p-3 lg:p-4 grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-4">
        <div className="flex flex-col gap-4 min-h-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-none">
            <div
              className={`relative overflow-hidden rounded-3xl p-6 transition-all duration-500 border ${
                gameState === "flying"
                  ? "bg-purple-600/10 border-purple-500/30 glow-purple shadow-[0_0_40px_-10px_rgba(168,85,247,0.2)] animate-pulse-subtle"
                  : gameState === "crashed"
                    ? "bg-red-600/10 border-red-500/30 glow-red"
                    : "bg-white/[0.03] border-white/10"
              }`}
            >
              <div className="relative z-10">
                <div className="flex justify-between items-start mb-2">
                  <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Live Multiplier</p>
                  {gameState === "crashed" && (
                    <span className="text-[10px] font-black text-red-500 uppercase tracking-widest bg-red-500/10 px-2 py-0.5 rounded animate-bounce">
                      FLEW AWAY
                    </span>
                  )}
                </div>
                <div className="flex items-baseline gap-2">
                  <span
                    className={`text-6xl font-black font-mono tracking-tighter transition-colors duration-300 ${
                      gameState === "crashed" ? "text-red-500" : "text-white"
                    }`}
                  >
                    {finalResult !== undefined ? finalResult.toFixed(2) : "0.00"}
                  </span>
                  <span
                    className={`text-2xl font-bold transition-colors duration-300 ${
                      gameState === "crashed" ? "text-red-500/50" : "text-slate-600"
                    }`}
                  >
                    x
                  </span>
                </div>
                {currentPoint?.roundMax && currentPoint.roundMax > 1 && (
                  <p className="mt-2 text-xs text-slate-400">
                    Round Result:{" "}
                    <span className={`font-mono font-bold ${gameState === "crashed" ? "text-red-400" : "text-white"}`}>
                      {currentPoint.roundMax.toFixed(2)}x
                    </span>
                  </p>
                )}
              </div>
              {gameState === "flying" && (
                <div className="absolute inset-0 bg-gradient-to-tr from-purple-600/20 to-transparent animate-pulse" />
              )}
            </div>

            <div className="rounded-3xl p-6 border bg-white/[0.03] border-white/10">
              <div className="flex items-center justify-between mb-2">
                <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500 font-bold">Next Round Signal</p>
                <span className="px-2 py-0.5 rounded-full text-[8px] font-bold uppercase tracking-widest bg-white/10 text-slate-400">
                  Probabilistic
                </span>
              </div>
              <div className="min-h-[80px]">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg font-bold text-emerald-400">
                    {analytics ? `${Math.round(analytics.probAbove2x * 100)}% ≥ 2x` : "--"}
                  </span>
                  <span className="text-slate-500 text-xs">based on last 100</span>
                </div>
                <p className="text-sm text-slate-300 leading-relaxed">
                  {analytics
                    ? `Range (P25–P90): ${analytics.p25.toFixed(2)}x–${analytics.p90.toFixed(2)}x`
                    : "Awaiting enough rounds."}
                </p>
                <p className="mt-2 text-[10px] text-slate-500">
                  Signal is statistical, not a guaranteed prediction.
                </p>
              </div>
            </div>
          </div>

          <div className="flex-1 min-h-0 bg-white/[0.02] border border-white/5 rounded-3xl overflow-hidden relative p-4">
            <span className="text-[10px] uppercase tracking-widest text-slate-600 font-bold bg-black/40 px-2 py-1 rounded backdrop-blur-sm">
              Real-time Telemetry
            </span>
            <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-slate-400">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <p className="uppercase tracking-widest text-[10px] text-slate-500">Current State</p>
                <p className="mt-2 text-sm font-bold text-white">{gameState.toUpperCase()}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                <p className="uppercase tracking-widest text-[10px] text-slate-500">OCR Confidence</p>
                <p className="mt-2 text-sm font-bold text-white">
                  {ocrDebug ? `${Math.round(ocrDebug.confidence * 100)}%` : "--"}
                </p>
              </div>
            </div>
          </div>
        </div>

        <aside className="flex flex-col gap-3 min-h-0">
          <div className="flex-1 overflow-y-auto no-scrollbar grid grid-cols-2 lg:grid-cols-1 gap-3 pr-1">
            <StatCard
              label="Rolling Median (50)"
              value={analytics ? `${analytics.rollingMedian50.toFixed(2)}x` : "0.00x"}
              hint="Median of last 50"
              tone="default"
            />
            <StatCard
              label="Rolling Median (100)"
              value={analytics ? `${analytics.rollingMedian100.toFixed(2)}x` : "0.00x"}
              hint="Median of last 100"
              tone="default"
            />
            <StatCard
              label="Volatility"
              value={analytics?.volatilityPhase.toUpperCase() ?? "STABLE"}
              hint="Current market phase"
              tone={analytics?.volatilityPhase === "chaotic" ? "warn" : "default"}
            />
            <StatCard
              label="Low Streak"
              value={analytics ? `${analytics.streakLow}` : "--"}
              hint="Under 2x"
            />
            <StatCard
              label="High Streak"
              value={analytics ? `${analytics.streakHigh}` : "--"}
              hint="Above 5x"
            />

            <div className="lg:col-span-1 col-span-2 rounded-2xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-500 mb-3">Recent Rounds</p>
              <div className="flex flex-wrap gap-2">
                {points
                  .filter((p) => p.state === "crashed")
                  .slice(-8)
                  .reverse()
                  .map((p, i) => (
                    <span
                      key={i}
                      className={`px-2 py-1 rounded-md font-mono text-xs font-bold ${
                        p.value >= 10
                          ? "bg-pink-500/20 text-pink-400 border border-pink-500/30"
                          : p.value >= 2
                            ? "bg-purple-500/20 text-purple-400 border border-purple-500/30"
                            : "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      }`}
                    >
                      {p.value.toFixed(2)}x
                    </span>
                  ))}
                {points.filter((p) => p.state === "crashed").length === 0 && (
                  <p className="text-[10px] text-slate-600 italic">No history yet</p>
                )}
              </div>
            </div>

            <StatCard
              label="OCR Intelligence"
              value={ocrDebug?.engine?.split("_")[0].toUpperCase() ?? "AUTO"}
              hint={`Conf: ${ocrDebug ? Math.round(ocrDebug.confidence * 100) : 0}%`}
            >
              <div className="mt-2 p-2 bg-black/40 rounded-lg border border-white/5 font-mono text-[10px] text-purple-400 truncate">
                {ocrDebug?.rawText || "NO_DATA"}
              </div>
            </StatCard>
          </div>

          <div className="flex-none p-4 rounded-3xl bg-gradient-to-br from-white/[0.05] to-transparent border border-white/10">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-tighter font-bold text-slate-500 mb-2">
              <span>System Health</span>
              <span>100% Operational</span>
            </div>
            <div className="h-1 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-purple-500 to-pink-500" />
            </div>
            <p className="mt-3 text-[9px] text-slate-600 leading-tight">
              Signals are probabilistic. Accuracy depends on stream quality and OCR confidence.
            </p>
          </div>
        </aside>
      </div>
    </main>
  );
}
