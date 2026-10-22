"use client";

import { useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { api } from "@/lib/api";
import { useSession } from "./OrgContext";

export function VerifyBanner() {
  const { user } = useSession();
  const [sent, setSent] = useState(false);
  if (user.email_verified) return null;
  return (
    <Alert kind="info" className="mb-4">
      Please verify {user.email}.{" "}
      {sent ? (
        "Verification email sent."
      ) : (
        <button type="button" className="underline" onClick={() => api.post("/auth/resend-verification").then(() => setSent(true))}>
          Resend the link
        </button>
      )}
    </Alert>
  );
}
