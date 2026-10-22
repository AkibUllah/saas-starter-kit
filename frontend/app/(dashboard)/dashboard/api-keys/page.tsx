"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound } from "lucide-react";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { api, ApiError } from "@/lib/api";
import type { ApiKey, ApiKeyCreated } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { formatDate, formatDateTime } from "@/lib/utils";
import { apiKeySchema } from "@/lib/validation";

const SCOPES: { id: "org:read" | "projects:read" | "projects:write"; label: string }[] = [
  { id: "org:read", label: "Read organization" },
  { id: "projects:read", label: "Read projects" },
  { id: "projects:write", label: "Create and update projects" },
];

export default function ApiKeysPage() {
  const { org } = useSession();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [error, setError] = useState<string | null>(null);
  const keys = useQuery({ queryKey: ["api-keys", org.id], queryFn: () => api.get<ApiKey[]>(`/orgs/${org.id}/api-keys`) });
  const form = useForm(apiKeySchema, { name: "", scopes: ["projects:read"] as ("org:read" | "projects:read" | "projects:write")[], expires_in_days: undefined as number | undefined });
  const refresh = () => qc.invalidateQueries({ queryKey: ["api-keys", org.id] });
  const revoke = useMutation({
    mutationFn: (id: string) => api.delete<ApiKey>(`/orgs/${org.id}/api-keys/${id}`),
    onSuccess: refresh,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Request failed"),
  });

  const create = form.handleSubmit(async (data) => {
    const key = await api.post<ApiKeyCreated>(`/orgs/${org.id}/api-keys`, data);
    setCreated(key);
    setOpen(false);
    form.reset();
    refresh();
  });

  const toggleScope = (scope: (typeof SCOPES)[number]["id"]) => {
    const current = form.values.scopes;
    form.setField("scopes", current.includes(scope) ? current.filter((s) => s !== scope) : [...current, scope]);
  };

  return (
    <>
      <PageHeader title="API keys" description="Server-to-server access scoped to this organization. Send the key as `Authorization: Bearer sk_live_…`." actions={<Button onClick={() => setOpen(true)}><KeyRound className="h-4 w-4" /> New key</Button>} />
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      {created && (
        <Alert kind="success" className="mb-4">
          <p className="font-medium">Copy your key now. It is shown only once.</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="rounded bg-white/60 px-2 py-1 font-mono text-xs dark:bg-black/30" data-testid="new-key">{created.key}</code>
            <Button size="sm" variant="secondary" onClick={() => navigator.clipboard?.writeText(created.key)} aria-label="Copy key"><Copy className="h-3 w-3" /></Button>
          </div>
        </Alert>
      )}
      <section className="card p-0">
        {keys.data && keys.data.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Key</th>
                <th>Scopes</th>
                <th>Last used</th>
                <th>Expires</th>
                <th className="text-right"></th>
              </tr>
            </thead>
            <tbody>
              {keys.data.map((k) => (
                <tr key={k.id} className={k.revoked_at ? "opacity-50" : ""}>
                  <td className="font-medium">{k.name}</td>
                  <td className="font-mono text-xs">{k.masked}</td>
                  <td className="space-x-1">{k.scopes.map((s) => <Badge key={s}>{s}</Badge>)}</td>
                  <td className="text-slate-500">{formatDateTime(k.last_used_at)}</td>
                  <td className="text-slate-500">{k.expires_at ? formatDate(k.expires_at) : "never"}</td>
                  <td className="text-right">
                    {k.revoked_at ? <Badge tone="danger">revoked</Badge> : <Button variant="ghost" size="sm" onClick={() => window.confirm(`Revoke ${k.name}?`) && revoke.mutate(k.id)}>Revoke</Button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="p-8 text-center text-sm text-slate-500">No API keys yet.</p>
        )}
      </section>

      <Dialog open={open} onClose={() => setOpen(false)} title="Create API key">
        <form onSubmit={create} className="space-y-4" noValidate>
          {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
          <Input label="Name" placeholder="CI deploy key" value={form.values.name} onChange={(e) => form.setField("name", e.target.value)} error={form.errors.name} autoFocus />
          <fieldset>
            <legend className="label">Scopes</legend>
            <div className="space-y-1">
              {SCOPES.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={form.values.scopes.includes(s.id)} onChange={() => toggleScope(s.id)} /> {s.label} <code className="text-xs text-slate-500">{s.id}</code>
                </label>
              ))}
            </div>
            {form.errors.scopes && <p role="alert" className="mt-1 text-xs text-rose-600">{form.errors.scopes}</p>}
          </fieldset>
          <Input label="Expires in days (optional)" type="number" min={1} max={3650} value={form.values.expires_in_days ?? ""} onChange={(e) => form.setField("expires_in_days", e.target.value ? Number(e.target.value) : undefined)} error={form.errors.expires_in_days} />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={form.busy}>Create key</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
