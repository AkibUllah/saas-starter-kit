import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 dark:bg-slate-950">
      <div className="mx-auto flex w-full max-w-md items-center justify-between px-4 py-6">
        <Logo />
        <ThemeToggle />
      </div>
      <main className="mx-auto w-full max-w-md flex-1 px-4 pb-16">{children}</main>
    </div>
  );
}
