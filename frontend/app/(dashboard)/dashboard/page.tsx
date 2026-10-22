"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Plus, Trash2 } from "lucide-react";
import { canManage, useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { UsageMeter } from "@/components/ui/UsageMeter";
import { api, ApiError } from "@/lib/api";
import type { BillingOverview, Project } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { formatDate } from "@/lib/utils";
import { projectSchema } from "@/lib/validation";
import Link from "next/link";

export default function OverviewPage() {
  const { org } = useSession();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const projects = useQuery({ queryKey: ["projects", org.id], queryFn: () => api.get<Project[]>(`/orgs/${org.id}/projects`) });
  const billing = useQuery({ queryKey: ["billing", org.id], queryFn: () => api.get<BillingOverview>(`/orgs/${org.id}/billing`) });
  const form = useForm(projectSchema, { name: "", description: "" });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["projects", org.id] });
    qc.invalidateQueries({ queryKey: ["billing", org.id] });
  };
  const onError = (err: unknown) => setError(err instanceof ApiError ? err.message : "Request failed");
  const archive = useMutation({
    mutationFn: (p: Project) => api.patch<Project>(`/orgs/${org.id}/projects/${p.id}`, { status: p.status === "active" ? "archived" : "active" }),
    onSuccess: invalidate,
    onError,
  });
  const remove = useMutation({ mutationFn: (id: string) => api.delete(`/orgs/${org.id}/projects/${id}`), onSuccess: invalidate, onError });

  const create = form.handleSubmit(async (data) => {
    await api.post<Project>(`/orgs/${org.id}/projects`, data);
    form.reset();
    setOpen(false);
    invalidate();
  });

  const usage = billing.data?.usage;
  const atLimit = usage ? usage.projects.limit !== -1 && usage.projects.used >= usage.projects.limit : false;

  return (
    <>
      <PageHeader
        title={org.name}
        description={`Overview of your ${billing.data?.plan.name ?? org.plan} workspace`}
        actions={
          <Button onClick={() => setOpen(true)} disabled={!canManage(org.role) && org.role !== "member"}>
            <Plus className="h-4 w-4" /> New project
          </Button>
        }
      />
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      {atLimit && (
        <Alert kind="info" className="mb-4">
          You have used all {usage?.projects.limit} projects on the {billing.data?.plan.name} plan.{" "}
          <Link href="/dashboard/billing" className="font-medium underline">Upgrade</Link> to add more.
        </Alert>
      )}
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="card p-0">
          <h2 className="border-b border-slate-200 px-5 py-3 font-semibold dark:border-slate-800">Projects</h2>
          {projects.isPending ? (
            <p className="p-5 text-sm text-slate-500">Loading…</p>
          ) : projects.data && projects.data.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {projects.data.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-slate-500">{p.description || p.slug}</div>
                    </td>
                    <td><Badge tone={statusTone(p.status)}>{p.status}</Badge></td>
                    <td className="text-slate-500">{formatDate(p.created_at)}</td>
                    <td className="text-right">
                      <Button variant="ghost" size="sm" onClick={() => archive.mutate(p)} aria-label={p.status === "active" ? "Archive" : "Restore"}>
                        <Archive className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => window.confirm(`Delete ${p.name}?`) && remove.mutate(p.id)} aria-label="Delete">
                        <Trash2 className="h-4 w-4 text-rose-600" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-sm text-slate-500">No projects yet. Create the first one.</div>
          )}
        </section>
        <aside className="space-y-6">
          <section className="card space-y-4">
            <h2 className="font-semibold">Plan usage</h2>
            {usage ? (
              Object.entries(usage).map(([key, u]) => <UsageMeter key={key} label={key} used={u.used} limit={u.limit} />)
            ) : (
              <p className="text-sm text-slate-500">Loading…</p>
            )}
            <Link href="/dashboard/billing" className="block text-sm font-medium text-brand-600">
              Manage plan →
            </Link>
          </section>
          <section className="card text-sm">
            <h2 className="font-semibold">Your role</h2>
            <p className="mt-1 text-slate-500">
              You are <Badge tone="brand">{org.role}</Badge> of {org.name}.
            </p>
          </section>
        </aside>
      </div>

      <Dialog open={open} onClose={() => setOpen(false)} title="New project">
        <form onSubmit={create} className="space-y-4" noValidate>
          {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
          <Input label="Name" value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} error={form.errors.name} autoFocus />
          <Input label="Description" value={form.values.description ?? ""} onChange={(e) => form.setField("description", e.target.value)} error={form.errors.description} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={form.busy}>Create</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
