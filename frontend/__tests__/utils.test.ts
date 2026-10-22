import { describe, expect, it } from "vitest";
import { cn, formatDate, formatMoney, initials, limitLabel, titleCase, usagePercent } from "@/lib/utils";

describe("formatMoney", () => {
  it("drops cents for whole dollars and keeps them otherwise", () => {
    expect(formatMoney(0)).toBe("$0");
    expect(formatMoney(2900)).toBe("$29");
    expect(formatMoney(2950)).toBe("$29.50");
    expect(formatMoney(9900)).toBe("$99");
  });
});

describe("initials", () => {
  it("builds two-letter initials", () => {
    expect(initials("Akib Jafor")).toBe("AJ");
    expect(initials("Fatema Binte Rahman")).toBe("FR");
    expect(initials("fatema")).toBe("FA");
    expect(initials("   ")).toBe("?");
  });
});

describe("quota helpers", () => {
  it("handles unlimited and full quotas", () => {
    expect(limitLabel(-1)).toBe("Unlimited");
    expect(limitLabel(25)).toBe("25");
    expect(usagePercent(3, 3)).toBe(100);
    expect(usagePercent(1, 4)).toBe(25);
    expect(usagePercent(10, -1)).toBe(0);
    expect(usagePercent(7, 3)).toBe(100);
  });
});

describe("misc", () => {
  it("formats dates and titles", () => {
    expect(formatDate("2026-10-20T10:00:00Z")).toBe("20 Oct 2026");
    expect(formatDate(null)).toBe("–");
    expect(titleCase("api_keys")).toBe("Api Keys");
    expect(cn("a", false && "b", "c")).toBe("a c");
  });
});
