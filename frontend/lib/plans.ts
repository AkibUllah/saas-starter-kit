import type { Plan, PlanId } from "./types";

export const PLAN_ORDER: PlanId[] = ["free", "pro", "business"];

/**
 * Static copy of the backend catalogue for the marketing page (rendered without an
 * API call). The dashboard always uses the live `/plans` response.
 */
export const PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    price_cents: 0,
    description: "For trying things out and tiny side projects.",
    limits: { projects: 3, members: 3, api_keys: 1 },
    features: { audit_log: false, priority_support: false, sso: false },
    highlights: ["3 projects", "3 team members", "1 API key", "Community support"],
  },
  {
    id: "pro",
    name: "Pro",
    price_cents: 2900,
    description: "For small teams shipping to customers.",
    limits: { projects: 25, members: 10, api_keys: 10 },
    features: { audit_log: true, priority_support: true, sso: false },
    highlights: ["25 projects", "10 team members", "10 API keys", "Audit log", "Priority support"],
  },
  {
    id: "business",
    name: "Business",
    price_cents: 9900,
    description: "For companies that need scale and compliance.",
    limits: { projects: -1, members: 100, api_keys: 100 },
    features: { audit_log: true, priority_support: true, sso: true },
    highlights: ["Unlimited projects", "100 team members", "100 API keys", "Audit log", "SSO"],
  },
];

export function isUpgrade(current: PlanId, target: PlanId): boolean {
  return PLAN_ORDER.indexOf(target) > PLAN_ORDER.indexOf(current);
}

export function planById(id: string): Plan {
  return PLANS.find((p) => p.id === id) ?? PLANS[0];
}

/** The cheapest plan whose limit for `resource` fits `needed`. */
export function planFor(resource: string, needed: number): Plan {
  return PLANS.find((p) => p.limits[resource] === -1 || p.limits[resource] >= needed) ?? PLANS[PLANS.length - 1];
}
