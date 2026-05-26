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
    email: "",
    phone: "",
    full_name: "",
    password: "",
    puf_enabled: true,
    puf_mode: "virtual",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.signup(form);
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Signup failed");
    } finally {
      setLoading(false);
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
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center justify-between">
            <Link href="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Home</Link>
            <ThemeToggle />
          </div>

          <div className="bank-card rounded-2xl p-8">
            <h1 className="text-xl font-bold text-[var(--primary)]">Create Account</h1>

            {success ? (
              <div className="mt-6 rounded-lg border border-[var(--success)]/30 bg-[var(--success)]/10 px-4 py-3 text-sm text-[var(--success)]">
                Account created! Redirecting to login...
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                {error && (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</div>
                )}
                <div>
                  <label className="mb-1 block text-sm font-medium">Full Name</label>
                  <input className="input-field" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Email</label>
                  <input className="input-field" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Phone (10 digits)</label>
                  <input className="input-field" required pattern="\d{10}" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="9876543210" />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Password</label>
                  <input className="input-field" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
                </div>
                <label className="flex items-start gap-3 rounded-lg border border-[var(--border)] p-3">
                  <input
                    type="checkbox"
                    checked={form.puf_enabled}
                    onChange={(e) => setForm({ ...form, puf_enabled: e.target.checked })}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium">Enable device authentication (PUF)</p>
                    <p className="text-xs text-[var(--muted)]">Recommended for maximum security</p>
                  </div>
                </label>
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
