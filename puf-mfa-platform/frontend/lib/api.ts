const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((d: { msg: string }) => d.msg).join(", ")
      : data.detail || "Request failed";
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  signup: (body: {
    email: string;
    phone: string;
    full_name: string;
    password: string;
    puf_enabled: boolean;
    puf_mode: string;
  }) => request("/api/auth/signup", { method: "POST", body: JSON.stringify(body) }),

  loginStart: (email: string, password: string) =>
    request<{
      session_id: string;
      requires_puf: boolean;
      puf_mode: string;
      message: string;
    }>("/api/auth/login/start", { method: "POST", body: JSON.stringify({ email, password }) }),

  verifyOtp: (session_id: string, otp: string) =>
    request<{
      session_id?: string;
      challenge?: string;
      nonce?: string;
      next_step: string;
      access_token?: string;
      refresh_token?: string;
    }>("/api/auth/login/verify-otp", { method: "POST", body: JSON.stringify({ session_id, otp }) }),

  verifyPufAuto: (session_id: string) =>
    request<{ access_token: string; refresh_token: string; next_step: string }>(
      "/api/auth/login/verify-puf-auto",
      { method: "POST", body: JSON.stringify({ session_id, otp: "000000" }) },
    ),

  me: (token: string) => request<UserProfile>("/api/auth/me", {}, token),

  updatePufSettings: (token: string, puf_enabled: boolean, puf_mode: string) =>
    request("/api/users/puf-settings", {
      method: "PATCH",
      body: JSON.stringify({ puf_enabled, puf_mode }),
    }, token),

  authHistory: (token: string) =>
    request<{ logs: AuthLogEntry[] }>("/api/users/auth-history", {}, token),

  adminStats: (token: string) => request<AdminStats>("/api/admin/stats", {}, token),

  adminUsers: (token: string) => request<{ total: number; users: AdminUser[] }>("/api/admin/users", {}, token),

  adminLogs: (token: string) =>
    request<{ total: number; logs: AdminLog[] }>("/api/admin/auth-logs?limit=50", {}, token),
};

export type UserProfile = {
  id: string;
  email: string;
  phone: string;
  full_name: string;
  role: string;
  puf_enabled: boolean;
  puf_mode: string;
};

export type AuthLogEntry = {
  event: string;
  factor: string;
  status: string;
  ip_address: string | null;
  created_at: string;
};

export type AdminStats = {
  total_users: number;
  puf_enabled_users: number;
  active_auth_sessions: number;
  auth_events_24h: number;
  success_24h: number;
  failed_24h: number;
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  puf_enabled: boolean;
  puf_mode: string;
  is_active: boolean;
  created_at: string;
};

export type AdminLog = {
  id: string;
  user_id: string | null;
  event: string;
  factor: string;
  status: string;
  created_at: string;
};
