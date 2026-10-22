"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { PricingTable } from "@/components/marketing/PricingTable";
import { Alert } from "@/components/ui/Alert";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { UsageMeter } from "@/components/ui/UsageMeter";
import { api, ApiError } from "@/lib/api";
import type { BillingOverview, Checkout, Plan, PlanId, Subscription } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

function BillingPage() {
  const { org } = useSession();
  const router = useRouter();
  const qc = useQueryClient();
  const params = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [busyPlan, setBusyPlan] = useState<PlanId | null>(null);
  const overview = useQuery({ queryKey: ["billing", org.id], queryFn: () => api.get<BillingOverview>(`/orgs/${org.id}/billing`) });
  const isOwner = org.role === "owner";
  const onError = (err: unknown) => setError(err instanceof ApiError ? err.message : "Request failed");
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["billing", org.id] });
    router.refresh();
  };
  const cancel = useMutation({ mutationFn: () => api.post<Subscription>(`/orgs/${org.id}/billing/cancel`), onSuccess: refresh, onError });
  const resume = useMutation({ mutationFn: () => api.post<Subscription>(`/orgs/${org.id}/billing/resume`), onSuccess: refresh, onError });

  const choose = async (plan: Plan) => {
    setError(null);
    if (plan.id === "free") {
      cancel.mutate();
      return;
    }
    setBusyPlan(plan.id);
    try {
      const session = await api.post<Checkout>(`/orgs/${org.id}/billing/checkout`, { plan: plan.id });
      router.push(`/dashboard/billing/checkout?session=${session.session_id}`);
    } catch (err) {
      onError(err);
      setBusyPlan(null);
    }
  };

  const sub = overview.data?.subscription;
  return (
    <>
      <PageHeader title="Billing" description="Plan, usage and payment status for this organization" />
      {params.get("upgraded") && <Alert kind="success" className="mb-4">Your plan is now {overview.data?.plan.name}. Limits were raised immediately.</Alert>}
      {params.get("upgrade") && !params.get("upgraded") && <Alert kind="info" className="mb-4">Pick the {params.get("upgrade")} plan below to finish upgrading.</Alert>}
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      {!isOwner && <Alert kind="info" className="mb-4">Only organization owners can change the plan.</Alert>}

      {overview.data && sub && (
        <div className="mb-8 grid gap-6 lg:grid-cols-2">
          <section className="card">
            <h2 className="font-semibold">Current subscription</h2>
            <dl className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
              <dt className="text-slate-500">Plan</dt>
              <dd className="font-medium">{overview.data.plan.name} · {formatMoney(overview.data.plan.price_cents)}/month</dd>
              <dt className="text-slate-500">Status</dt>
              <dd><Badge tone={statusTone(sub.status)}>{sub.status.replace("_", " ")}</Badge></dd>
              <dt className="text-slate-500">Current period ends</dt>
              <dd>{formatDate(sub.current_period_end)}</dd>
              <dt className="text-slate-500">Provider</dt>
              <dd className="capitalize">{sub.provider} (sandbox)</dd>
            </dl>
            {sub.status === "past_due" && <Alert kind="error" className="mt-4">The last payment failed. Update the payment method with the provider to keep {overview.data.plan.name} features.</Alert>}
            {sub.plan !== "free" && isOwner && (
              <div className="mt-4">
                {sub.cancel_at_period_end ? (
                  <div className="flex items-center justify-between gap-3 text-sm">
                    <span>Cancels on {formatDate(sub.current_period_end)}.</span>
                    <Button variant="secondary" size="sm" onClick={() => resume.mutate()} loading={resume.isPending}>Keep subscription</Button>
                  </div>
                ) : (
                  <Button variant="ghost" size="sm" onClick={() => window.confirm("Cancel at the end of the period?") && cancel.mutate()} loading={cancel.isPending}>Cancel at period end</Button>
                )}
              </div>
            )}
          </section>
          <section className="card space-y-4">
            <h2 className="font-semibold">Usage</h2>
            {Object.entries(overview.data.usage).map(([key, u]) => <UsageMeter key={key} label={key} used={u.used} limit={u.limit} />)}
          </section>
        </div>
      )}

      {overview.data && (
        <PricingTable plans={overview.data.plans} currentPlan={overview.data.plan.id} onSelect={isOwner ? choose : undefined} busyPlan={busyPlan} ctaHref={() => "#"} />
      )}
    </>
  );
}

export default function BillingPageWrapper() {
  return (
    <Suspense>
      <BillingPage />
    </Suspense>
  );
}
