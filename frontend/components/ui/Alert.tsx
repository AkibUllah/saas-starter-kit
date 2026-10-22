import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import { cn } from "@/lib/utils";

type Kind = "info" | "success" | "error";
const STYLES: Record<Kind, string> = {
  info: "border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-900 dark:bg-brand-950/50 dark:text-brand-100",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-100",
  error: "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-100",
};
const ICONS = { info: Info, success: CheckCircle2, error: AlertTriangle };

export function Alert({ kind = "info", children, className }: { kind?: Kind; children: ReactNode; className?: string }) {
  const Icon = ICONS[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={cn("flex gap-2 rounded-md border px-3 py-2 text-sm", STYLES[kind], className)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
