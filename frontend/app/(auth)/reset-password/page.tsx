"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { useForm } from "@/lib/useForm";
import { resetPasswordSchema } from "@/lib/validation";

function ResetForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const form = useForm(resetPasswordSchema, { password: "", confirm: "" });
  const submit = form.handleSubmit(async (data) => {
    await api.post("/auth/reset-password", { token, password: data.password });
    router.replace("/login?reset=1");
  });
  if (!token) {
    return (
      <AuthCard title="Invalid link">
        <Alert kind="error">This reset link is missing its token. Request a new one from the <Link href="/forgot-password" className="underline">forgot password</Link> page.</Alert>
      </AuthCard>
    );
  }
  return (
    <AuthCard title="Choose a new password">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
        <Input label="New password" type="password" autoComplete="new-password" value={form.values.password} onChange={(e) => form.setField("password", e.target.value)} error={form.errors.password} />
        <Input label="Confirm password" type="password" autoComplete="new-password" value={form.values.confirm} onChange={(e) => form.setField("confirm", e.target.value)} error={form.errors.confirm} />
        <Button type="submit" className="w-full" loading={form.busy}>
          Update password
        </Button>
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetForm />
    </Suspense>
  );
}
