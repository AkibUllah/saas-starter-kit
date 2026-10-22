import { describe, expect, it } from "vitest";
import { apiKeySchema, fieldErrors, loginSchema, orgSchema, passwordSchema, resetPasswordSchema, signupSchema } from "@/lib/validation";

describe("password rules", () => {
  it("requires length, a letter and a digit", () => {
    expect(passwordSchema.safeParse("short1").success).toBe(false);
    expect(passwordSchema.safeParse("onlyletters").success).toBe(false);
    expect(passwordSchema.safeParse("12345678").success).toBe(false);
    expect(passwordSchema.safeParse("Str0ngPass").success).toBe(true);
  });
});

describe("signup / login", () => {
  it("normalises email and reports the first error per field", () => {
    const ok = signupSchema.safeParse({ full_name: " Akib ", email: " Akib@Example.COM ", password: "Str0ngPass" });
    expect(ok.success).toBe(true);
    if (ok.success) expect(ok.data).toEqual({ full_name: "Akib", email: "akib@example.com", password: "Str0ngPass" });
    const bad = signupSchema.safeParse({ full_name: "", email: "nope", password: "x" });
    expect(bad.success).toBe(false);
    if (!bad.success) {
      const errors = fieldErrors(bad.error);
      expect(errors.full_name).toBe("Tell us your name");
      expect(errors.email).toBe("Enter a valid email");
      expect(errors.password).toBe("At least 8 characters");
    }
    expect(loginSchema.safeParse({ email: "a@b.co", password: "" }).success).toBe(false);
  });
});

describe("org, api key and reset schemas", () => {
  it("validates slugs, scopes and confirmation", () => {
    expect(orgSchema.safeParse({ name: "Acme", slug: "acme-dhaka" }).success).toBe(true);
    expect(orgSchema.safeParse({ name: "Acme", slug: "" }).success).toBe(true);
    expect(orgSchema.safeParse({ name: "Acme", slug: "Bad Slug" }).success).toBe(false);
    expect(apiKeySchema.safeParse({ name: "CI", scopes: [] }).success).toBe(false);
    const key = apiKeySchema.safeParse({ name: "CI", scopes: ["projects:read"], expires_in_days: "30" });
    expect(key.success && key.data.expires_in_days).toBe(30);
    const reset = resetPasswordSchema.safeParse({ password: "Str0ngPass", confirm: "Other123" });
    expect(reset.success).toBe(false);
    if (!reset.success) expect(fieldErrors(reset.error).confirm).toBe("Passwords do not match");
  });
});
