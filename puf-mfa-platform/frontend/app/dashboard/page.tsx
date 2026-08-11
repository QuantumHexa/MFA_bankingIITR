"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut, Shield } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { LiveAuthStepper } from "@/components/LiveAuthStepper";
import { Navbar } from "@/components/Navbar";
import { ApiError, api, AuthLogEntry } from "@/lib/api";
import { authStore } from "@/lib/auth-store";
import { WebSerialBridge } from "@/lib/webSerial";
import {
  encryptTransaction,
  getOrDeriveRoot,
  loadCryptoBundle,
  nextRatchetCounter,
} from "@/lib/sessionCrypto";

export default function DashboardPage() {
  const { user, loading, logout, refreshUser } = useAuth();
  const router = useRouter();
  const [logs, setLogs] = useState<AuthLogEntry[]>([]);
  const [pufEnabled, setPufEnabled] = useState(false);
  const [pufMode, setPufMode] = useState("virtual");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [msgOk, setMsgOk] = useState(true);
  const [transferLoading, setTransferLoading] = useState(false);
  const [transferResult, setTransferResult] = useState("");

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
    if (!token || !user) return;
    setSaving(true);
    setMsg("");
    setMsgOk(true);
    try {
      let devicePubkeyHex = undefined;
      if (pufEnabled && pufMode === "hardware") {
        if (!WebSerialBridge.isSupported()) {
          throw new Error("Your browser does not support hardware device management. Please use Chrome or Edge.");
        }
        const bridge = new WebSerialBridge();
        await bridge.connect();
        try {
          devicePubkeyHex = await bridge.enroll(user.id);
        } finally {
          await bridge.disconnect();
        }
      }

      await api.updatePufSettings(token, pufEnabled, pufMode, devicePubkeyHex);
      await refreshUser();
      setMsg("Security settings updated successfully.");
      setMsgOk(true);
    } catch (e: any) {
      setMsg(e instanceof ApiError ? String(e.message) : e.message || "Could not update settings. Please try again.");
      setMsgOk(false);
    } finally {
      setSaving(false);
    }
  };

  const demoEncryptedTransfer = async () => {
    const token = authStore.getToken();
    const bundle = loadCryptoBundle();
    if (!token || !bundle) {
      setTransferResult("Please complete a full login with device authentication to enable secure transfers.");
      return;
    }
    setTransferLoading(true);
    setTransferResult("");
    try {
      const root = await getOrDeriveRoot();
      if (!root) throw new Error("Could not establish secure session.");
      const counter = nextRatchetCounter();
      const encrypted = await encryptTransaction(root, counter, {
        type: "transfer",
        amount: 100,
        currency: "INR",
        note: "Secure transfer",
      });
      const res = await api.encryptedTransfer(token, {
        crypto_session_id: bundle.crypto_session_id,
        counter: encrypted.counter,
        iv: encrypted.iv,
        ciphertext: encrypted.ciphertext,
      });
      setTransferResult(`Transfer successful — encrypted with session key (counter ${encrypted.counter} → ${res.next_counter})`);
    } catch (e) {
      setTransferResult(e instanceof ApiError ? String(e.message) : "Transfer failed. Please try again.");
    } finally {
      setTransferLoading(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--border)] border-t-[var(--primary)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-6xl px-6 py-10">
        {/* Header */}
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-[var(--border)] pb-6">
          <div>
            <p className="text-sm text-[var(--text-tertiary)]">Welcome back</p>
            <h1 className="mt-0.5 text-2xl font-semibold text-[var(--text)]">{user.full_name}</h1>
            <p className="mt-0.5 text-sm text-[var(--text-secondary)]">
              Customer ID: {user.username || user.email}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className="status-label text-[var(--success)]">
              <span className="status-dot bg-[var(--success)]" />
              Secure session
            </span>
            <button onClick={logout} className="btn-outline flex items-center gap-2 py-2 text-sm">
              <LogOut className="h-4 w-4" /> Sign Out
            </button>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-3">
          {/* Balance card */}
          <div className="bank-card p-6 lg:col-span-2">
            <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-secondary)]">
              Available Balance
            </p>
            <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-[var(--text)]">
              ₹{(user.balance || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </p>
            {user.account_number && (
              <p className="mt-1 text-xs text-[var(--text-tertiary)]">A/C No. {user.account_number}</p>
            )}
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={demoEncryptedTransfer}
                disabled={transferLoading}
                className="btn-primary text-sm"
              >
                {transferLoading ? "Processing…" : "Send Money"}
              </button>
              <button type="button" disabled className="btn-outline text-sm opacity-50" title="Coming soon">
                Add Money
              </button>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-[var(--text-tertiary)]">
              Transfers are encrypted with session keys from your device authentication.
            </p>
            {transferResult && (
              <p
                className={`mt-2 text-xs font-medium ${
                  transferResult.startsWith("Transfer successful")
                    ? "text-[var(--success)]"
                    : "text-[var(--error)]"
                }`}
              >
                {transferResult}
              </p>
            )}
          </div>

          {/* Security settings */}
          <div className="bank-card p-6">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-[var(--primary)]" />
              <h2 className="text-sm font-semibold text-[var(--text)]">Security Settings</h2>
            </div>
            <div className="mt-5 space-y-4">
              <label className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-secondary)]">Device Authentication</span>
                <input type="checkbox" checked={pufEnabled} onChange={(e) => setPufEnabled(e.target.checked)} />
              </label>
              {pufEnabled && (
                <>
                  <p className="text-xs text-[var(--warning)]">
                    Changing device mode will re-register your security device. Keep your device connected for hardware mode.
                  </p>
                  <select
                    className="input-field text-sm"
                    value={pufMode}
                    onChange={(e) => setPufMode(e.target.value)}
                  >
                    <option value="virtual">Virtual Device</option>
                    <option value="hardware">ESP32-C6 Hardware Device</option>
                  </select>
                </>
              )}
              <button onClick={savePufSettings} disabled={saving} className="btn-primary w-full text-sm">
                {saving ? "Saving…" : "Save Settings"}
              </button>
              {msg && (
                <p className={`text-xs font-medium ${msgOk ? "text-[var(--success)]" : "text-[var(--error)]"}`}>{msg}</p>
              )}
            </div>
          </div>
        </div>

        {/* Activity + Live monitor */}
        <div className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="bank-card p-6">
            <h2 className="mb-4 text-sm font-semibold text-[var(--text)]">Login History</h2>
            {logs.length === 0 ? (
              <p className="py-6 text-center text-sm text-[var(--text-tertiary)]">No recent activity.</p>
            ) : (
              <div className="divide-y divide-[var(--border)]">
                {logs.map((log, i) => (
                  <div key={i} className="flex items-center justify-between py-3 text-sm">
                    <div>
                      <p className="font-medium capitalize text-[var(--text)]">{log.event.replace("_", " ")}</p>
                      <p className="text-xs text-[var(--text-tertiary)]">{log.factor} · {new Date(log.created_at).toLocaleString()}</p>
                    </div>
                    <span className={`text-xs font-medium ${log.status === "success" ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                      {log.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <LiveAuthStepper />
        </div>

        {user.role === "admin" && (
          <div className="mt-6 text-center">
            <Link href="/admin" className="text-sm font-medium text-[var(--primary)] transition-colors duration-150 hover:text-[var(--primary-hover)]">
              Go to Admin Panel →
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}
