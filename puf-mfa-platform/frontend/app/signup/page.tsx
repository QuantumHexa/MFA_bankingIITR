"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Landmark } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ApiError, api } from "@/lib/api";
import { WebSerialBridge } from "@/lib/webSerial";

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
  const [signupId] = useState(() => crypto.randomUUID());
  const [devicePubkeyHex, setDevicePubkeyHex] = useState("");
  const [secretIdentifier, setSecretIdentifier] = useState("");
  const [readingPuf, setReadingPuf] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.signup({
        ...form,
        id: signupId,
        device_pubkey_hex: form.puf_mode === "hardware" ? devicePubkeyHex : undefined,
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
      setError(err instanceof ApiError ? String(err.message) : "Registration failed. Please try again.");
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
      if (mode === "hardware") {
        if (!WebSerialBridge.isSupported()) {
          throw new Error("Your browser does not support hardware device enrolment. Please use Chrome or Edge.");
        }
        const bridge = new WebSerialBridge();
        await bridge.connect();
        try {
          const pubkey = await bridge.enroll(signupId);
          setDevicePubkeyHex(pubkey);
          const preview = await api.signupPufPreview("hardware", pubkey);
          setSecretIdentifier(preview.secret_identifier);
        } finally {
          await bridge.disconnect();
        }
      } else {
        const preview = await api.signupPufPreview(mode);
        setSecretIdentifier(preview.secret_identifier);
      }
    } catch (err: any) {
      setError(err instanceof ApiError ? String(err.message) : err.message || "Could not register device.");
    } finally {
      setReadingPuf(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left branding panel */}
      <div className="hidden w-[380px] shrink-0 flex-col justify-center bg-[var(--primary)] p-10 lg:flex">
        <div className="flex h-8 w-8 items-center justify-center bg-white/15 text-white">
          <Landmark className="h-4 w-4" />
        </div>
        <p className="mt-6 text-[10px] font-medium uppercase tracking-wider text-white/50">SecureVault</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Open a new account</h2>
        <p className="mt-3 text-sm leading-relaxed text-white/65">
          Start banking with multi-factor security from day one.
        </p>
      </div>

      {/* Right — form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-2xl">
          <div className="mb-6 flex items-center justify-between">
            <Link href="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Home</Link>
            <ThemeToggle />
          </div>

          <div className="bank-card p-8">
            <h1 className="text-xl font-semibold text-[var(--text)]">Account Registration</h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">Enter your details to open a SecureVault account.</p>

            {created ? (
              <div className="mt-6 space-y-3 rounded-md border border-[var(--success)]/20 bg-[var(--success-subtle)] p-5 text-sm">
                <p className="font-semibold text-[var(--success)]">Account Created Successfully</p>
                <p><span className="font-medium text-[var(--text)]">Account Number:</span> <span className="font-mono text-[var(--text)]">{created.account_number}</span></p>
                <p><span className="font-medium text-[var(--text)]">Opening Balance:</span> <span className="tabular-nums text-[var(--text)]">₹{created.initial_deposit.toLocaleString()}</span></p>
                <p className="text-xs text-[var(--text-secondary)]">{created.mfa_note}</p>
                {created.puf_enrollment?.status === "error" && (
                  <div className="rounded-md border border-[var(--warning)]/20 bg-[var(--warning-subtle)] px-3 py-2 text-xs text-[var(--warning)]">
                    <p className="font-medium">Device enrolment incomplete</p>
                    <p className="mt-1">{created.puf_enrollment.message || "You can register your security device from account settings after login."}</p>
                  </div>
                )}
                {created.puf_enrollment?.status === "success" && created.puf_enrollment.secret_identifier && (
                  <p className="text-xs text-[var(--text)]"><span className="font-medium">Device ID:</span> <span className="font-mono">{created.puf_enrollment.secret_identifier}</span></p>
                )}
                <button onClick={() => router.push("/login")} className="btn-primary mt-2 w-full">Proceed to Login</button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="mt-6 space-y-5">
                {error && (
                  <div className="rounded-md border border-[var(--error)]/20 bg-[var(--error-subtle)] px-4 py-3 text-sm text-[var(--error)]">{error}</div>
                )}
                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Full Name</label>
                    <input className="input-field" required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} placeholder="As per your ID" />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Date of Birth</label>
                    <input className="input-field" type="date" required value={form.dob} onChange={(e) => setForm({ ...form, dob: e.target.value })} />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Mobile Number</label>
                    <input className="input-field" required pattern="\d{10}" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value.replace(/\D/g, "").slice(0, 10) })} placeholder="10-digit mobile number" />
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">Used for account recovery and contact</p>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Email Address</label>
                    <input className="input-field" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="your@email.com" />
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">OTP will be sent to this email during login</p>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Security Phrase (Anti-Phishing)</label>
                    <input
                      className="input-field"
                      required
                      minLength={4}
                      maxLength={40}
                      value={form.site_auth_phrase}
                      onChange={(e) => setForm({ ...form, site_auth_phrase: e.target.value })}
                      placeholder="e.g. MySecureBank2026"
                    />
                    <p className="mt-1 text-xs text-[var(--text-tertiary)]">
                      This phrase will be displayed at login to confirm you are on the genuine SecureVault website.
                    </p>
                  </div>
                  <div className="sm:col-span-2">
                    <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Initial Deposit (₹)</label>
                    <input className="input-field tabular-nums" type="number" min={0} value={form.initial_deposit} onChange={(e) => setForm({ ...form, initial_deposit: Number(e.target.value) || 0 })} />
                  </div>
                </div>

                <label className="flex items-start gap-3 rounded-md border border-[var(--border)] p-3.5">
                  <input
                    type="checkbox"
                    checked={form.netbanking_enabled}
                    onChange={(e) => setForm({ ...form, netbanking_enabled: e.target.checked })}
                    disabled
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium text-[var(--text)]">Enable Net Banking</p>
                    <p className="text-xs text-[var(--text-secondary)]">Required for online account access</p>
                  </div>
                </label>

                {form.netbanking_enabled && (
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Choose Username</label>
                      <input className="input-field" required minLength={4} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="Min. 4 characters" />
                    </div>
                    <div>
                      <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Set Password</label>
                      <input className="input-field" type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Min. 8 characters" />
                    </div>
                  </div>
                )}

                <label className="flex items-start gap-3 rounded-md border border-[var(--border)] p-3.5">
                  <input
                    type="checkbox"
                    checked={form.puf_enabled}
                    onChange={(e) => setForm({ ...form, puf_enabled: e.target.checked })}
                    className="mt-0.5"
                  />
                  <div>
                    <p className="text-sm font-medium text-[var(--text)]">Enable Hardware Device Authentication</p>
                    <p className="text-xs text-[var(--text-secondary)]">Adds a third security layer using a physical device. OTP verification is always required.</p>
                  </div>
                </label>

                {form.puf_enabled && (
                  <div className="space-y-3 rounded-md border border-[var(--border)] p-4">
                    <p className="text-sm font-medium text-[var(--text)]">Device Type</p>
                    <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                      <input type="radio" name="puf_mode" checked={form.puf_mode === "hardware"} onChange={() => setForm({ ...form, puf_mode: "hardware" })} />
                      ESP32-C6 Hardware Device
                    </label>
                    <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
                      <input type="radio" name="puf_mode" checked={form.puf_mode === "virtual"} onChange={() => setForm({ ...form, puf_mode: "virtual" })} />
                      Virtual Security Device
                    </label>
                    {form.puf_mode === "hardware" && (
                      <p className="text-xs text-[var(--warning)]">
                        Connect your ESP32-C6 device via USB, then click Register Device.
                      </p>
                    )}
                    <button type="button" onClick={readPufSecret} className="btn-outline text-sm" disabled={readingPuf}>
                      {readingPuf ? "Registering…" : "Register Device"}
                    </button>
                    <div className="rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] px-3 py-2.5 text-sm">
                      <span className="font-medium text-[var(--text-secondary)]">Device ID:</span>{" "}
                      <span className="font-mono text-[var(--text)]">{secretIdentifier || "Not registered yet"}</span>
                    </div>
                  </div>
                )}

                <button type="submit" disabled={loading} className="btn-primary w-full">
                  {loading ? "Creating Account…" : "Open Account"}
                </button>
              </form>
            )}
          </div>

          <p className="mt-5 text-center text-sm text-[var(--text-secondary)]">
            Already have an account? <Link href="/login" className="font-medium text-[var(--primary)] transition-colors duration-150 hover:text-[var(--primary-hover)]">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
