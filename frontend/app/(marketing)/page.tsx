import Link from "next/link";
import { Building2, KeyRound, CreditCard, ShieldCheck, Users, ScrollText } from "lucide-react";
import { PricingTable } from "@/components/marketing/PricingTable";
import { PLANS } from "@/lib/plans";

const FEATURES = [
  { icon: Building2, title: "Organizations", text: "Every record is scoped to a tenant. Users belong to many orgs and switch in one click." },
  { icon: Users, title: "Team & roles", text: "Owner, admin and member roles with email invites, role changes and safe ownership transfer." },
  { icon: KeyRound, title: "API keys", text: "Scoped, hashed, revocable keys with usage tracking so customers can integrate from day one." },
  { icon: CreditCard, title: "Plans & billing", text: "Free, Pro and Business with enforced limits, checkout, webhooks, dunning states and cancellation." },
  { icon: ScrollText, title: "Audit log", text: "Who did what, when, from where. Filterable per organization and gated by plan." },
  { icon: ShieldCheck, title: "Secure sessions", text: "Short-lived access tokens, rotating refresh tokens with reuse detection, lockouts and rate limits." },
];

export default function LandingPage() {
  return (
    <>
      <section className="mx-auto max-w-6xl px-4 py-20 text-center">
        <p className="mb-4 inline-block rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 dark:border-brand-900 dark:bg-brand-950 dark:text-brand-200">
          FastAPI · Next.js 14 · Postgres · Redis
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
          The multi-tenant plumbing your SaaS needs, already wired
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600 dark:text-slate-300">
          Auth, organizations, invites, API keys, plan limits, billing webhooks, audit logs and an admin
          area. Start on the product, not on the scaffolding.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/signup" className="rounded-md bg-brand-600 px-5 py-3 font-medium text-white hover:bg-brand-700">
            Create your workspace
          </Link>
          <Link href="/login" className="rounded-md border border-slate-300 px-5 py-3 font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800">
            Sign in
          </Link>
        </div>
      </section>

      <section id="features" className="border-t border-slate-200 bg-slate-50 py-20 dark:border-slate-800 dark:bg-slate-900/50">
        <div className="mx-auto grid max-w-6xl gap-6 px-4 md:grid-cols-3">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="card">
              <Icon className="h-6 w-6 text-brand-600" aria-hidden="true" />
              <h3 className="mt-3 font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="pricing" className="mx-auto max-w-6xl px-4 py-20">
        <h2 className="text-center text-3xl font-bold">Simple pricing</h2>
        <p className="mt-2 text-center text-slate-600 dark:text-slate-300">
          Limits are enforced by the API, so the pricing page and the product never disagree.
        </p>
        <div className="mt-10">
          <PricingTable plans={PLANS} />
        </div>
      </section>
    </>
  );
}
