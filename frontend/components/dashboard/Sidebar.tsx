"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CreditCard, FolderKanban, KeyRound, LayoutDashboard, ScrollText, Settings, ShieldCheck, Users } from "lucide-react";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/utils";
import { useSession, canManage } from "./OrgContext";
import { OrgSwitcher } from "./OrgSwitcher";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/team", label: "Team", icon: Users },
  { href: "/dashboard/api-keys", label: "API keys", icon: KeyRound, manage: true },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/audit", label: "Audit log", icon: ScrollText, manage: true },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, org } = useSession();
  return (
    <aside className="flex w-full flex-col border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 lg:h-screen lg:w-64 lg:border-b-0 lg:border-r">
      <div className="flex h-16 items-center px-4">
        <Logo href="/dashboard" />
      </div>
      <div className="px-3 pb-3">
        <OrgSwitcher />
      </div>
      <nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:flex-1 lg:flex-col lg:overflow-visible" aria-label="Dashboard">
        {NAV.filter((item) => !item.manage || canManage(org.role)).map(({ href, label, icon: Icon, exact }) => {
          const active = exact ? pathname === href : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium",
                active ? "bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-200" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </Link>
          );
        })}
        <Link
          href="/dashboard"
          className="hidden items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-500 lg:flex"
          aria-hidden="true"
          tabIndex={-1}
        >
          <FolderKanban className="h-4 w-4" /> {org.name}
        </Link>
        {user.is_superuser && (
          <Link
            href="/admin"
            className={cn(
              "flex items-center gap-2 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium lg:mt-auto",
              pathname.startsWith("/admin") ? "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
            )}
          >
            <ShieldCheck className="h-4 w-4" aria-hidden="true" /> Admin
          </Link>
        )}
      </nav>
    </aside>
  );
}
