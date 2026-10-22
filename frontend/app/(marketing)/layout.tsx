import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";
import { getCurrentUser } from "@/lib/server";

export default async function MarketingLayout({ children }: { children: ReactNode }) {
  const user = await getCurrentUser();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 dark:border-slate-800">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Logo />
          <nav className="flex items-center gap-2 text-sm">
            <Link href="/#features" className="px-3 py-2 text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white">
              Features
            </Link>
            <Link href="/#pricing" className="px-3 py-2 text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white">
              Pricing
            </Link>
            <ThemeToggle />
            {user ? (
              <Link href="/dashboard" className="rounded-md bg-brand-600 px-3 py-2 font-medium text-white hover:bg-brand-700">
                Dashboard
              </Link>
            ) : (
              <>
                <Link href="/login" className="px-3 py-2 font-medium">
                  Sign in
                </Link>
                <Link href="/signup" className="rounded-md bg-brand-600 px-3 py-2 font-medium text-white hover:bg-brand-700">
                  Get started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500 dark:border-slate-800">
        Built in Dhaka · FastAPI + Next.js · MIT licensed
      </footer>
    </div>
  );
}
