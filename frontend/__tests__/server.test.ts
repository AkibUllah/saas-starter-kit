import { describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({ cookies: () => ({ getAll: () => [], get: () => undefined }) }));

import { pickCurrentOrg } from "@/lib/server";
import type { Org } from "@/lib/types";

const org = (id: string): Org => ({ id, name: id, slug: id, plan: "free", role: "owner", created_at: "2026-01-01T00:00:00Z" });

describe("pickCurrentOrg", () => {
  it("prefers the cookie org when still a member, else the first org", () => {
    const orgs = [org("a"), org("b")];
    expect(pickCurrentOrg(orgs, "b")?.id).toBe("b");
    expect(pickCurrentOrg(orgs, "zzz")?.id).toBe("a");
    expect(pickCurrentOrg(orgs, undefined)?.id).toBe("a");
    expect(pickCurrentOrg([], "a")).toBeNull();
  });
});
