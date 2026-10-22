import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Badge, roleTone, statusTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { UsageMeter } from "@/components/ui/UsageMeter";

describe("Badge tones", () => {
  it("maps roles and statuses to tones", () => {
    expect(roleTone("owner")).toBe("brand");
    expect(roleTone("member")).toBe("neutral");
    expect(statusTone("past_due")).toBe("warning");
    expect(statusTone("canceled")).toBe("danger");
    expect(statusTone("active")).toBe("success");
    render(<Badge tone="danger">revoked</Badge>);
    expect(screen.getByText("revoked").className).toContain("rose");
  });
});

describe("Button", () => {
  it("disables itself while loading", async () => {
    const onClick = vi.fn();
    render(<Button loading onClick={onClick}>Save</Button>);
    const button = screen.getByRole("button", { name: "Save" });
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});

describe("Input", () => {
  it("wires label, error and aria attributes", () => {
    render(<Input label="Email" error="Enter a valid email" defaultValue="x" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email");
  });
});

describe("UsageMeter", () => {
  it("shows used/limit and flags full quotas", () => {
    render(<UsageMeter label="projects" used={3} limit={3} />);
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
    render(<UsageMeter label="api_keys" used={2} limit={-1} />);
    expect(screen.getByText("2 / Unlimited")).toBeInTheDocument();
  });
});
