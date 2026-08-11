"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, Download, Pencil, Shield, Users } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AdminCharts } from "@/components/AdminCharts";
import { AdminAnalytics, AdminLog, AdminStats, AdminUser, AttackResult, PufStatus, api } from "@/lib/api";
import { authStore } from "@/lib/auth-store";

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const [attackResult, setAttackResult] = useState<AttackResult | null>(null);
  const [attackLoading, setAttackLoading] = useState("");
  const [replaySessionId, setReplaySessionId] = useState("");
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [pufStatus, setPufStatus] = useState<PufStatus | null>(null);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState("");
  const [editSuccess, setEditSuccess] = useState("");
  const [editForm, setEditForm] = useState({
    username: "",
    full_name: "",
    email: "",
    phone: "",
    account_number: "",
    balance: "",
    password: "",
    is_active: true,
  });

  const [loadError, setLoadError] = useState("");

  const loadData = () => {
    const token = authStore.getToken();
    if (!token || user?.role !== "admin") return;
    setLoadError("");
    Promise.all([
      api.adminStats(token),
      api.adminUsers(token),
      api.adminLogs(token),
      api.adminAnalytics(token),
      api.adminPufStatus(token),
    ])
      .then(([s, u, l, a, p]) => {
        setStats(s);
        setUsers(u.users);
        setLogs(l.logs);
        setAnalytics(a);
        setPufStatus(p);
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load admin data"));
  };

  useEffect(() => {
    if (!loading) {
      if (!user) router.push("/login");
      else if (user.role !== "admin") router.push("/dashboard");
    }
  }, [user, loading, router]);

  useEffect(() => {
    loadData();
  }, [user]);

  const runAttack = async (type: "password-only" | "replay" | "clone") => {
    const token = authStore.getToken();
    if (!token) return;
    setAttackLoading(type);
    setAttackResult(null);
    try {
      const body: { email?: string; session_id?: string } = { email: "demo@bank.com" };
      if (type === "replay") body.session_id = replaySessionId;
      const res = await api.attackDemo(token, type, body);
      setAttackResult(res);
      loadData();
    } catch (e) {
      setAttackResult({ attack: type, result: "ERROR", explanation: String(e) });
    } finally {
      setAttackLoading("");
    }
  };

  const exportCsv = async () => {
    const token = authStore.getToken();
    if (!token) return;
    const res = await fetch(api.exportLogsUrl(), { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) {
      setAttackResult({ attack: "export", result: "ERROR", explanation: "Export failed" });
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "auth_logs.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const startEdit = (u: AdminUser) => {
    setEditingUser(u);
    setEditError("");
    setEditSuccess("");
    setEditForm({
      username: u.username || "",
      full_name: u.full_name || "",
      email: u.email || "",
      phone: u.phone || "",
      account_number: u.account_number || "",
      balance: String(u.balance ?? 0),
      password: "",
      is_active: u.is_active,
    });
  };

  const saveUserEdit = async () => {
    if (!editingUser) return;
    const token = authStore.getToken();
    if (!token) return;
    setEditSaving(true);
    setEditError("");
    setEditSuccess("");
    try {
      await api.adminUpdateUser(token, editingUser.id, {
        username: editForm.username.trim() || undefined,
        full_name: editForm.full_name.trim() || undefined,
        email: editForm.email.trim() || undefined,
        phone: editForm.phone.trim() || undefined,
        account_number: editForm.account_number.trim() || undefined,
        balance: editForm.balance.trim() ? Number(editForm.balance) : undefined,
        password: editForm.password.trim() || undefined,
        is_active: editForm.is_active,
      });
      setEditSuccess("User updated successfully.");
      setEditForm((prev) => ({ ...prev, password: "" }));
      loadData();
    } catch (e) {
      setEditError(e instanceof Error ? e.message : "Failed to update user");
    } finally {
      setEditSaving(false);
    }
  };

  if (loading || !user || user.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
      </div>
    );
  }

  const statCards = stats
    ? [
        { label: "Total Users", value: stats.total_users },
        { label: "PUF Enabled", value: stats.puf_enabled_users },
        { label: "Events (24h)", value: stats.auth_events_24h },
        { label: "Failed (24h)", value: stats.failed_24h },
      ]
    : [];

  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-6xl px-6 py-8">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <Link href="/dashboard" className="btn-ghost text-sm">
            <ArrowLeft className="h-4 w-4" /> Accounts
          </Link>
          <div className="flex gap-2">
            <button onClick={exportCsv} className="btn-outline flex items-center gap-2 py-2 text-sm">
              <Download className="h-4 w-4" /> Export CSV
            </button>
            <ThemeToggle />
          </div>
        </div>

        <div className="mb-8 flex items-center gap-3 border-b border-[var(--border)] pb-6">
          <div className="flex h-9 w-9 items-center justify-center bg-[var(--primary)] text-white">
            <Shield className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-[var(--text)]">Admin Console</h1>
            <p className="text-sm text-[var(--text-secondary)]">
              Monitoring, users, and security tests
            </p>
          </div>
        </div>

        {loadError && (
          <div className="mb-6 rounded-md border border-[var(--error)]/20 bg-[var(--error-subtle)] px-4 py-3 text-sm text-[var(--error)]">
            {loadError}
          </div>
        )}

        {/* Stat cards */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((s) => (
            <div key={s.label} className="bank-card p-5">
              <p className="text-xs font-medium text-[var(--text-secondary)]">{s.label}</p>
              <p className="mt-1.5 text-2xl font-bold tabular-nums text-[var(--text)]">{s.value}</p>
            </div>
          ))}
        </div>

        {/* PUF status */}
        {pufStatus && (
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="bank-card p-4">
              <p className="text-xs font-medium text-[var(--text-secondary)]">Virtual PUF</p>
              <div className="mt-2 flex items-center gap-2">
                <span className={`status-dot ${pufStatus.virtual.online ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
                <span className={`text-sm font-medium ${pufStatus.virtual.online ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                  {pufStatus.virtual.online ? "Online" : "Offline"}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-tertiary)]">{pufStatus.virtual.host}:{pufStatus.virtual.port}</p>
            </div>
            <div className="bank-card p-4">
              <p className="text-xs font-medium text-[var(--text-secondary)]">Hardware PUF (ESP32-C6)</p>
              <div className="mt-2 flex items-center gap-2">
                <span className={`status-dot ${pufStatus.hardware.online ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
                <span className={`text-sm font-medium ${pufStatus.hardware.online ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                  {pufStatus.hardware.online ? "Connected" : "Not connected"}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-tertiary)]">{pufStatus.hardware.port} @ {pufStatus.hardware.baud}</p>
            </div>
            <div className="bank-card p-4">
              <p className="text-xs font-medium text-[var(--text-secondary)]">Email OTP</p>
              <div className="mt-2 flex items-center gap-2">
                <span className={`status-dot ${pufStatus.email_otp_configured ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
                <span className={`text-sm font-medium ${pufStatus.email_otp_configured ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                  {pufStatus.email_otp_configured
                    ? pufStatus.otp_email_provider === "smtp"
                      ? "Gmail SMTP active"
                      : "Email OTP active"
                    : "Not configured"}
                </span>
              </div>
              <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                {pufStatus.email_otp_configured
                  ? "OTP via email"
                  : "Add SMTP_USERNAME + SMTP_PASSWORD (Gmail App Password) to backend/.env"}
              </p>
            </div>
          </div>
        )}

        <AdminCharts data={analytics} />

        {/* Attack demos */}
        <div className="bank-card mt-6 border-[var(--error)]/20 p-6">
          <div className="mb-4 flex items-center gap-2 text-[var(--error)]">
            <AlertTriangle className="h-4 w-4" />
            <h2 className="text-sm font-semibold">Security Penetration Tests</h2>
          </div>
          <p className="mb-4 text-sm text-[var(--text-secondary)]">
            Simulate common attack vectors to verify that multi-factor authentication is blocking unauthorized access. All results are logged.
          </p>
          <div className="mb-4">
            <label className="mb-1.5 block text-xs font-medium text-[var(--text-secondary)]">Session ID for replay test</label>
            <input
              className="input-field font-mono text-xs"
              placeholder="Paste session_id from a completed login"
              value={replaySessionId}
              onChange={(e) => setReplaySessionId(e.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => runAttack("password-only")}
              disabled={!!attackLoading}
              className="btn-outline border-[var(--error)]/30 text-sm text-[var(--error)]"
            >
              {attackLoading === "password-only" ? "Running…" : "Password-Only Bypass"}
            </button>
            <button
              onClick={() => runAttack("replay")}
              disabled={!!attackLoading || !replaySessionId}
              className="btn-outline border-[var(--error)]/30 text-sm text-[var(--error)]"
            >
              {attackLoading === "replay" ? "Running…" : "Replay Attack"}
            </button>
            <button
              onClick={() => runAttack("clone")}
              disabled={!!attackLoading}
              className="btn-outline border-[var(--error)]/30 text-sm text-[var(--error)]"
            >
              {attackLoading === "clone" ? "Running…" : "Clone Device"}
            </button>
          </div>
          {attackResult && (
            <div className="mt-4 rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] p-4">
              <p className="text-sm font-medium text-[var(--text)]">{attackResult.attack}</p>
              <p className={`mt-1 text-sm font-semibold ${attackResult.result === "BLOCKED" ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                {attackResult.result}
              </p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">{attackResult.explanation}</p>
            </div>
          )}
        </div>

        {/* Users + Logs */}
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="bank-card p-6">
            <div className="mb-4 flex items-center gap-2">
              <Users className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-semibold text-[var(--text)]">Customer Accounts</h2>
            </div>
            <div className="max-h-64 divide-y divide-[var(--border)] overflow-y-auto">
              {users.map((u) => (
                <div key={u.id} className="flex items-center justify-between py-3 text-sm">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[var(--text)]">{u.full_name}</p>
                    <p className="truncate text-xs text-[var(--text-tertiary)]">{u.email} · {u.phone}</p>
                    <p className="text-xs text-[var(--text-tertiary)]">
                      @{u.username || "n/a"} · Acct {u.account_number || "n/a"} · <span className="tabular-nums">₹{u.balance ?? 0}</span>
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 pl-3">
                    <span className="text-xs text-[var(--text-tertiary)]">
                      {u.puf_enabled ? `${u.puf_mode} PUF` : "No PUF"}
                    </span>
                    <button
                      onClick={() => startEdit(u)}
                      className="btn-outline flex items-center gap-1 px-2 py-1 text-xs"
                    >
                      <Pencil className="h-3 w-3" /> Edit
                    </button>
                  </div>
                </div>
              ))}
            </div>
            {editingUser && (
              <div className="mt-4 rounded-md border border-[var(--border)] p-4">
                <p className="mb-3 text-sm font-medium text-[var(--text)]">Edit User: {editingUser.full_name}</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <input className="input-field text-sm" placeholder="Username" value={editForm.username} onChange={(e) => setEditForm({ ...editForm, username: e.target.value })} />
                  <input className="input-field text-sm" placeholder="Full name" value={editForm.full_name} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} />
                  <input className="input-field text-sm" placeholder="Email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })} />
                  <input className="input-field text-sm" placeholder="Phone (10 digits)" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} />
                  <input className="input-field text-sm" placeholder="Account number" value={editForm.account_number} onChange={(e) => setEditForm({ ...editForm, account_number: e.target.value })} />
                  <input className="input-field text-sm tabular-nums" placeholder="Balance" type="number" min="0" value={editForm.balance} onChange={(e) => setEditForm({ ...editForm, balance: e.target.value })} />
                  <input className="input-field text-sm sm:col-span-2" placeholder="New password (optional, min 8 chars)" type="password" value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })} />
                </div>
                <label className="mt-3 flex items-center gap-2 text-xs text-[var(--text-secondary)]">
                  <input type="checkbox" checked={editForm.is_active} onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })} />
                  User active
                </label>
                {editError && <p className="mt-2 text-xs text-[var(--error)]">{editError}</p>}
                {editSuccess && <p className="mt-2 text-xs text-[var(--success)]">{editSuccess}</p>}
                <div className="mt-3 flex gap-2">
                  <button onClick={saveUserEdit} disabled={editSaving} className="btn-primary py-2 text-xs">
                    {editSaving ? "Saving..." : "Save Changes"}
                  </button>
                  <button onClick={() => setEditingUser(null)} className="btn-outline py-2 text-xs">
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="bank-card p-6">
            <h2 className="mb-4 text-sm font-semibold text-[var(--text)]">Authentication Logs</h2>
            <div className="max-h-64 divide-y divide-[var(--border)] overflow-y-auto">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-medium capitalize text-[var(--text)]">{log.event.replace("_", " ")}</p>
                    <p className="text-xs text-[var(--text-tertiary)]">{log.factor}</p>
                  </div>
                  <span className={`text-xs font-medium ${log.status === "success" || log.status === "blocked" ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                    {log.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
