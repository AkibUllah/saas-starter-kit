"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AuthCard } from "@/components/auth/AuthCard";
import { Alert } from "@/components/ui/Alert";
import { api, ApiError } from "@/lib/api";

function VerifyEmail() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<"working" | "done" | "error">("working");
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("The verification link is missing its token.");
      return;
    }
    api
      .post("/auth/verify-email", { token })
      .then(() => setState("done"))
      .catch((err: unknown) => {
        setState("error");
        setMessage(err instanceof ApiError ? err.message : "Verification failed");
      });
  }, [token]);
  return (
    <AuthCard title="Email verification" footer={<Link href="/dashboard" className="text-brand-600">Continue to dashboard</Link>}>
      {state === "working" && <p className="text-sm text-slate-500">Verifying…</p>}
      {state === "done" && <Alert kind="success">Your email address is verified. Thank you.</Alert>}
      {state === "error" && <Alert kind="error">{message}</Alert>}
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
