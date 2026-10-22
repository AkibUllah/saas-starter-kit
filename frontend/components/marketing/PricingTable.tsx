import Link from "next/link";
import { Check } from "lucide-react";
import type { Plan, PlanId } from "@/lib/types";
import { formatMoney, cn } from "@/lib/utils";

interface Props {
  plans: Plan[];
  currentPlan?: PlanId;
  onSelect?: (plan: Plan) => void;
  ctaHref?: (plan: Plan) => string;
  busyPlan?: PlanId | null;
}

/** Shared by the marketing page (links to signup) and the billing page (upgrade buttons). */
export function PricingTable({ plans, currentPlan, onSelect, ctaHref, busyPlan }: Props) {
  return (
    <div className="grid gap-6 md:grid-cols-3" data-testid="pricing-table">
      {plans.map((plan) => {
        const current = plan.id === currentPlan;
        const featured = plan.id === "pro";
        return (
          <div
            key={plan.id}
            data-testid={`plan-${plan.id}`}
            className={cn("card flex flex-col", featured && "border-brand-500 ring-1 ring-brand-500")}
          >
            <div className="flex items-baseline justify-between">
              <h3 className="text-lg font-semibold">{plan.name}</h3>
              {featured && <span className="rounded-full bg-brand-600 px-2 py-0.5 text-xs font-medium text-white">Popular</span>}
            </div>
            <p className="mt-1 text-sm text-slate-500">{plan.description}</p>
            <p className="mt-4">
              <span className="text-3xl font-bold">{formatMoney(plan.price_cents)}</span>
              <span className="text-sm text-slate-500"> / month</span>
            </p>
            <ul className="mt-4 flex-1 space-y-2 text-sm">
              {plan.highlights.map((h) => (
                <li key={h} className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-emerald-500" aria-hidden="true" /> {h}
                </li>
              ))}
            </ul>
            <div className="mt-6">
              {current ? (
                <span className="inline-flex h-10 w-full items-center justify-center rounded-md border border-slate-300 text-sm text-slate-500 dark:border-slate-700">
                  Current plan
                </span>
              ) : onSelect ? (
                <button
                  type="button"
                  onClick={() => onSelect(plan)}
                  disabled={busyPlan !== undefined && busyPlan !== null}
                  className={cn(
                    "h-10 w-full rounded-md text-sm font-medium",
                    featured ? "bg-brand-600 text-white hover:bg-brand-700" : "border border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800",
                  )}
                >
                  {busyPlan === plan.id ? "Redirecting…" : plan.price_cents === 0 ? "Downgrade" : `Upgrade to ${plan.name}`}
                </button>
              ) : (
                <Link
                  href={ctaHref ? ctaHref(plan) : `/signup?plan=${plan.id}`}
                  className={cn(
                    "inline-flex h-10 w-full items-center justify-center rounded-md text-sm font-medium",
                    featured ? "bg-brand-600 text-white hover:bg-brand-700" : "border border-slate-300 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800",
                  )}
                >
                  {plan.price_cents === 0 ? "Start for free" : `Start with ${plan.name}`}
                </Link>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
