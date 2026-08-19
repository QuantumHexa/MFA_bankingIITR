"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, Cpu, Eye, EyeOff, Key, Landmark } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ApiError, api, CryptoBundle, HardwarePufVerification, PufReadResult, PufVerification } from "@/lib/api";
import { saveCryptoBundle } from "@/lib/sessionCrypto";
import { WebSerialBridge } from "@/lib/webSerial";

function CryptoField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--bg-subtle)] p-3 text-left">
      <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
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
  const [sitePhrase, setSitePhrase] = useState("");
  const [siteChallengeId, setSiteChallengeId] = useState("");
  const [siteConfirmed, setSiteConfirmed] = useState(false);
  const [skipSiteAuth, setSkipSiteAuth] = useState(false);
  const [pufData, setPufData] = useState<PufReadResult | null>(null);
  const [pufVerified, setPufVerified] = useState<PufVerification | HardwarePufVerification | null>(null);
  const [showCryptoDetails, setShowCryptoDetails] = useState(false);
  const [hardwareElapsed, setHardwareElapsed] = useState(0);
  const isHardwarePuf = pufMode === "hardware";

  const totalSteps = (requiresPuf || step >= 3 ? 4 : 3) - (skipSiteAuth ? 1 : 0);
  const displayStep = skipSiteAuth ? Math.max(step, 1) : step + 1;

  const persistCryptoBundle = (bundle?: CryptoBundle) => {
    if (bundle) saveCryptoBundle(bundle);
  };

  const handleUsernameContinue = async () => {
    setError("");
    setLoading(true);
    try {
      if (username.toLowerCase() === "admin") {
        setSkipSiteAuth(true);
        setSitePhrase("");
        setSiteChallengeId("");
        setStep(1);
        return;
      }
      const res = await api.siteChallenge(username);
      setSitePhrase(res.phrase);
      setSiteChallengeId(res.challenge_id);
      setSiteConfirmed(false);
      setSkipSiteAuth(false);
      setStep(1);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "User not found");
    } finally {
      setLoading(false);
    }
  };

  const handlePassword = async () => {
    setError("");
    if (!skipSiteAuth && siteChallengeId && !siteConfirmed) {
      setError("Please verify your Security Phrase shown above before continuing.");
      return;
    }
    setLoading(true);
    try {
      if (siteChallengeId && !skipSiteAuth) {
        await api.siteChallengeConfirm(siteChallengeId);
      }
      const res = await api.loginStart(username, password, siteChallengeId || undefined);
      if (res.next_step === "dashboard" && res.access_token) {
        persistCryptoBundle(res.crypto_bundle);
        await login(res.access_token, res.refresh_token || "");
        router.push("/admin");
        return;
      }
      setSessionId(res.session_id || "");
      setRequiresPuf(Boolean(res.requires_puf));
      setPufMode(res.puf_mode || "virtual");
      setOtpMessage(res.message);
      setStep(2);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (loading && isHardwarePuf && step === 3) {
      const t = setInterval(() => setHardwareElapsed((s) => s + 1), 1000);
      return () => clearInterval(t);
    }
  }, [loading, isHardwarePuf, step]);

  useEffect(() => {
    if (step !== 3) setHardwareElapsed(0);
  }, [step]);

  useEffect(() => {
    if (step !== 3 || !sessionId || !isHardwarePuf) return;
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
        setStep(3);
        return;
      }
      setError("Unexpected response. Please try again.");
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Invalid OTP. Please check and try again.");
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
      setError(e instanceof ApiError ? String(e.message) : "Could not resend OTP. Please try again.");
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
      setError(e instanceof ApiError ? String(e.message) : "Could not connect to security device.");
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
      persistCryptoBundle(res.crypto_bundle);
      await login(res.access_token, res.refresh_token);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (e) {
      setError(e instanceof ApiError ? String(e.message) : "Device verification failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleHardwareAuth = async () => {
    setError("");
    setLoading(true);
    try {
      let currentPufData = pufData;
      if (!currentPufData) {
        currentPufData = await api.pufRead(sessionId);
        setPufData(currentPufData);
      }

      if (!currentPufData.eph_public_hex || !currentPufData.customer_id) {
        throw new Error("Missing security parameters. Please try again.");
      }

      if (!WebSerialBridge.isSupported()) {
        throw new Error("Your browser does not support hardware authentication. Please use Chrome or Edge.");
      }

      const bridge = new WebSerialBridge();
      await bridge.connect();
      let proofHex = "";
      try {
        proofHex = await bridge.authenticate(
          sessionId,
          currentPufData.customer_id,
          currentPufData.eph_public_hex,
          currentPufData.nonce
        );
      } finally {
        await bridge.disconnect();
      }

      const res = await api.verifyPufHardware(sessionId, proofHex);
      setPufVerified(res.puf_verification || null);
      persistCryptoBundle(res.crypto_bundle);
      await login(res.access_token, res.refresh_token);
      setTimeout(() => router.push("/dashboard"), 2500);
    } catch (e: any) {
      const raw = e instanceof ApiError ? String(e.message) : e?.message || "";
      const failedFetch = /failed to fetch/i.test(raw) || e instanceof TypeError;
      setError(
        failedFetch
          ? "ESP32 step could not reach the server. Use Chrome/Edge, plug in the same ESP32 that was enrolled for this account, then click Authenticate again."
          : raw || "Hardware authentication failed. Please reconnect your device."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left branding panel */}
      <div className="hidden w-[400px] shrink-0 flex-col justify-between bg-[var(--primary)] p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center bg-white/15 text-white">
            <Landmark className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <span className="block text-sm font-semibold text-white">SecureVault</span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-white/50">
              Net Banking
            </span>
          </div>
        </div>
        <div>
          <h2 className="text-2xl font-semibold text-white">Sign in to your account</h2>
          <p className="mt-3 text-sm leading-relaxed text-white/65">
            Password, email OTP, and optional device verification keep your banking session secure.
          </p>
        </div>
        <p className="text-xs text-white/40">
          We will never ask for your OTP by phone or email.
        </p>
      </div>

      {/* Right — form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          <div className="mb-6 flex items-center justify-between lg:hidden">
            <Link href="/" className="btn-ghost"><ArrowLeft className="h-4 w-4" /> Home</Link>
            <div className="flex items-center gap-2">
              <Landmark className="h-4 w-4 text-[var(--primary)]" />
              <span className="text-sm font-semibold text-[var(--text)]">SecureVault</span>
            </div>
            <ThemeToggle />
          </div>

          <div className="bank-card p-8">
            <h1 className="text-xl font-semibold text-[var(--text)]">Sign In</h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Step {displayStep} of {totalSteps}
            </p>
            <div className="mt-4 flex gap-1.5">
              {Array.from({ length: totalSteps }).map((_, i) => (
                <div
                  key={i}
                  className={`h-0.5 flex-1 transition-colors duration-200 ${
                    i < displayStep ? "bg-[var(--primary)]" : "bg-[var(--border)]"
                  }`}
                />
              ))}
            </div>

            {error && (
              <div className="mt-4 rounded-md border border-[var(--error)]/20 bg-[var(--error-subtle)] px-4 py-3 text-sm text-[var(--error)]">
                {error}
              </div>
            )}

            {otpMessage && step === 2 && (
              <div className="mt-4 rounded-md border border-[var(--success)]/20 bg-[var(--success-subtle)] px-4 py-3 text-sm text-[var(--success)]">
                {otpMessage}
              </div>
            )}

            {/* Step 0: Username */}
            {step === 0 && (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!loading && username) void handleUsernameContinue();
                }}
              >
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Customer ID / Username</label>
                  <input className="input-field" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" />
                </div>
                <button type="submit" disabled={loading || !username} className="btn-primary w-full">
                  {loading ? "Verifying..." : "Continue"}
                </button>
              </form>
            )}

            {/* Step 1: Password */}
            {step === 1 && (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!loading && password && (skipSiteAuth || siteConfirmed)) void handlePassword();
                }}
              >
                {!skipSiteAuth && sitePhrase && (
                  <div className="space-y-3 rounded-md border border-[var(--primary)]/20 bg-[var(--primary-subtle)] p-4">
                    <p className="text-sm font-medium text-[var(--text)]">
                      Verify your Security Phrase
                    </p>
                    <p className="text-xs text-[var(--text-secondary)]">This phrase confirms you are on the official SecureVault website.</p>
                    <div className="rounded-md border border-[var(--border-strong)] bg-[var(--surface)] px-4 py-3 text-center">
                      <p className="font-mono text-lg font-semibold tracking-wide text-[var(--primary)]">{sitePhrase}</p>
                    </div>
                    <label className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                      <input
                        type="checkbox"
                        checked={siteConfirmed}
                        onChange={(e) => setSiteConfirmed(e.target.checked)}
                        className="mt-0.5"
                      />
                      <span>I recognise this as my Security Phrase</span>
                    </label>
                  </div>
                )}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-[var(--text)]">Password</label>
                  <div className="relative">
                    <input
                      className="input-field pr-12"
                      type={showPass ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter your password"
                    />
                    <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] transition-colors duration-150 hover:text-[var(--text-secondary)]">
                      {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading || !password || (!skipSiteAuth && !!sitePhrase && !siteConfirmed)}
                  className="btn-primary w-full"
                >
                  {loading ? "Verifying..." : skipSiteAuth ? "Sign In" : "Continue"}
                </button>
              </form>
            )}

            {/* Step 2: OTP */}
            {step === 2 && (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!loading && otp.length === 6) void handleOtp();
                }}
              >
                <p className="text-sm text-[var(--text-secondary)]">
                  Enter the 6-digit OTP sent to your registered email address.
                </p>
                <input
                  className="input-field text-center font-mono text-2xl tracking-[0.4em]"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  placeholder="000000"
                  maxLength={6}
                />
                <button type="submit" disabled={loading || otp.length !== 6} className="btn-primary w-full">
                  {loading ? "Verifying..." : "Verify OTP"}
                </button>
                <button type="button" onClick={handleResendOtp} disabled={resendingOtp || !sessionId} className="btn-outline w-full">
                  {resendingOtp ? "Sending..." : "Resend OTP"}
                </button>
              </form>
            )}

            {/* Step 3: Hardware PUF */}
            {step === 3 && isHardwarePuf && (
              <div className="mt-6 space-y-4">
                <div className="text-center">
                  <Cpu className="mx-auto h-10 w-10 text-[var(--primary)]" />
                  <p className="mt-3 text-sm font-medium text-[var(--text)]">Hardware Device Verification</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    Connect your registered security device via USB and click authenticate.
                  </p>
                </div>

                {loading && (
                  <p className="text-center text-xs text-[var(--text-tertiary)]">
                    Verifying device identity… {hardwareElapsed}s elapsed
                  </p>
                )}

                {pufData && !pufVerified && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-md border border-[var(--border)] px-4 py-3 text-sm">
                      <span className="text-[var(--text-secondary)]">Device Status</span>
                      <span className="font-mono font-medium text-[var(--text)]">{pufData.device_status || "unknown"}</span>
                    </div>
                    {pufData.pubkey_match !== undefined && (
                      <div className="flex items-center justify-between rounded-md border border-[var(--border)] px-4 py-3 text-sm">
                        <span className="text-[var(--text-secondary)]">Device Identity</span>
                        <span className={`font-medium ${pufData.pubkey_match ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                          {pufData.pubkey_match ? "Verified" : "Mismatch"}
                        </span>
                      </div>
                    )}
                  </div>
                )}

                {!pufVerified && (
                  <button onClick={handleHardwareAuth} disabled={loading} className="btn-primary flex w-full items-center justify-center gap-2">
                    <Key className="h-4 w-4" />
                    {loading ? "Authenticating device…" : "Authenticate with Security Device"}
                  </button>
                )}

                {pufVerified && (
                  <div className="space-y-3 text-center">
                    <CheckCircle2 className="mx-auto h-12 w-12 text-[var(--success)]" />
                    <p className="text-base font-semibold text-[var(--success)]">Device Verified Successfully</p>
                    <p className="text-sm text-[var(--text-secondary)]">
                      All security checks passed
                      {"elapsed_s" in pufVerified && pufVerified.elapsed_s != null
                        ? ` (${pufVerified.elapsed_s}s)`
                        : ""}
                      {" · Redirecting to your account…"}
                    </p>
                    <CryptoField label="Session Key" value={pufVerified.session_key} />
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Virtual PUF */}
            {step === 3 && !isHardwarePuf && (
              <div className="mt-6 space-y-4">
                <div className="text-center">
                  <Cpu className="mx-auto h-10 w-10 text-[var(--primary)]" />
                  <p className="mt-3 text-sm font-medium text-[var(--text)]">Device Authentication</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    Verifying your registered security device to complete login.
                  </p>
                </div>

                {!pufData && !pufVerified && (
                  <button onClick={handlePufRead} disabled={loading} className="btn-primary w-full">
                    {loading ? "Connecting to device…" : "Verify Security Device"}
                  </button>
                )}

                {pufData && !pufVerified && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between rounded-md border border-[var(--border)] px-4 py-3 text-sm">
                      <span className="text-[var(--text-secondary)]">Device: {pufData.device_label}</span>
                      <span className="font-mono font-medium text-[var(--text)]">{pufData.device_status || "unknown"}</span>
                    </div>
                    {pufData.challenge && (
                      <button
                        type="button"
                        onClick={() => setShowCryptoDetails(!showCryptoDetails)}
                        className="flex w-full items-center justify-between text-xs font-medium text-[var(--primary)] transition-colors duration-150 hover:text-[var(--primary-hover)]"
                      >
                        {showCryptoDetails ? "Hide" : "Show"} technical details
                        {showCryptoDetails ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </button>
                    )}
                    {showCryptoDetails && (
                      <>
                        {pufData.challenge && <CryptoField label="Server Challenge" value={pufData.challenge} />}
                        <CryptoField label="Session Nonce" value={pufData.nonce} />
                        {pufData.puf_response && <CryptoField label="Device Response" value={pufData.puf_response} />}
                        {pufData.reference_response && <CryptoField label="Reference Response" value={pufData.reference_response} />}
                        {pufData.secret_identifier && <CryptoField label="Device Identifier" value={pufData.secret_identifier} />}
                        {pufData.session_key && <CryptoField label="Derived Session Key" value={pufData.session_key} />}
                      </>
                    )}
                    {pufData.hamming_distance !== undefined && (
                      <div className="flex items-center justify-between rounded-md border border-[var(--border)] px-4 py-3 text-sm">
                        <span className="text-[var(--text-secondary)]">Device similarity</span>
                        <span className={`font-mono font-medium ${pufData.will_verify ? "text-[var(--success)]" : "text-[var(--error)]"}`}>
                          {pufData.hamming_distance} bits {pufData.will_verify ? "✓" : "✗"}
                        </span>
                      </div>
                    )}
                    <button
                      onClick={handlePufVerify}
                      disabled={loading || !pufData.puf_response}
                      className="btn-primary flex w-full items-center justify-center gap-2"
                    >
                      <Key className="h-4 w-4" />
                      {loading ? "Verifying…" : "Complete Sign In"}
                    </button>
                    {!pufData.will_verify && pufData.puf_response && (
                      <button type="button" onClick={handlePufRead} disabled={loading} className="btn-outline w-full text-sm">
                        Retry device verification
                      </button>
                    )}
                  </div>
                )}

                {pufVerified && (
                  <div className="space-y-3 text-center">
                    <CheckCircle2 className="mx-auto h-12 w-12 text-[var(--success)]" />
                    <p className="text-base font-semibold text-[var(--success)]">Identity Verified</p>
                    <p className="text-sm text-[var(--text-secondary)]">
                      All security checks passed · Redirecting to your account…
                    </p>
                    <CryptoField label="Session Key" value={pufVerified.session_key} />
                  </div>
                )}
              </div>
            )}
          </div>

          <p className="mt-5 text-center text-sm text-[var(--text-secondary)]">
            Don&apos;t have an account? <Link href="/signup" className="font-medium text-[var(--primary)] transition-colors duration-150 hover:text-[var(--primary-hover)]">Open an account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
