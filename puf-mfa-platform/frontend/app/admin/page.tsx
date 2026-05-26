"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Shield, Users } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AdminLog, AdminStats, AdminUser, api } from "@/lib/api";
import { authStore } from "@/lib/auth-store";

export default function AdminPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [logs, setLogs] = useState<AdminLog[]>([]);

  useEffect(() => {
    if (!loading) {
      if (!user) router.push("/login");
      else if (user.role !== "admin") router.push("/dashboard");
    }
  }, [user, loading, router]);

  useEffect(() => {
    const token = authStore.getToken();
    if (!token || user?.role !== "admin") return;
    Promise.all([api.adminStats(token), api.adminUsers(token), api.adminLogs(token)]).then(
      ([s, u, l]) => {
        setStats(s);
        setUsers(u.users);
        setLogs(l.logs);
      },
    );
  }, [user]);

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
          <Link href="/dashboard" className="btn-ghost text-sm"><ArrowLeft className="h-4 w-4" /> Dashboard</Link>
          <ThemeToggle />
        </div>

        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--primary)]">Admin Panel</h1>
            <p className="text-sm text-[var(--muted)]">Security monitoring & user management</p>
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
                  <span className="text-xs text-[var(--muted)]">{u.puf_enabled ? "PUF ✓" : "No PUF"}</span>
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
                    <p className="font-medium capitalize">{log.event}</p>
                    <p className="text-xs text-[var(--muted)]">{log.factor}</p>
                  </div>
                  <span className={`text-xs font-medium ${log.status === "success" ? "text-[var(--success)]" : "text-red-500"}`}>
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
