import { buildEncryptedSignupBody } from "./registrationCrypto";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

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

  const res = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: "include" });
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
  signup: async (body: {
    id?: string;
    username: string;
    email: string;
    phone: string;
    full_name: string;
    dob: string;
    initial_deposit: number;
    netbanking_enabled: boolean;
    password: string;
    puf_enabled: boolean;
    puf_mode: string;
    device_pubkey_hex?: string;
    site_auth_phrase?: string;
  }) => {
    const encryptedBody = await buildEncryptedSignupBody(API_URL, body);
    return request<{
      message: string;
      user_id: string;
      account_number: string;
      initial_deposit: number;
      mfa_note: string;
      puf_enabled: boolean;
      puf_enrollment?: { status?: string; secret_identifier?: string; message?: string };
    }>("/api/auth/signup", { method: "POST", body: JSON.stringify(encryptedBody) });
  },

  siteChallenge: (username: string) =>
    request<{ challenge_id: string; phrase: string; message: string }>("/api/auth/site-challenge", {
      method: "POST",
      body: JSON.stringify({ username }),
    }),

  siteChallengeConfirm: (challenge_id: string) =>
    request<{ ok: boolean; challenge_id: string }>("/api/auth/site-challenge/confirm", {
      method: "POST",
      body: JSON.stringify({ challenge_id }),
    }),

  loginStart: (username: string, password: string, site_challenge_id?: string) =>
    request<{
      session_id?: string;
      requires_puf?: boolean;
      puf_mode?: string;
      message: string;
      next_step?: string;
      access_token?: string;
      refresh_token?: string;
      delivery?: string;
      crypto_bundle?: CryptoBundle;
    }>("/api/auth/login/start", {
      method: "POST",
      body: JSON.stringify({ username, password, site_challenge_id }),
    }),

  signupPufPreview: (mode: "virtual" | "hardware", device_pubkey_hex?: string) =>
    request<{ mode: string; challenge?: string; puf_response?: string; secret_identifier: string; device_pubkey_hex?: string }>(
      "/api/auth/signup/puf-preview",
      { method: "POST", body: JSON.stringify({ mode, device_pubkey_hex }) },
    ),

  verifyOtp: (session_id: string, otp: string) =>
    request<{
      session_id?: string;
      challenge?: string;
      nonce?: string;
      next_step: string;
      access_token?: string;
      refresh_token?: string;
    }>("/api/auth/login/verify-otp", { method: "POST", body: JSON.stringify({ session_id, otp }) }),

  resendOtp: (session_id: string) =>
    request<{ message: string; session_id: string }>("/api/auth/login/resend-otp", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  verifyPufAuto: (session_id: string) =>
    request<{ access_token: string; refresh_token: string; next_step: string; puf_verification?: PufVerification }>(
      "/api/auth/login/verify-puf-auto",
      { method: "POST", body: JSON.stringify({ session_id, otp: "000000" }) },
    ),

  pufRead: (session_id: string) =>
    request<PufReadResult>("/api/auth/login/puf-read", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  verifyPuf: (session_id: string, puf_response: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      next_step: string;
      puf_verification?: PufVerification;
      crypto_bundle?: CryptoBundle;
    }>(
      "/api/auth/login/verify-puf",
      { method: "POST", body: JSON.stringify({ session_id, puf_response }) },
    ),

  verifyPufHardware: (session_id: string, proof_hex?: string) =>
    request<{
      access_token: string;
      refresh_token: string;
      next_step: string;
      puf_verification?: HardwarePufVerification;
      crypto_bundle?: CryptoBundle;
    }>("/api/auth/login/verify-puf-hardware", {
      method: "POST",
      body: JSON.stringify({ session_id, proof_hex }),
    }),

  encryptedTransfer: (
    token: string,
    body: { crypto_session_id: string; counter: number; iv: string; ciphertext: string },
  ) =>
    request<{
      status: string;
      message: string;
      transaction: Record<string, unknown>;
      next_counter: number;
    }>("/api/transactions/transfer", { method: "POST", body: JSON.stringify(body) }, token),

  me: (token?: string | null) => request<UserProfile>("/api/auth/me", {}, token ?? null),

  refresh: (refreshToken: string) =>
    request<{ access_token: string; refresh_token: string; token_type: string }>("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  logout: (token?: string | null) => request<{ message: string }>("/api/auth/logout", { method: "POST" }, token ?? null),

  updatePufSettings: (token: string, puf_enabled: boolean, puf_mode: string, device_pubkey_hex?: string) =>
    request("/api/users/puf-settings", {
      method: "PATCH",
      body: JSON.stringify({ puf_enabled, puf_mode, device_pubkey_hex }),
    }, token),

  authHistory: (token: string) =>
    request<{ logs: AuthLogEntry[] }>("/api/users/auth-history", {}, token),

  adminStats: (token: string) => request<AdminStats>("/api/admin/stats", {}, token),

  adminUsers: (token: string) => request<{ total: number; users: AdminUser[] }>("/api/admin/users", {}, token),
  adminUpdateUser: (
    token: string,
    user_id: string,
    body: {
      username?: string;
      email?: string;
      phone?: string;
      full_name?: string;
      password?: string;
      account_number?: string;
      balance?: number;
      is_active?: boolean;
    },
  ) => request<{ message: string; user: AdminUser }>(`/api/admin/users/${user_id}`, { method: "PATCH", body: JSON.stringify(body) }, token),

  adminLogs: (token: string) =>
    request<{ total: number; logs: AdminLog[] }>("/api/admin/auth-logs?limit=50", {}, token),

  adminAnalytics: (token: string) =>
    request<AdminAnalytics>("/api/admin/analytics", {}, token),

  adminPufStatus: (token: string) =>
    request<PufStatus>("/api/admin/puf-status", {}, token),

  attackDemo: (token: string, type: "password-only" | "replay" | "clone", body: { email?: string; session_id?: string }) =>
    request<AttackResult>(`/api/admin/attack-demo/${type}`, { method: "POST", body: JSON.stringify(body) }, token),

  exportLogsUrl: () => `${API_URL}/api/admin/auth-logs/export`,
};

export type UserProfile = {
  id: string;
  username?: string;
  email: string;
  phone: string;
  full_name: string;
  dob?: string;
  account_number?: string;
  balance?: number;
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
  username?: string;
  email: string;
  phone?: string;
  full_name: string;
  dob?: string;
  account_number?: string;
  balance?: number;
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

export type AttackResult = {
  attack: string;
  result: string;
  explanation: string;
};

export type AdminAnalytics = {
  factor_usage: Record<string, number>;
  hourly_events: Record<string, number>;
  success_count: number;
  failed_count: number;
  total_24h: number;
};

export type CryptoBundle = {
  crypto_session_id: string;
  auth_session_id: string;
  proof_hex: string;
  nonce: string;
  challenge: string;
  ratchet_counter: number;
  puf_mode?: string;
};

export type PufVerification = {
  verified: boolean;
  puf_mode: string;
  device_label: string;
  challenge: string;
  puf_response: string;
  reference_response: string;
  hamming_distance: number;
  session_key: string;
  nonce: string;
};

export type PufReadResult = {
  session_id: string;
  puf_mode: string;
  device_label: string;
  secret_identifier?: string;
  challenge?: string;
  nonce: string;
  puf_response?: string;
  reference_response?: string;
  hamming_distance?: number;
  will_verify?: boolean;
  session_key?: string;
  message: string;
  device_status?: string;
  live_pubkey_hex?: string | null;
  stored_pubkey_hex?: string | null;
  pubkey_match?: boolean;
  ready_for_auth?: boolean;
  eph_public_hex?: string;
  customer_id?: string;
};

export type HardwarePufVerification = {
  verified: boolean;
  puf_mode: string;
  device_label: string;
  device_status?: string;
  pubkey_match?: boolean;
  live_pubkey_hex?: string;
  stored_pubkey_hex?: string;
  elapsed_s?: number;
  login_id?: string;
  session_key: string;
  nonce: string;
};

export type PufStatus = {
  virtual: { online: boolean; host: string; port: number; error: string };
  hardware: { online: boolean; port: string; baud: number; status?: string; error: string };
  twilio_configured: boolean;
};
