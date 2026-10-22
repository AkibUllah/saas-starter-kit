export type Role = "owner" | "admin" | "member";
export type PlanId = "free" | "pro" | "business";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Org {
  id: string;
  name: string;
  slug: string;
  plan: PlanId;
  role: Role;
  created_at: string;
}

export interface Member {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  joined_at: string;
}

export interface Invite {
  id: string;
  email: string;
  role: Role;
  status: "pending" | "accepted" | "revoked" | "expired";
  expires_at: string;
  created_at: string;
}

export interface InvitePreview {
  org_name: string;
  email: string;
  role: Role;
  expires_at: string;
  status: Invite["status"];
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  masked: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface ApiKeyCreated extends ApiKey {
  key: string;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  slug: string;
  description: string;
  status: "active" | "archived";
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface Plan {
  id: PlanId;
  name: string;
  price_cents: number;
  description: string;
  limits: Record<string, number>;
  features: Record<string, boolean>;
  highlights: string[];
}

export interface Subscription {
  plan: PlanId;
  status: "trialing" | "active" | "past_due" | "canceled";
  provider: string;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_ends_at: string | null;
  cancel_at_period_end: boolean;
  canceled_at: string | null;
  seats: number;
}

export interface BillingOverview {
  subscription: Subscription;
  plan: Plan;
  usage: Record<string, { used: number; limit: number }>;
  features: Record<string, boolean>;
  plans: Plan[];
}

export interface Checkout {
  session_id: string;
  url: string;
  plan: PlanId;
  amount_cents: number;
  status: "open" | "completed" | "expired";
}

export interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_email: string;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  ip: string;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminStats {
  users_total: number;
  users_verified: number;
  users_active_30d: number;
  orgs_total: number;
  projects_total: number;
  subscriptions_by_plan: Record<string, number>;
  subscriptions_by_status: Record<string, number>;
  mrr_cents: number;
  signups_last_30_days: { date: string; count: number }[];
}

export interface AdminUser extends User {
  org_count: number;
}

export interface AdminOrg {
  id: string;
  name: string;
  slug: string;
  plan: PlanId;
  subscription_status: string;
  member_count: number;
  project_count: number;
  created_at: string;
}

export interface ApiErrorBody {
  detail: string;
  code?: string;
  errors?: { field: string; message: string }[];
}
