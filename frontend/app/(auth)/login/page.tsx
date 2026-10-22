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
import { loginSchema } from "@/lib/validation";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next");
  const form = useForm(loginSchema, { email: "", password: "" });

  const submit = form.handleSubmit(async (data) => {
    await api.post<AuthResponse>("/auth/login", data);
    router.replace(next && next.startsWith("/") ? next : "/dashboard");
    router.refresh();
  });

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to your workspace"
      footer={
        <>
          No account? <Link href="/signup" className="font-medium text-brand-600">Create one</Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        {params.get("reset") === "1" && <Alert kind="success">Password updated. Sign in with your new password.</Alert>}
        {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
        <Input label="Email" type="email" autoComplete="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} error={form.errors.email} />
        <Input label="Password" type="password" autoComplete="current-password" value={form.values.password} onChange={(e) => form.setField("password", e.target.value)} error={form.errors.password} />
        <div className="flex items-center justify-between">
          <Link href="/forgot-password" className="text-sm text-brand-600">
            Forgot password?
          </Link>
          <Button type="submit" loading={form.busy}>
            Sign in
          </Button>
        </div>
      </form>
    </AuthCard>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
