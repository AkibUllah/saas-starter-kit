"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api, ApiError } from "@/lib/api";
import type { AdminOrg, AdminStats, AdminUser, Page } from "@/lib/types";
import { formatDate, formatMoney } from "@/lib/utils";

export default function AdminPage() {
  const { user } = useSession();
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [error, setError] = useState<string | null>(null);
  const stats = useQuery({ queryKey: ["admin", "stats"], queryFn: () => api.get<AdminStats>("/admin/stats"), enabled: user.is_superuser, retry: false });
  const users = useQuery({ queryKey: ["admin", "users", q], queryFn: () => api.get<Page<AdminUser>>(`/admin/users?page_size=20${q ? `&q=${encodeURIComponent(q)}` : ""}`), enabled: user.is_superuser });
  const orgs = useQuery({ queryKey: ["admin", "orgs"], queryFn: () => api.get<Page<AdminOrg>>("/admin/orgs?page_size=20"), enabled: user.is_superuser });
  const toggle = useMutation({
    mutationFn: (u: AdminUser) => api.patch<AdminUser>(`/admin/users/${u.id}`, { is_active: !u.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin"] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Request failed"),
  });

  if (!user.is_superuser) return <Alert kind="error">This area is for platform administrators.</Alert>;
  const s = stats.data;
  const maxSignups = Math.max(1, ...(s?.signups_last_30_days.map((d) => d.count) ?? [1]));

  return (
    <>
      <PageHeader title="Admin" description="Platform-wide numbers across all organizations" />
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      {s && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ["Users", s.users_total],
            ["Verified", s.users_verified],
            ["Active 30d", s.users_active_30d],
            ["Organizations", s.orgs_total],
            ["Projects", s.projects_total],
          ].map(([label, value]) => (
            <div key={String(label)} className="card">
              <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
              <div className="mt-1 text-2xl font-semibold">{value}</div>
            </div>
          ))}
        </div>
      )}
      {s && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <section className="card">
            <h2 className="font-semibold">Revenue</h2>
            <div className="mt-2 text-3xl font-bold">{formatMoney(s.mrr_cents)} <span className="text-sm font-normal text-slate-500">MRR</span></div>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              {Object.entries(s.subscriptions_by_plan).map(([plan, n]) => <Badge key={plan} tone="brand">{plan}: {n}</Badge>)}
              {Object.entries(s.subscriptions_by_status).map(([st, n]) => <Badge key={st} tone={statusTone(st)}>{st}: {n}</Badge>)}
            </div>
          </section>
          <section className="card">
            <h2 className="font-semibold">Signups, last 30 days</h2>
            <svg viewBox="0 0 300 80" className="mt-2 h-24 w-full" role="img" aria-label="Signups per day">
              {s.signups_last_30_days.map((d, i) => {
                const h = (d.count / maxSignups) * 70;
                return <rect key={d.date} x={i * 10} y={78 - h} width={8} height={h} className="fill-brand-500"><title>{`${d.date}: ${d.count}`}</title></rect>;
              })}
            </svg>
          </section>
        </div>
      )}
      <section className="card mb-6 p-0">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-800">
          <h2 className="font-semibold">Users</h2>
          <Input placeholder="Search email or name" value={q} onChange={(e) => setQ(e.target.value)} className="w-64" aria-label="Search users" />
        </div>
        <table className="table">
          <thead>
            <tr><th>User</th><th>Orgs</th><th>Status</th><th>Joined</th><th className="text-right"></th></tr>
          </thead>
          <tbody>
            {(users.data?.items ?? []).map((u) => (
              <tr key={u.id}>
                <td><div className="font-medium">{u.full_name}</div><div className="text-xs text-slate-500">{u.email}</div></td>
                <td>{u.org_count}</td>
                <td className="space-x-1">
                  <Badge tone={u.is_active ? "success" : "danger"}>{u.is_active ? "active" : "disabled"}</Badge>
                  {u.is_superuser && <Badge tone="warning">superuser</Badge>}
                  {!u.email_verified && <Badge>unverified</Badge>}
                </td>
                <td className="text-slate-500">{formatDate(u.created_at)}</td>
                <td className="text-right">{u.id !== user.id && <Button variant="ghost" size="sm" onClick={() => toggle.mutate(u)}>{u.is_active ? "Disable" : "Enable"}</Button>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section className="card p-0">
        <h2 className="border-b border-slate-200 px-5 py-3 font-semibold dark:border-slate-800">Organizations</h2>
        <table className="table">
          <thead>
            <tr><th>Organization</th><th>Plan</th><th>Status</th><th>Members</th><th>Projects</th><th>Created</th></tr>
          </thead>
          <tbody>
            {(orgs.data?.items ?? []).map((o) => (
              <tr key={o.id}>
                <td><div className="font-medium">{o.name}</div><div className="text-xs text-slate-500">{o.slug}</div></td>
                <td><Badge tone="brand">{o.plan}</Badge></td>
                <td><Badge tone={statusTone(o.subscription_status)}>{o.subscription_status}</Badge></td>
                <td>{o.member_count}</td>
                <td>{o.project_count}</td>
                <td className="text-slate-500">{formatDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
