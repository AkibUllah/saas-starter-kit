import { limitLabel, usagePercent } from "@/lib/utils";

export function UsageMeter({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = usagePercent(used, limit);
  const full = limit !== -1 && used >= limit;
  return (
    <div data-testid={`usage-${label}`}>
      <div className="flex items-baseline justify-between text-sm">
        <span className="capitalize">{label.replace("_", " ")}</span>
        <span className="tabular-nums text-slate-500">
          {used} / {limitLabel(limit)}
        </span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className={full ? "h-full bg-rose-500" : "h-full bg-brand-500"} style={{ width: `${limit === -1 ? 8 : pct}%` }} />
      </div>
    </div>
  );
}
