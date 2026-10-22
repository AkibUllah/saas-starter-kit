import { describe, expect, it } from "vitest";
import { PLANS, isUpgrade, planById, planFor } from "@/lib/plans";

describe("plans", () => {
  it("orders free < pro < business", () => {
    expect(isUpgrade("free", "pro")).toBe(true);
    expect(isUpgrade("pro", "business")).toBe(true);
    expect(isUpgrade("business", "free")).toBe(false);
    expect(isUpgrade("pro", "pro")).toBe(false);
  });
  it("finds the plan that fits a need", () => {
    expect(planFor("projects", 3).id).toBe("free");
    expect(planFor("projects", 4).id).toBe("pro");
    expect(planFor("projects", 500).id).toBe("business");
    expect(planFor("members", 50).id).toBe("business");
  });
  it("falls back to free for unknown ids and mirrors backend limits", () => {
    expect(planById("nope").id).toBe("free");
    expect(PLANS.find((p) => p.id === "business")?.limits.projects).toBe(-1);
    expect(PLANS.map((p) => p.price_cents)).toEqual([0, 2900, 9900]);
  });
});
