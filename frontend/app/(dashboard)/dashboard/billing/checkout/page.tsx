"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import type { Checkout } from "@/lib/types";
import { formatMoney, titleCase } from "@/lib/utils";

/**
 * Stand-in for the provider's hosted checkout page. "Pay" tells the backend to emit the
 * signed `checkout.completed` webhook, exactly what a real provider would do after payment.
 */
function MockCheckout() {
  const { org } = useSession();
  const router = useRouter();
  const sessionId = useSearchParams().get("session") ?? "";
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const session = useQuery({
    queryKey: ["checkout", org.id, sessionId],
    queryFn: () => api.get<Checkout>(`/orgs/${org.id}/billing/checkout/${sessionId}`),
    enabled: sessionId.length > 0,
    retry: false,
  });

  const pay = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/orgs/${org.id}/billing/checkout/${sessionId}/complete`);
      router.replace("/dashboard/billing?upgraded=1");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment failed");
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-md">
      <PageHeader title="Checkout" description="Sandbox payment page (no real charge)" />
      {session.isError && <Alert kind="error">Checkout session not found.</Alert>}
      {session.data && (
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">{org.name}</span>
            <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/50 dark:text-amber-200">Test mode</span>
          </div>
          <div>
            <div className="text-sm text-slate-500">{titleCase(session.data.plan)} plan, monthly</div>
            <div className="text-3xl font-bold">{formatMoney(session.data.amount_cents)}</div>
          </div>
          <div className="space-y-2 rounded-md border border-dashed border-slate-300 p-3 text-sm text-slate-500 dark:border-slate-700">
            <div className="flex justify-between"><span>Card</span><span className="font-mono">4242 4242 4242 4242</span></div>
            <div className="flex justify-between"><span>Expiry</span><span className="font-mono">12/30</span></div>
          </div>
          {error && <Alert kind="error">{error}</Alert>}
          {session.data.status === "completed" ? (
            <Alert kind="success">This checkout was already completed.</Alert>
          ) : (
            <Button className="w-full" onClick={pay} loading={busy}>
              <ShieldCheck className="h-4 w-4" /> Pay {formatMoney(session.data.amount_cents)}
            </Button>
          )}
          <button type="button" className="w-full text-center text-sm text-slate-500 underline" onClick={() => router.push("/dashboard/billing")}>
            Back to billing
          </button>
        </div>
      )}
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense>
      <MockCheckout />
    </Suspense>
  );
}
