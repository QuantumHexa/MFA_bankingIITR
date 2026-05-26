"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CreditCard, LogOut, Shield, Wallet } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { LiveAuthStepper } from "@/components/LiveAuthStepper";
import { Navbar } from "@/components/Navbar";
import { ApiError, api, AuthLogEntry } from "@/lib/api";
import { authStore } from "@/lib/auth-store";

export default function DashboardPage() {
  const { user, loading, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [logs, setLogs] = useState<AuthLogEntry[]>([]);
  const [pufEnabled, setPufEnabled] = useState(false);
  const [pufMode, setPufMode] = useState("virtual");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  useEffect(() => {
    if (user) {
      setPufEnabled(user.puf_enabled);
      setPufMode(user.puf_mode);
      const token = authStore.getToken();
      if (token) {
        api.authHistory(token).then((r) => setLogs(r.logs)).catch(() => {});
      }
    }
  }, [user]);

  const savePufSettings = async () => {
    const token = authStore.getToken();
    if (!token) return;
    setSaving(true);
    setMsg("");
    try {
      await api.updatePufSettings(token, pufEnabled, pufMode);
      await refreshUser();
      setMsg("Security settings saved.");
    } catch (e) {
      setMsg(e instanceof ApiError ? String(e.message) : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-[var(--muted)]">Welcome back</p>
            <h1 className="text-2xl font-bold text-[var(--primary)]">{user.full_name}</h1>
            <p className="text-sm text-[var(--muted)]">{user.email}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-[var(--success)]/30 bg-[var(--success)]/10 px-3 py-1 text-xs font-medium text-[var(--success)]">
              Authenticated Session
            </span>
            <button onClick={logout} className="btn-outline flex items-center gap-2 py-2 text-sm">
              <LogOut className="h-4 w-4" /> Logout
            </button>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="bank-card rounded-2xl p-6 lg:col-span-2">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-[var(--muted)]">Available Balance</p>
                <p className="mt-1 text-3xl font-bold">₹ 1,24,580.00</p>
              </div>
              <Wallet className="h-7 w-7 text-[var(--primary)]" />
            </div>
            <div className="mt-6 flex gap-3">
              <button className="btn-primary text-sm">Transfer</button>
              <button className="btn-outline text-sm">Pay Bills</button>
            </div>
          </div>

          <div className="bank-card rounded-2xl p-6">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-[var(--primary)]" />
              <h2 className="font-semibold">Security Settings</h2>
            </div>
            <div className="mt-4 space-y-4">
              <label className="flex items-center justify-between">
                <span className="text-sm">PUF Device Auth</span>
                <input type="checkbox" checked={pufEnabled} onChange={(e) => setPufEnabled(e.target.checked)} />
              </label>
              {pufEnabled && (
                <select
                  className="input-field"
                  value={pufMode}
                  onChange={(e) => setPufMode(e.target.value)}
                >
                  <option value="virtual">Virtual Device</option>
                  <option value="hardware">Hardware (CMOD A7)</option>
                </select>
              )}
              <button onClick={savePufSettings} disabled={saving} className="btn-primary w-full text-sm disabled:opacity-50">
                {saving ? "Saving..." : "Save Settings"}
              </button>
              {msg && <p className="text-xs text-[var(--success)]">{msg}</p>}
            </div>
          </div>
        </div>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="bank-card rounded-2xl p-6">
            <div className="mb-4 flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-[var(--primary)]" />
              <h2 className="font-semibold">Recent Activity</h2>
            </div>
            <div className="space-y-2">
              {logs.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">No activity yet.</p>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex items-center justify-between rounded-lg border border-[var(--border)] px-3 py-2 text-sm">
                    <div>
                      <p className="font-medium capitalize">{log.event.replace("_", " ")}</p>
                      <p className="text-xs text-[var(--muted)]">{log.factor} · {new Date(log.created_at).toLocaleString()}</p>
                    </div>
                    <span className={`text-xs font-medium ${log.status === "success" ? "text-[var(--success)]" : "text-red-500"}`}>
                      {log.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
          <LiveAuthStepper />
        </div>

        {user.role === "admin" && (
          <div className="mt-6 text-center">
            <Link href="/admin" className="text-sm font-medium text-[var(--primary)] hover:underline">
              Go to Admin Panel →
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
