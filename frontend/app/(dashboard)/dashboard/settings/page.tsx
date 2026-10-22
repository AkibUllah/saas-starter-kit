"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api, ApiError } from "@/lib/api";
import type { Org, User } from "@/lib/types";
import { useForm } from "@/lib/useForm";
import { passwordSchema } from "@/lib/validation";

export default function SettingsPage() {
  const { user, org } = useSession();
  const router = useRouter();
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const profile = useForm(z.object({ full_name: z.string().trim().min(1, "Name is required").max(120) }), { full_name: user.full_name });
  const password = useForm(z.object({ current_password: z.string().min(1, "Enter your current password"), new_password: passwordSchema }), { current_password: "", new_password: "" });
  const orgForm = useForm(z.object({ name: z.string().trim().min(2).max(120) }), { name: org.name });
  const isOwner = org.role === "owner";
  const manage = isOwner || org.role === "admin";

  const saveProfile = profile.handleSubmit(async (data) => {
    await api.patch<User>("/users/me", data);
    setSaved("Profile updated");
    router.refresh();
  });
  const changePassword = password.handleSubmit(async (data) => {
    await api.post("/auth/change-password", data);
    router.replace("/login?reset=1");
    router.refresh();
  });
  const saveOrg = orgForm.handleSubmit(async (data) => {
    await api.patch<Org>(`/orgs/${org.id}`, data);
    setSaved("Organization updated");
    router.refresh();
  });
  const deleteOrg = async () => {
    if (!window.confirm(`Delete ${org.name} and everything in it? This cannot be undone.`)) return;
    try {
      await api.delete(`/orgs/${org.id}`);
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete");
    }
  };
  const signOutEverywhere = async () => {
    await api.post("/auth/logout-all");
    router.replace("/login");
    router.refresh();
  };

  return (
    <>
      <PageHeader title="Settings" description="Your profile, security and this organization" />
      {saved && <Alert kind="success" className="mb-4">{saved}</Alert>}
      {error && <Alert kind="error" className="mb-4">{error}</Alert>}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="card">
          <h2 className="font-semibold">Profile</h2>
          <form onSubmit={saveProfile} className="mt-4 space-y-4" noValidate>
            {profile.errors._ && <Alert kind="error">{profile.errors._}</Alert>}
            <Input label="Full name" value={profile.values.full_name} onChange={(e) => profile.setField("full_name", e.target.value)} error={profile.errors.full_name} />
            <Input label="Email" value={user.email} disabled hint={user.email_verified ? "Verified" : "Not verified yet"} />
            <Button type="submit" loading={profile.busy}>Save</Button>
          </form>
        </section>
        <section className="card">
          <h2 className="font-semibold">Password</h2>
          <form onSubmit={changePassword} className="mt-4 space-y-4" noValidate>
            {password.errors._ && <Alert kind="error">{password.errors._}</Alert>}
            <Input label="Current password" type="password" autoComplete="current-password" value={password.values.current_password} onChange={(e) => password.setField("current_password", e.target.value)} error={password.errors.current_password} />
            <Input label="New password" type="password" autoComplete="new-password" value={password.values.new_password} onChange={(e) => password.setField("new_password", e.target.value)} error={password.errors.new_password} />
            <div className="flex items-center justify-between">
              <button type="button" className="text-sm text-slate-500 underline" onClick={signOutEverywhere}>Sign out of all devices</button>
              <Button type="submit" loading={password.busy}>Change password</Button>
            </div>
          </form>
        </section>
        <section className="card">
          <h2 className="font-semibold">Organization</h2>
          <form onSubmit={saveOrg} className="mt-4 space-y-4" noValidate>
            {orgForm.errors._ && <Alert kind="error">{orgForm.errors._}</Alert>}
            <Input label="Name" value={orgForm.values.name} onChange={(e) => orgForm.setField("name", e.target.value)} error={orgForm.errors.name} disabled={!manage} />
            <Input label="Slug" value={org.slug} disabled hint="Used in URLs; fixed after creation" />
            {manage && <Button type="submit" loading={orgForm.busy}>Save</Button>}
          </form>
        </section>
        {isOwner && (
          <section className="card border-rose-200 dark:border-rose-900">
            <h2 className="font-semibold text-rose-700 dark:text-rose-300">Danger zone</h2>
            <p className="mt-1 text-sm text-slate-500">Deleting the organization removes its projects, members, API keys and billing history.</p>
            <Button variant="danger" className="mt-4" onClick={deleteOrg}>Delete organization</Button>
          </section>
        )}
      </div>
    </>
  );
}
