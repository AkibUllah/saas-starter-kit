"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { LogOut, Settings } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { api } from "@/lib/api";
import { initials } from "@/lib/utils";
import { useSession } from "./OrgContext";

export function UserMenu() {
  const router = useRouter();
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const logout = async () => {
    await api.post("/auth/logout").catch(() => undefined);
    router.replace("/login");
    router.refresh();
  };
  return (
    <div className="flex items-center gap-2">
      <ThemeToggle />
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={open}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white"
          aria-label="Account menu"
        >
          {initials(user.full_name || user.email)}
        </button>
        {open && (
          <div role="menu" className="absolute right-0 z-20 mt-2 w-56 rounded-md border border-slate-200 bg-white p-1 text-sm shadow-lg dark:border-slate-700 dark:bg-slate-900">
            <div className="px-3 py-2">
              <div className="truncate font-medium">{user.full_name}</div>
              <div className="truncate text-xs text-slate-500">{user.email}</div>
            </div>
            <Link role="menuitem" href="/dashboard/settings" className="flex items-center gap-2 rounded px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-800" onClick={() => setOpen(false)}>
              <Settings className="h-4 w-4" /> Settings
            </Link>
            <button role="menuitem" type="button" onClick={logout} className="flex w-full items-center gap-2 rounded px-3 py-2 text-left hover:bg-slate-50 dark:hover:bg-slate-800">
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
