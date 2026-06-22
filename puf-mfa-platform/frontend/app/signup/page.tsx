"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Landmark } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ApiError, api } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    email: "",
    phone: "",
    full_name: "",
    dob: "",
    initial_deposit: 5000,
    netbanking_enabled: true,
    password: "",
    puf_enabled: false,
    puf_mode: "virtual",
    site_auth_phrase: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [created, setCreated] = useState<{
    account_number: string;
    initial_deposit: number;
    mfa_note: string;
    puf_enrollment?: { status?: string; message?: string; secret_identifier?: string };
  } | null>(null);
  const [secretIdentifier, setSecretIdentifier] = useState("");
  const [readingPuf, setReadingPuf] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.signup({
        ...form,
        site_auth_phrase: form.site_auth_phrase || `${form.username}Auth`,
      });
      setCreated({
        account_number: res.account_number,
        initial_deposit: res.initial_deposit,
        mfa_note: res.mfa_note,
        puf_enrollment: res.puf_enrollment,
      });
      if (res.puf_enrollment?.secret_identifier) {
        setSecretIdentifier(res.puf_enrollment.secret_identifier);
      }
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  const readPufSecret = async () => {
    if (!form.puf_enabled) return;
    setError("");
    setReadingPuf(true);
    try {
      const mode = (form.puf_mode as "virtual" | "hardware") || "virtual";
      const preview = await api.signupPufPreview(mode);
      setSecretIdentifier(preview.secret_identifier);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Could not read PUF");
    } finally {
      setReadingPuf(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--bg)]">
      <div className="hidden w-2/5 bg-[var(--primary)] p-12 text-white lg:flex lg:flex-col lg:justify-center">
        <Landmark className="h-8 w-8 text-[var(--accent)]" />
        <h2 className="mt-6 text-2xl font-bold">Open your account</h2>
        <p className="mt-3 text-sm text-blue-100/70">
          Register with multi-factor security enabled from day one.
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl">
          <div className="mb-6 flex items-center justify-between">
            <Link href="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Home</Link>
            <ThemeToggle />
          </div>

          <div className="bank-card rounded-2xl p-8">
            <h1 className="text-xl font-bold text-[var(--primary)]">Create Account</h1>

            {created ? (
              <div className="mt-6 space-y-3 rounded-xl border border-green-200 bg-green-50 p-5 text-sm dark:border-green-800 dark:bg-green-950/30">
                <p className="font-semibold text-[var(--success)]">Account Created</p>
                <p><span className="font-medium">Your Account No:</span> <span className="font-mono">{created.account_number}</span></p>
                <p><span className="font-medium">Initial Amount:</span> INR {created.initial_deposit.toLocaleString()}</p>
                <p className="text-xs text-[var(--muted)]">{created.mfa_note}</p>
                {created.puf_enrollment?.status === "error" && (
                  <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
                    <p className="font-medium">PUF enrollment did not complete</p>
                    <p className="mt-1">{created.puf_enrollment.message || "Connect your device and enroll from the dashboard after login."}</p>
                  </div>
                )}
                {created.puf_enrollment?.status === "success" && created.puf_enrollment.secret_identifier && (
                  <p className="text-xs"><span className="font-medium">Device ID:</span> <span className="font-mono">{created.puf_enrollment.secret_identifier}</span></p>
                )}
                <button onClick={() => router.push("/login")} className="btn-primary mt-2 w-full">Go to Login</button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                {error && (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">{error}</div>
                )}
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-sm font-medium">Name</label>
                    <input className="input-field" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">DoB</label>
                    <input className="input-field" type="date" required value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">Mobile (10-digit, WhatsApp OTP)</label>
                    <input className="input-field" required pattern="\d{10}" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })} placeholder="7300041850" />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">Email</label>
                    <input className="input-field" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1 block text-sm font-medium">Site Authentication Text</label>
                    <input
                      className="input-field"
                      required
                      minLength={4}
                      maxLength={40}
                      value={form.site_auth_phrase}
                      onChange={(e) => setForm({ ...form, site_auth_phrase: e.target.value })}
                      placeholder="e.g. EmperorAuthentication"
                    />
                    <p className="mt-1 text-xs text-[var(--muted)]">
                      Shown at login so you can verify this is the real SecureVault site (anti-phishing)
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1 block text-sm font-medium">Initial Deposit Amount</label>
                    <input className="input-field" type="number" min={0} value={form.initial_deposit} onChange={(e) => setForm({ ...form, initial_deposit: Number(e.target.value) || 0 })} />
                  </div>
                </div>

                <label className="flex items-start gap-3 rounded-lg border border-[var(--border)] p-3">
                  <input
                    type="checkbox"
                    checked={form.netbanking_enabled}
                    onChange={(e) => setForm({ ...form, netbanking_enabled: e.target.checked })}
                    disabled
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium">Enable Netbanking</p>
                    <p className="text-xs text-[var(--muted)]">Required for username login</p>
                  </div>
                </label>

                {form.netbanking_enabled && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="mb-1 block text-sm font-medium">Username</label>
                      <input className="input-field" required minLength={4} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
                    </div>
                    <div>
                      <label className="mb-1 block text-sm font-medium">Password</label>
                      <input className="input-field" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                    </div>
                  </div>
                )}

                <label className="flex items-start gap-3 rounded-lg border border-[var(--border)] p-3">
                  <input
                    type="checkbox"
                    checked={form.puf_enabled}
                    onChange={(e) => setForm({ ...form, puf_enabled: e.target.checked })}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium">Enable PUF device factor</p>
                    <p className="text-xs text-[var(--muted)]">WhatsApp OTP is always required at login</p>
                  </div>
                </label>

                {form.puf_enabled && (
                  <div className="space-y-3 rounded-lg border border-[var(--border)] p-3">
                    <p className="text-sm font-medium">Select PUF mode (one at a time)</p>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="radio" name="puf_mode" checked={form.puf_mode === "hardware"} onChange={() => setForm({ ...form, puf_mode: "hardware" })} />
                      ESP32-C6 Hardware PUF
                    </label>
                    <label className="flex items-center gap-2 text-sm">
                      <input type="radio" name="puf_mode" checked={form.puf_mode === "virtual"} onChange={() => setForm({ ...form, puf_mode: "virtual" })} />
                      Virtual PUF
                    </label>
                    {form.puf_mode === "hardware" && (
                      <p className="text-xs text-amber-700 dark:text-amber-400">
                        ESP32-C6 must be connected to the PC running the backend at signup time.
                      </p>
                    )}
                    <button type="button" onClick={readPufSecret} className="btn-outline text-sm" disabled={readingPuf}>
                      {readingPuf ? "Reading PUF..." : "Read PUF"}
                    </button>
                    <div className="rounded-lg border border-green-300 bg-green-50 px-3 py-2 text-sm dark:border-green-800 dark:bg-green-950">
                      <span className="font-medium">Secret Identifier:</span>{" "}
                      <span className="font-mono">{secretIdentifier || "Not generated yet"}</span>
                    </div>
                  </div>
                )}

                <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">
                  {loading ? "Creating..." : "Create Account"}
                </button>
              </form>
            )}
          </div>

          <p className="mt-4 text-center text-sm text-[var(--muted)]">
            Already have an account? <Link href="/login" className="font-medium text-[var(--primary)] hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
