import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string;
  hint: string;
  tone?: "default" | "signal" | "warn";
  children?: ReactNode;
}

export function StatCard({ label, value, hint, tone = "default", children }: StatCardProps) {
  const toneClasses =
    tone === "signal"
      ? "border-signal/40 bg-signal/10 text-green-200"
      : tone === "warn"
        ? "border-warn/40 bg-warn/10 text-red-200"
        : "border-white/10 bg-white/5 text-stone-300";

  return (
    <section className={`rounded-[2rem] border ${toneClasses} p-5 transition-colors duration-300`}>
      <p className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-70">{label}</p>
      <div className="mt-2 flex items-baseline gap-1.5">
        <p
          className={`font-display text-3xl font-black tracking-tight ${
            tone === "signal" ? "text-green-100" : tone === "warn" ? "text-red-100" : "text-panel"
          }`}
        >
          {value}
        </p>
      </div>
      <p className="mt-2 text-[10px] uppercase tracking-widest font-medium opacity-50">{hint}</p>
      {children}
    </section>
  );
}
