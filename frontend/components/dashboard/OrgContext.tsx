"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Org, User } from "@/lib/types";

export interface Session {
  user: User;
  orgs: Org[];
  org: Org;
}

const Ctx = createContext<Session | null>(null);

export function SessionProvider({ value, children }: { value: Session; children: ReactNode }) {
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const value = useContext(Ctx);
  if (!value) throw new Error("useSession must be used inside the dashboard layout");
  return value;
}

export function canManage(role: string): boolean {
  return role === "owner" || role === "admin";
}
