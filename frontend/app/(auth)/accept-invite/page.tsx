"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AuthCard } from "@/components/auth/AuthCard";
import { Alert } from "@/components/ui/Alert";
import { Badge, roleTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import type { InvitePreview, Org, User } from "@/lib/types";

function AcceptInvite() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const preview = useQuery({
    queryKey: ["invite", token],
    queryFn: () => api.get<InvitePreview>(`/invites/preview?token=${encodeURIComponent(token)}`),
    enabled: token.length > 0,
    retry: false,
  });
  const me = useQuery({ queryKey: ["me"], queryFn: () => api.get<User>("/users/me"), retry: false });

  const accept = async () => {
    setBusy(true);
    setError(null);
    try {
      const org = await api.post<Org>("/invites/accept", { token });
      await fetch("/api/session/org", { method: "POST", body: JSON.stringify({ org_id: org.id }), headers: { "content-type": "application/json" } });
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not accept the invitation");
      setBusy(false);
    }
  };

  if (!token) return <AuthCard title="Invitation"><Alert kind="error">This link is missing its token.</Alert></AuthCard>;
  if (preview.isPending) return <AuthCard title="Invitation"><p className="text-sm text-slate-500">Loading…</p></AuthCard>;
  if (preview.isError || !preview.data) return <AuthCard title="Invitation"><Alert kind="error">This invitation does not exist.</Alert></AuthCard>;
  const invite = preview.data;
  const mismatch = me.data && me.data.email !== invite.email;

  return (
    <AuthCard title={`Join ${invite.org_name}`} subtitle={`Invitation for ${invite.email}`}>
      <div className="space-y-4">
        <p className="text-sm">
          You have been invited as <Badge tone={roleTone(invite.role)}>{invite.role}</Badge>
        </p>
        {invite.status !== "pending" && <Alert kind="error">This invitation is {invite.status}.</Alert>}
        {mismatch && (
          <Alert kind="error">
            You are signed in as {me.data?.email}. Sign out and use the {invite.email} account to accept.
          </Alert>
        )}
        {error && <Alert kind="error">{error}</Alert>}
        {me.data ? (
          <Button className="w-full" onClick={accept} loading={busy} disabled={invite.status !== "pending" || Boolean(mismatch)}>
            Accept invitation
          </Button>
        ) : (
          <div className="flex gap-2">
            <Link href={`/signup?invite=${encodeURIComponent(token)}`} className="flex-1 rounded-md bg-brand-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-brand-700">
              Create account
            </Link>
            <Link href={`/login?next=${encodeURIComponent(`/accept-invite?token=${token}`)}`} className="flex-1 rounded-md border border-slate-300 px-4 py-2 text-center text-sm font-medium dark:border-slate-700">
              Sign in
            </Link>
          </div>
        )}
      </div>
    </AuthCard>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense>
      <AcceptInvite />
    </Suspense>
  );
}
