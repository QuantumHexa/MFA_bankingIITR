"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, Download, Shield, Users } from "lucide-react";
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

  const loadData = () => {
    const token = authStore.getToken();
    if (!token || user?.role !== "admin") return;
    Promise.all([
      api.adminStats(token),
      api.adminUsers(token),
      api.adminLogs(token),
      api.adminAnalytics(token),
      api.adminPufStatus(token),
    ]).then(([s, u, l, a, p]) => {
      setStats(s);
      setUsers(u.users);
      setLogs(l.logs);
      setAnalytics(a);
      setPufStatus(p);
    });
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
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "auth_logs.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading || !user || user.role !== "admin") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
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
    <div className="min-h-screen bg-[var(--bg)]">
      <div className="mx-auto max-w-5xl px-6 py-8">
        <div className="mb-8 flex items-center justify-between">
          <Link href="/dashboard" className="btn-ghost text-sm">
            <ArrowLeft className="h-4 w-4" /> Dashboard
          </Link>
          <div className="flex gap-2">
            <button onClick={exportCsv} className="btn-outline flex items-center gap-2 py-2 text-sm">
              <Download className="h-4 w-4" /> Export CSV
            </button>
            <ThemeToggle />
          </div>
        </div>

        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--primary)]">Admin Panel</h1>
            <p className="text-sm text-[var(--muted)]">Security monitoring & attack demonstrations</p>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {statCards.map((s) => (
            <div key={s.label} className="bank-card rounded-xl p-5">
              <p className="text-xs text-[var(--muted)]">{s.label}</p>
              <p className="mt-1 text-2xl font-bold text-[var(--primary)]">{s.value}</p>
            </div>
          ))}
        </div>

        {pufStatus && (
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div className="bank-card rounded-xl p-4">
              <p className="text-xs text-[var(--muted)]">Virtual PUF</p>
              <p className={`mt-1 font-semibold ${pufStatus.virtual.online ? "text-[var(--success)]" : "text-red-500"}`}>
                {pufStatus.virtual.online ? "Online" : "Offline"}
              </p>
              <p className="text-xs text-[var(--muted)]">{pufStatus.virtual.host}:{pufStatus.virtual.port}</p>
            </div>
            <div className="bank-card rounded-xl p-4">
              <p className="text-xs text-[var(--muted)]">Hardware PUF (CMOD A7)</p>
              <p className={`mt-1 font-semibold ${pufStatus.hardware.online ? "text-[var(--success)]" : "text-red-500"}`}>
                {pufStatus.hardware.online ? "Connected" : "Not connected"}
              </p>
              <p className="text-xs text-[var(--muted)]">{pufStatus.hardware.port} @ {pufStatus.hardware.baud}</p>
            </div>
            <div className="bank-card rounded-xl p-4">
              <p className="text-xs text-[var(--muted)]">WhatsApp OTP</p>
              <p className={`mt-1 font-semibold ${pufStatus.twilio_configured ? "text-[var(--success)]" : "text-red-500"}`}>
                {pufStatus.twilio_configured ? "Twilio active" : "Not configured"}
              </p>
              <p className="text-xs text-[var(--muted)]">
                {pufStatus.twilio_configured ? "OTP via WhatsApp" : "Add Twilio credentials to backend/.env"}
              </p>
            </div>
          </div>
        )}

        <AdminCharts data={analytics} />

        {/* Attack demos */}
        <div className="bank-card mt-6 rounded-2xl border-red-200 p-6 dark:border-red-900">
          <div className="mb-4 flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            <h2 className="font-semibold">Attack Simulations</h2>
          </div>
          <p className="mb-4 text-sm text-[var(--muted)]">
            Demonstrate why MFA blocks common attacks. Results are logged to auth history.
          </p>
          <div className="mb-4">
            <label className="mb-1 block text-xs font-medium">Session ID for replay test (optional)</label>
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
              className="btn-outline border-red-300 text-sm text-red-600"
            >
              {attackLoading === "password-only" ? "Running..." : "Password-only bypass"}
            </button>
            <button
              onClick={() => runAttack("replay")}
              disabled={!!attackLoading || !replaySessionId}
              className="btn-outline border-red-300 text-sm text-red-600"
            >
              {attackLoading === "replay" ? "Running..." : "Replay attack"}
            </button>
            <button
              onClick={() => runAttack("clone")}
              disabled={!!attackLoading}
              className="btn-outline border-red-300 text-sm text-red-600"
            >
              {attackLoading === "clone" ? "Running..." : "Clone device"}
            </button>
          </div>
          {attackResult && (
            <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--bg)] p-4">
              <p className="font-semibold">{attackResult.attack}</p>
              <p className={`mt-1 text-sm font-bold ${attackResult.result === "BLOCKED" ? "text-[var(--success)]" : "text-red-500"}`}>
                {attackResult.result}
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">{attackResult.explanation}</p>
            </div>
          )}
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="bank-card rounded-2xl p-6">
            <div className="mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-[var(--primary)]" />
              <h2 className="font-semibold">Users</h2>
            </div>
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {users.map((u) => (
                <div key={u.id} className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                  <div>
                    <p className="font-medium">{u.full_name}</p>
                    <p className="text-xs text-[var(--muted)]">{u.email}</p>
                  </div>
                  <span className="text-xs text-[var(--muted)]">
                    {u.puf_enabled ? `${u.puf_mode} PUF` : "No PUF"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bank-card rounded-2xl p-6">
            <h2 className="mb-4 font-semibold">Auth Logs</h2>
            <div className="max-h-64 space-y-2 overflow-y-auto">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                  <div>
                    <p className="font-medium capitalize">{log.event.replace("_", " ")}</p>
                    <p className="text-xs text-[var(--muted)]">{log.factor}</p>
                  </div>
                  <span className={`text-xs font-medium ${log.status === "success" || log.status === "blocked" ? "text-[var(--success)]" : "text-red-500"}`}>
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
