import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type Tone = "neutral" | "brand" | "success" | "warning" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200",
  brand: "bg-brand-100 text-brand-800 dark:bg-brand-900/50 dark:text-brand-200",
  success: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200",
  warning: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200",
  danger: "bg-rose-100 text-rose-800 dark:bg-rose-900/50 dark:text-rose-200",
};

export function Badge({ tone = "neutral", children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize", TONES[tone], className)}>
      {children}
    </span>
  );
}

export function roleTone(role: string): Tone {
  return role === "owner" ? "brand" : role === "admin" ? "success" : "neutral";
}

export function statusTone(status: string): Tone {
  switch (status) {
    case "active":
    case "accepted":
    case "succeeded":
      return "success";
    case "past_due":
    case "pending":
    case "trialing":
      return "warning";
    case "canceled":
    case "revoked":
    case "expired":
    case "archived":
      return "danger";
    default:
      return "neutral";
  }
}
