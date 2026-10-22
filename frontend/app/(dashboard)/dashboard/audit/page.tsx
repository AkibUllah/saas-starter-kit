"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "@/components/dashboard/OrgContext";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";
import type { AuditEntry, Page } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

const FILTERS = ["", "user", "org", "member", "invite", "project", "api_key", "billing"];
const PAGE_SIZE = 25;

export default function AuditPage() {
  const { org } = useSession();
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const audit = useQuery({
    queryKey: ["audit", org.id, action, page],
    queryFn: () => api.get<Page<AuditEntry>>(`/orgs/${org.id}/audit?page=${page}&page_size=${PAGE_SIZE}${action ? `&action=${action}` : ""}`),
    retry: false,
  });
  const gated = audit.error instanceof ApiError && audit.error.status === 402;
  const total = audit.data?.total ?? 0;

  return (
    <>
      <PageHeader title="Audit log" description="Every change made in this organization, newest first" />
      {gated ? (
        <Alert kind="info">
          The audit log is included in the Pro and Business plans. <Link href="/dashboard/billing" className="font-medium underline">Upgrade</Link> to see who changed what.
        </Alert>
      ) : audit.isError ? (
        <Alert kind="error">{(audit.error as Error).message}</Alert>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap gap-1">
            {FILTERS.map((f) => (
              <button key={f} type="button" onClick={() => { setAction(f); setPage(1); }} className={`rounded-md border px-2.5 py-1 text-xs ${action === f ? "border-brand-600 bg-brand-600 text-white" : "border-slate-300 dark:border-slate-700"}`}>
                {f || "all"}
              </button>
            ))}
          </div>
          <section className="card p-0">
            <table className="table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {(audit.data?.items ?? []).map((e) => (
                  <tr key={e.id}>
                    <td className="whitespace-nowrap text-slate-500">{formatDateTime(e.created_at)}</td>
                    <td>{e.actor_email || "system"}</td>
                    <td><Badge>{e.action}</Badge></td>
                    <td className="font-mono text-xs text-slate-500">{e.target_type && `${e.target_type}:${e.target_id.slice(0, 8)}`}</td>
                    <td className="font-mono text-xs text-slate-500">{Object.keys(e.metadata).length ? JSON.stringify(e.metadata) : ""}</td>
                  </tr>
                ))}
                {audit.data && audit.data.items.length === 0 && (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-500">No entries.</td></tr>
                )}
              </tbody>
            </table>
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-2 text-sm text-slate-500 dark:border-slate-800">
              <span>{total} entries</span>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                <Button variant="secondary" size="sm" disabled={page * PAGE_SIZE >= total} onClick={() => setPage((p) => p + 1)}>Next</Button>
              </div>
            </div>
          </section>
        </>
      )}
    </>
  );
}
