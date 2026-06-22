"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, Cpu, Eye, EyeOff, Key, Landmark } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ApiError, api, HardwarePufVerification, PufReadResult, PufVerification } from "@/lib/api";

function CryptoField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--bg)] p-3 text-left">
      <p className="text-xs font-medium text-[var(--muted)]">{label}</p>
      <p className="mt-1 break-all font-mono text-xs text-[var(--primary)]">{value}</p>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [step, setStep] = useState(0);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [requiresPuf, setRequiresPuf] = useState(false);
  const [pufMode, setPufMode] = useState("virtual");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [otpMessage, setOtpMessage] = useState("");
  const [resendingOtp, setResendingOtp] = useState(false);
  const [pufData, setPufData] = useState<PufReadResult | null>(null);
  const [pufVerified, setPufVerified] = useState<PufVerification | HardwarePufVerification | null>(null);
  const [showCryptoDetails, setShowCryptoDetails] = useState(false);
  const [hardwareElapsed, setHardwareElapsed] = useState(0);
  const isHardwarePuf = pufMode === "hardware";

  const totalSteps = requiresPuf || step >= 2 ? 3 : 2;

  useEffect(() => {
    if (loading && isHardwarePuf && step === 2) {
      const t = setInterval(() => setHardwareElapsed((s) => s + 1), 1000);
      return () => clearInterval(t);
    }
  }, [loading, isHardwarePuf, step]);

  useEffect(() => {
    if (step !== 2) setHardwareElapsed(0);
  }, [step]);

  useEffect(() => {
    if (step !== 2 || !sessionId || !isHardwarePuf) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.pufRead(sessionId);
        if (!cancelled) setPufData(res);
      } catch {
        /* status check is optional */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [step, sessionId, isHardwarePuf]);

  const handlePassword = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.loginStart(username, password);
      if (res.next_step === "dashboard" && res.access_token) {
        await login(res.access_token, res.refresh_token || "");
        router.push("/admin");
        return;
      }
      setSessionId(res.session_id || "");
      setRequiresPuf(Boolean(res.requires_puf));
      setPufMode(res.puf_mode || "virtual");
      setOtpMessage(res.message);
      setStep(1);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  const handleOtp = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.verifyOtp(sessionId, otp);
      if (res.next_step === "dashboard" && res.access_token) {
        await login(res.access_token, res.refresh_token || "");
        router.push("/dashboard");
        return;
      }
      if (res.next_step === "verify_puf") {
        setPufData(null);
        setPufVerified(null);
        setStep(2);
        return;
      }
      setError("Unexpected login step. Please try again.");
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Invalid OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setError("");
    setResendingOtp(true);
    try {
      const res = await api.resendOtp(sessionId);
      setOtpMessage(res.message);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Could not resend OTP");
    } finally {
      setResendingOtp(false);
    }
  };

  const handlePufRead = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.pufRead(sessionId);
      setPufData(res);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Could not read PUF device");
    } finally {
      setLoading(false);
    }
  };

  const handlePufVerify = async () => {
    if (!pufData?.puf_response) return;
    setError("");
    setLoading(true);
    try {
      const res = await api.verifyPuf(sessionId, pufData.puf_response);
      setPufVerified(res.puf_verification || null);
      await login(res.access_token, res.refresh_token);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "PUF verification failed");
    } finally {
      setLoading(false);
    }
  };

  const handleHardwareAuth = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.verifyPufHardware(sessionId);
      setPufVerified(res.puf_verification || null);
      await login(res.access_token, res.refresh_token);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "ESP32 device authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[var(--bg)]">
      <div className="hidden w-1/2 flex-col justify-between bg-[var(--primary)] p-12 text-white lg:flex">
        <div className="flex items-center gap-3">
          <Landmark className="h-7 w-7 text-[var(--accent)]" />
          <span className="text-lg font-bold">SecureVault Bank</span>
        </div>
        <div>
          <h2 className="text-2xl font-bold">Secure Net Banking</h2>
          <p className="mt-3 max-w-sm text-sm text-blue-100/70">
            Login is protected by password, WhatsApp OTP, and optional device authentication.
          </p>
        </div>
        <p className="text-xs text-blue-100/40">Never share your OTP with anyone.</p>
      </div>

      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-lg">
          <div className="mb-6 flex items-center justify-between lg:hidden">
            <Link href="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Home</Link>
            <div className="flex items-center gap-2">
              <Landmark className="h-5 w-5 text-[var(--primary)]" />
              <span className="text-sm font-bold text-[var(--primary)]">SecureVault</span>
            </div>
            <ThemeToggle />
          </div>

          <div className="bank-card rounded-2xl p-8">
            <h1 className="text-xl font-bold text-[var(--primary)]">Sign In</h1>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Step {step + 1} of {totalSteps}
            </p>
            <div className="mt-3 flex gap-1">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-full transition-colors ${
                    i <= step ? "bg-[var(--primary)]" : "bg-[var(--border)]"
                  }`}
                />
              ))}
            </div>

            {error && (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400">
                {error}
              </div>
            )}

            {otpMessage && step === 1 && (
              <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
                {otpMessage}
              </div>
            )}

            {step === 0 && (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!loading && username && password) void handlePassword();
                }}
              >
                <div>
                  <label className="mb-1 block text-sm font-medium">Username</label>
                  <input className="input-field" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="your_username" />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Password</label>
                  <div className="relative">
                    <input
                      className="input-field pr-12"
                      type={showPass ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Password"
                    />
                    <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)]">
                      {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading || !username || !password} className="btn-primary w-full disabled:opacity-50">
                  {loading ? "Verifying..." : "Continue"}
                </button>
              </form>
            )}

            {step === 1 && (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!loading && otp.length === 6) void handleOtp();
                }}
              >
                <p className="text-sm text-[var(--muted)]">
                  Enter the 6-digit OTP sent to your WhatsApp number
                </p>
                <input
                  className="input-field text-center font-mono text-2xl tracking-[0.4em]"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  maxLength={6}
                />
                <button type="submit" disabled={loading || otp.length !== 6} className="btn-primary w-full disabled:opacity-50">
                  {loading ? "Verifying..." : "Verify OTP"}
                </button>
                <button type="button" onClick={handleResendOtp} disabled={resendingOtp || !sessionId} className="btn-outline w-full disabled:opacity-50">
                  {resendingOtp ? "Resending..." : "Resend OTP"}
                </button>
              </form>
            )}

            {step === 2 && isHardwarePuf && (
              <div className="mt-6 space-y-4">
                <div className="text-center">
                  <Cpu className="mx-auto h-12 w-12 text-[var(--primary)]" />
                  <p className="mt-2 font-medium">ESP32-C6 Hardware PUF Authentication</p>
                  <p className="text-sm text-[var(--muted)]">
                    Close Thonny/serial monitors, keep ESP32 on USB (COM port), then authenticate
                  </p>
                </div>

                {loading && (
                  <p className="text-center text-xs text-[var(--muted)]">
                    PUF reconstruction may take up to 2 minutes… {hardwareElapsed}s elapsed
                  </p>
                )}

                {pufData && !pufVerified && (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-[var(--border)] px-4 py-3 text-sm">
                      <p className="text-[var(--muted)]">Device status</p>
                      <p className="font-mono font-medium">{pufData.device_status || "unknown"}</p>
                    </div>
                    {pufData.pubkey_match !== undefined && (
                      <div className="flex items-center justify-between rounded-lg border border-[var(--border)] px-4 py-3 text-sm">
                        <span className="text-[var(--muted)]">Stored pubkey match</span>
                        <span className={`font-bold ${pufData.pubkey_match ? "text-[var(--success)]" : "text-red-500"}`}>
                          {pufData.pubkey_match ? "Yes" : "No"}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {!pufVerified && (
                  <button onClick={handleHardwareAuth} disabled={loading} className="btn-primary flex w-full items-center justify-center gap-2 disabled:opacity-50">
                    <Key className="h-4 w-4" />
                    {loading ? "Authenticating with ESP32… (PUF may take up to 2 min)" : "Authenticate with ESP32 Device"}
                  </button>
                )}

                {pufVerified && (
                  <div className="space-y-3 text-center">
                    <CheckCircle2 className="mx-auto h-14 w-14 text-[var(--success)]" />
                    <p className="text-lg font-semibold text-[var(--success)]">ESP32 Device Authenticated</p>
                    <p className="text-sm text-[var(--muted)]">
                      MFA proof verified
                      {"elapsed_s" in pufVerified && pufVerified.elapsed_s != null
                        ? ` in ${pufVerified.elapsed_s}s`
                        : ""}
                      {" · Redirecting to dashboard..."}
                    </p>
                    <CryptoField label="Session Key" value={pufVerified.session_key} />
                  </div>
                )}
              </div>
            )}

            {step === 2 && !isHardwarePuf && (
              <div className="mt-6 space-y-4">
                <div className="text-center">
                  <Cpu className="mx-auto h-12 w-12 text-[var(--primary)]" />
                  <p className="mt-2 font-medium">Virtual PUF Device Authentication</p>
                  <p className="text-sm text-[var(--muted)]">
                    Step 1: Read response from virtual PUF bridge · Step 2: Verify & derive session key
                  </p>
                </div>

                {!pufData && !pufVerified && (
                  <button onClick={handlePufRead} disabled={loading} className="btn-primary w-full disabled:opacity-50">
                    {loading ? "Contacting PUF bridge..." : "Read PUF Response"}
                  </button>
                )}

                {pufData && !pufVerified && (
                  <div className="space-y-3">
                    <div className="rounded-lg border border-[var(--border)] px-4 py-3 text-sm">
                      <p className="text-[var(--muted)]">Device: {pufData.device_label}</p>
                      <p className="font-mono font-medium">{pufData.device_status || "unknown"}</p>
                    </div>
                    {pufData.challenge && (
                      <button
                        type="button"
                        onClick={() => setShowCryptoDetails(!showCryptoDetails)}
                        className="flex w-full items-center justify-between text-xs font-medium text-[var(--primary)]"
                      >
                        {showCryptoDetails ? "Hide" : "Show"} technical details
                        {showCryptoDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                    )}
                    {showCryptoDetails && (
                      <>
                        {pufData.challenge && <CryptoField label="Server Challenge" value={pufData.challenge} />}
                        <CryptoField label="Session Nonce" value={pufData.nonce} />
                        {pufData.puf_response && <CryptoField label="PUF Response" value={pufData.puf_response} />}
                        {pufData.reference_response && <CryptoField label="Reference Response" value={pufData.reference_response} />}
                        {pufData.secret_identifier && <CryptoField label="Secret Identifier" value={pufData.secret_identifier} />}
                        {pufData.session_key && <CryptoField label="Derived Session Key" value={pufData.session_key} />}
                      </>
                    )}
                    {pufData.hamming_distance !== undefined && (
                      <div className="flex items-center justify-between rounded-lg border border-[var(--border)] px-4 py-3 text-sm">
                        <span className="text-[var(--muted)]">Hamming distance</span>
                        <span className={`font-mono font-bold ${pufData.will_verify ? "text-[var(--success)]" : "text-red-500"}`}>
                          {pufData.hamming_distance} bits {pufData.will_verify ? "✓" : "✗"}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={handlePufVerify}
                      disabled={loading || !pufData.puf_response}
                      className="btn-primary flex w-full items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <Key className="h-4 w-4" />
                      {loading ? "Verifying..." : "Verify PUF & Complete Login"}
                    </button>
                    {!pufData.will_verify && pufData.puf_response && (
                      <button type="button" onClick={handlePufRead} disabled={loading} className="btn-outline w-full text-sm">
                        Re-read PUF device
                      </button>
                    )}
                  </div>
                )}

                {pufVerified && (
                  <div className="space-y-3 text-center">
                    <CheckCircle2 className="mx-auto h-14 w-14 text-[var(--success)]" />
                    <p className="text-lg font-semibold text-[var(--success)]">PUF Verified Successfully</p>
                    <p className="text-sm text-[var(--muted)]">
                      Device authenticated · Session key derived · Redirecting to dashboard...
                    </p>
                    <CryptoField label="Final Session Key" value={pufVerified.session_key} />
                  </div>
                )}
              </div>
            )}
          </div>

          <p className="mt-4 text-center text-sm text-[var(--muted)]">
            No account? <Link href="/signup" className="font-medium text-[var(--primary)] hover:underline">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
