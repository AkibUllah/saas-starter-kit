"use client";

import Link from "next/link";
import { useState } from "react";
import { z } from "zod";
import { AuthCard } from "@/components/auth/AuthCard";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { useForm } from "@/lib/useForm";
import { emailSchema } from "@/lib/validation";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const form = useForm(z.object({ email: emailSchema }), { email: "" });
  const submit = form.handleSubmit(async (data) => {
    await api.post("/auth/forgot-password", data);
    setSent(true);
  });
  return (
    <AuthCard title="Reset your password" subtitle="We will email you a link that works for two hours" footer={<Link href="/login" className="text-brand-600">Back to sign in</Link>}>
      {sent ? (
        <Alert kind="success">If that address has an account, a reset link is on its way. In development the link is printed in the backend log.</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
          <Input label="Email" type="email" autoComplete="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} error={form.errors.email} />
          <Button type="submit" className="w-full" loading={form.busy}>
            Send reset link
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
