import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PricingTable } from "@/components/marketing/PricingTable";
import { PLANS } from "@/lib/plans";

describe("PricingTable", () => {
  it("links to signup on the marketing page", () => {
    render(<PricingTable plans={PLANS} />);
    const free = within(screen.getByTestId("plan-free"));
    expect(free.getByRole("link", { name: "Start for free" })).toHaveAttribute("href", "/signup?plan=free");
    const pro = within(screen.getByTestId("plan-pro"));
    expect(pro.getByText("$29")).toBeInTheDocument();
    expect(pro.getByText("Popular")).toBeInTheDocument();
  });

  it("marks the current plan and calls onSelect for upgrades", async () => {
    const onSelect = vi.fn();
    render(<PricingTable plans={PLANS} currentPlan="free" onSelect={onSelect} />);
    expect(within(screen.getByTestId("plan-free")).getByText("Current plan")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Upgrade to Business" }));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "business" }));
  });
});
