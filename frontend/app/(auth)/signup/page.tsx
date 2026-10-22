"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import type { AuthResponse } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { signupSchema } from "@/lib/validation";

function SignupForm() {
  const router = useRouter();
  const params = useSearchParams();
  const form = useForm(signupSchema, { full_name: "", email: "", password: "" });

  const submit = form.handleSubmit(async (data) => {
    await api.post<AuthResponse>("/auth/signup", data);
    const invite = params.get("invite");
    const plan = params.get("plan");
    const target = invite ? `/accept-invite?token=${encodeURIComponent(invite)}` : `/onboarding${plan ? `?plan=${plan}` : ""}`;
    router.replace(target);
    router.refresh();
  });

  return (
    <AuthCard
      title="Create your account"
      subtitle="Free plan, no card required"
      footer={
        <>
          Already registered? <Link href="/login" className="font-medium text-brand-600">Sign in</Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
        <Input label="Full name" autoComplete="name" value={form.values.full_name} onChange={(e) => form.setField("full_name", e.target.value)} error={form.errors.full_name} />
        <Input label="Email" type="email" autoComplete="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} error={form.errors.email} />
        <Input label="Password" type="password" autoComplete="new-password" hint="At least 8 characters with a letter and a number" value={form.values.password} onChange={(e) => form.setField("password", e.target.value)} error={form.errors.password} />
        <Button type="submit" className="w-full" loading={form.busy}>
          Create account
        </Button>
      </form>
    </AuthCard>
  );
}

export default function SignupPage() {
  return (
    <Suspense>
      <SignupForm />
    </Suspense>
  );
}
