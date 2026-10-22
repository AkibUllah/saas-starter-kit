"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Building2, ChevronsUpDown, Plus } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { useSession } from "./OrgContext";

export function OrgSwitcher() {
  const router = useRouter();
  const { org, orgs } = useSession();
  const [open, setOpen] = useState(false);

  const choose = async (orgId: string) => {
    setOpen(false);
    if (orgId === org.id) return;
    await fetch("/api/session/org", { method: "POST", body: JSON.stringify({ org_id: orgId }), headers: { "content-type": "application/json" } });
    router.push("/dashboard");
    router.refresh();
  };

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-left text-sm hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
      >
        <Building2 className="h-4 w-4 text-slate-500" aria-hidden="true" />
        <span className="flex-1 truncate font-medium">{org.name}</span>
        <Badge tone="brand">{org.plan}</Badge>
        <ChevronsUpDown className="h-4 w-4 text-slate-400" aria-hidden="true" />
      </button>
      {open && (
        <ul role="listbox" className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900">
          {orgs.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                role="option"
                aria-selected={o.id === org.id}
                onClick={() => choose(o.id)}
                className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800"
              >
                <span className="truncate">{o.name}</span>
                <span className="text-xs text-slate-500">{o.role}</span>
              </button>
            </li>
          ))}
          <li className="border-t border-slate-200 dark:border-slate-700">
            <a href="/onboarding" className="flex items-center gap-2 px-3 py-2 text-sm text-brand-600 hover:bg-slate-50 dark:hover:bg-slate-800">
              <Plus className="h-4 w-4" /> New organization
            </a>
          </li>
        </ul>
      )}
    </div>
  );
}
