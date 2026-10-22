"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Logo } from "@/components/Logo";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import type { Org } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { orgSchema } from "@/lib/validation";

function OnboardingForm() {
  const router = useRouter();
  const plan = useSearchParams().get("plan");
  const form = useForm(orgSchema, { name: "", slug: "" });
  const submit = form.handleSubmit(async (data) => {
    const org = await api.post<Org>("/orgs", { name: data.name, slug: data.slug || undefined });
    await fetch("/api/session/org", { method: "POST", body: JSON.stringify({ org_id: org.id }), headers: { "content-type": "application/json" } });
    router.replace(plan && plan !== "free" ? `/dashboard/billing?upgrade=${plan}` : "/dashboard");
    router.refresh();
  });
  return (
    <div className="card w-full max-w-md">
      <h1 className="text-xl font-semibold">Create your organization</h1>
      <p className="mt-1 text-sm text-slate-500">Projects, team members, API keys and billing all belong to an organization. You can create more later.</p>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
        <Input label="Organization name" placeholder="Acme Dhaka" value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} error={form.errors.name} />
        <Input label="URL slug (optional)" placeholder="acme-dhaka" value={form.values.slug ?? ""} onChange={(e) => form.setField("slug", e.target.value)} error={form.errors.slug} hint="Lowercase letters, numbers and dashes. Generated from the name if left blank." />
        <Button type="submit" className="w-full" loading={form.busy}>
          Continue
        </Button>
      </form>
    </div>
  );
}

export default function OnboardingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center bg-slate-50 px-4 py-10 dark:bg-slate-950">
      <Logo className="mb-8" />
      <Suspense>
        <OnboardingForm />
      </Suspense>
    </div>
  );
}
