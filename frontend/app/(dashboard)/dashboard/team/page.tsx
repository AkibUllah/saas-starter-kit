"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus, X } from "lucide-react";
import { canManage, useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge, roleTone, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { api, ApiError } from "@/lib/api";
import type { Invite, Member, Role } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { formatDate, initials } from "@/lib/utils";
import { inviteSchema } from "@/lib/validation";

const ROLES: Role[] = ["member", "admin", "owner"];

export default function TeamPage() {
  const { org, user } = useSession();
  const qc = useQueryClient();
  const manage = canManage(org.role);
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const members = useQuery({ queryKey: ["members", org.id], queryFn: () => api.get<Member[]>(`/orgs/${org.id}/members`) });
  const invites = useQuery({ queryKey: ["invites", org.id], queryFn: () => api.get<Invite[]>(`/orgs/${org.id}/invites`), enabled: manage });
  const form = useForm(inviteSchema, { email: "", role: "member" as Role });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["members", org.id] });
    qc.invalidateQueries({ queryKey: ["invites", org.id] });
  };
  const onError = (err: unknown) => setNotice({ kind: "error", text: err instanceof ApiError ? err.message : "Request failed" });
  const changeRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) => api.patch<Member>(`/orgs/${org.id}/members/${userId}`, { role }),
    onSuccess: refresh,
    onError,
  });
  const removeMember = useMutation({ mutationFn: (userId: string) => api.delete(`/orgs/${org.id}/members/${userId}`), onSuccess: refresh, onError });
  const revoke = useMutation({ mutationFn: (id: string) => api.delete(`/orgs/${org.id}/invites/${id}`), onSuccess: refresh, onError });

  const invite = form.handleSubmit(async (data) => {
    await api.post<Invite>(`/orgs/${org.id}/invites`, data);
    setOpen(false);
    form.reset();
    setNotice({ kind: "success", text: `Invitation sent to ${data.email}. In development the link is printed in the backend log.` });
    refresh();
  });

  return (
    <>
      <PageHeader
        title="Team"
        description="People with access to this organization"
        actions={manage && <Button onClick={() => setOpen(true)}><UserPlus className="h-4 w-4" /> Invite</Button>}
      />
      {notice && <Alert kind={notice.kind} className="mb-4">{notice.text}</Alert>}
      <section className="card p-0">
        <table className="table">
          <thead>
            <tr>
              <th>Member</th>
              <th>Role</th>
              <th>Joined</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(members.data ?? []).map((m) => {
              const isSelf = m.user_id === user.id;
              return (
                <tr key={m.user_id}>
                  <td>
                    <div className="flex items-center gap-3">
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold dark:bg-slate-700">{initials(m.full_name || m.email)}</span>
                      <div>
                        <div className="font-medium">{m.full_name} {isSelf && <span className="text-xs text-slate-500">(you)</span>}</div>
                        <div className="text-xs text-slate-500">{m.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    {manage ? (
                      <select
                        aria-label={`Role for ${m.email}`}
                        className="input w-auto py-1"
                        value={m.role}
                        onChange={(e) => changeRole.mutate({ userId: m.user_id, role: e.target.value as Role })}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r} disabled={r === "owner" && org.role !== "owner"}>
                            {r}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Badge tone={roleTone(m.role)}>{m.role}</Badge>
                    )}
                  </td>
                  <td className="text-slate-500">{formatDate(m.joined_at)}</td>
                  <td className="text-right">
                    {(manage || isSelf) && (
                      <Button variant="ghost" size="sm" onClick={() => window.confirm(isSelf ? "Leave this organization?" : `Remove ${m.email}?`) && removeMember.mutate(m.user_id)}>
                        {isSelf ? "Leave" : "Remove"}
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {manage && (
        <section className="card mt-6 p-0">
          <h2 className="border-b border-slate-200 px-5 py-3 font-semibold dark:border-slate-800">Invitations</h2>
          {invites.data && invites.data.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Expires</th>
                  <th className="text-right"></th>
                </tr>
              </thead>
              <tbody>
                {invites.data.map((i) => (
                  <tr key={i.id}>
                    <td>{i.email}</td>
                    <td><Badge tone={roleTone(i.role)}>{i.role}</Badge></td>
                    <td><Badge tone={statusTone(i.status)}>{i.status}</Badge></td>
                    <td className="text-slate-500">{formatDate(i.expires_at)}</td>
                    <td className="text-right">
                      {i.status === "pending" && (
                        <Button variant="ghost" size="sm" onClick={() => revoke.mutate(i.id)} aria-label="Revoke invitation"><X className="h-4 w-4" /></Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="p-5 text-sm text-slate-500">No invitations yet.</p>
          )}
        </section>
      )}

      <Dialog open={open} onClose={() => setOpen(false)} title="Invite a teammate">
        <form onSubmit={invite} className="space-y-4" noValidate>
          {form.errors._ && <Alert kind="error">{form.errors._}</Alert>}
          <Input label="Email" type="email" value={form.values.email} onChange={(e) => form.setField("email", e.target.value)} error={form.errors.email} autoFocus />
          <div>
            <label htmlFor="invite-role" className="label">Role</label>
            <select id="invite-role" className="input" value={form.values.role} onChange={(e) => form.setField("role", e.target.value as Role)}>
              {ROLES.map((r) => (
                <option key={r} value={r} disabled={r === "owner" && org.role !== "owner"}>{r}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" loading={form.busy}>Send invitation</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
