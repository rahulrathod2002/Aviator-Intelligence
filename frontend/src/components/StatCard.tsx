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
    tone === "signal" ? "border-purple-500/30 bg-purple-500/5 text-purple-400" : 
    tone === "warn" ? "border-red-500/30 bg-red-500/5 text-red-400" : 
    "border-white/10 bg-white/[0.02] text-slate-400";

  return (
    <section className={`rounded-2xl border ${toneClasses} p-4 transition-all duration-300 hover:bg-white/[0.05]`}>
      <p className="text-[10px] uppercase tracking-[0.2em] font-bold opacity-60">{label}</p>
      <div className="flex items-baseline gap-1.5 mt-2">
        <p className={`font-mono text-2xl font-black tracking-tight ${
          tone === 'signal' ? 'text-purple-400' : 
          tone === 'warn' ? 'text-red-400' : 'text-white'
        }`}>
          {value}
        </p>
      </div>
      <p className="mt-1 text-[9px] uppercase tracking-widest font-medium opacity-40">{hint}</p>
      {children}
    </section>
  );
}
