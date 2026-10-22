import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";
import { SessionProvider } from "@/components/dashboard/OrgContext";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { UserMenu } from "@/components/dashboard/UserMenu";
import { VerifyBanner } from "@/components/dashboard/VerifyBanner";
import { ORG_COOKIE, getCurrentUser, getOrgs, pickCurrentOrg } from "@/lib/server";

export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();
  if (!user) redirect("/login?next=/dashboard");
  const orgs = await getOrgs();
  const org = pickCurrentOrg(orgs, cookies().get(ORG_COOKIE)?.value);
  if (!org) redirect("/onboarding");

  return (
    <SessionProvider value={{ user, orgs, org }}>
      <div className="flex min-h-screen flex-col lg:flex-row">
        <Sidebar />
        <div className="flex-1">
          <header className="flex h-16 items-center justify-end border-b border-slate-200 px-6 dark:border-slate-800">
            <UserMenu />
          </header>
          <main className="mx-auto max-w-6xl p-6">
            <VerifyBanner />
            {children}
          </main>
        </div>
      </div>
    </SessionProvider>
  );
}
