import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/** 2900 -> "$29", 2950 -> "$29.50", 0 -> "$0". */
export function formatMoney(cents: number, currency = "USD"): string {
  const whole = cents % 100 === 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  return new Intl.DateTimeFormat("en-GB", { year: "numeric", month: "short", day: "2-digit" }).format(
    new Date(iso),
  );
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  return new Intl.DateTimeFormat("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  }).format(new Date(iso)) + " UTC";
}

/** "Akib Jafor" -> "AJ", "fatema" -> "FA", "" -> "?" */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Human label for limits: -1 means unlimited. */
export function limitLabel(limit: number): string {
  return limit === -1 ? "Unlimited" : String(limit);
}

/** Percentage of a quota used, clamped to 0-100; unlimited quotas report 0. */
export function usagePercent(used: number, limit: number): number {
  if (limit === -1 || limit === 0) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function titleCase(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
