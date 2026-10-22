import { z } from "zod";

export const passwordSchema = z
  .string()
  .min(8, "At least 8 characters")
  .max(128)
  .regex(/[A-Za-z]/, "Must contain a letter")
  .regex(/\d/, "Must contain a number");

export const emailSchema = z.string().trim().toLowerCase().email("Enter a valid email");

export const signupSchema = z.object({
  full_name: z.string().trim().min(1, "Tell us your name").max(120),
  email: emailSchema,
  password: passwordSchema,
});

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Enter your password"),
});

export const orgSchema = z.object({
  name: z.string().trim().min(2, "At least 2 characters").max(120),
  slug: z
    .string()
    .trim()
    .toLowerCase()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Lowercase letters, numbers and dashes")
    .min(2)
    .max(64)
    .optional()
    .or(z.literal("")),
});

export const projectSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(120),
  description: z.string().trim().max(2000).optional().default(""),
});

export const inviteSchema = z.object({
  email: emailSchema,
  role: z.enum(["owner", "admin", "member"]),
});

export const apiKeySchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(80),
  scopes: z.array(z.enum(["org:read", "projects:read", "projects:write"])).min(1, "Pick at least one scope"),
  expires_in_days: z.coerce.number().int().min(1).max(3650).optional(),
});

export const resetPasswordSchema = z
  .object({ password: passwordSchema, confirm: z.string() })
  .refine((v) => v.password === v.confirm, { message: "Passwords do not match", path: ["confirm"] });

export type FieldErrors<T> = Partial<Record<keyof T, string>>;

/** Flatten a zod error into { field: firstMessage }. */
export function fieldErrors<T>(error: z.ZodError<T>): FieldErrors<T> {
  const out: Record<string, string> = {};
  for (const issue of error.issues) {
    const key = String(issue.path[0] ?? "_");
    if (!(key in out)) out[key] = issue.message;
  }
  return out as FieldErrors<T>;
}
