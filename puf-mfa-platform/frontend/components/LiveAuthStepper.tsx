"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Cpu, KeyRound, MessageCircle, ShieldCheck } from "lucide-react";
import { authStore } from "@/lib/auth-store";

type StepStatus = "pending" | "active" | "done" | "failed";

type Step = {
  id: string;
  label: string;
  icon: typeof KeyRound;
  status: StepStatus;
  detail?: string;
};

const DEFAULT_STEPS: Step[] = [
  { id: "password", label: "Password", icon: KeyRound, status: "pending", detail: "Awaiting credentials" },
  { id: "email_otp", label: "OTP Verification", icon: MessageCircle, status: "pending", detail: "Pending" },
  { id: "puf", label: "Device Check", icon: Cpu, status: "pending", detail: "Optional" },
  { id: "complete", label: "Access Granted", icon: ShieldCheck, status: "pending", detail: "Pending" },
];

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || "";
const WS_MONITOR_URL =
  WS_BASE.replace(/\/ws\/auth\/?$/, "/ws/auth-monitor") ||
  (typeof window !== "undefined"
    ? `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000/ws/auth-monitor`
    : "ws://127.0.0.1:8000/ws/auth-monitor");

export function LiveAuthStepper() {
  const [steps, setSteps] = useState<Step[]>(DEFAULT_STEPS);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket;
    try {
      const token = authStore.getToken();
      const url =
        token && WS_BASE
          ? `${WS_BASE}${WS_BASE.includes("?") ? "&" : "?"}token=${encodeURIComponent(token)}`
          : WS_MONITOR_URL;
      ws = new WebSocket(url);
    } catch {
      return;
    }

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "connected") {
          setConnected(true);
          return;
        }
        if (msg.event === "auth_step") {
          const rawStep = msg.data?.step as string;
          const step = rawStep === "whatsapp_otp" ? "email_otp" : rawStep;
          const status = msg.data?.status as string;
          setSteps((prev) =>
            prev.map((s) => {
              if (s.id === step) {
                return {
                  ...s,
                  status:
                    status === "success"
                      ? "done"
                      : status === "failed"
                        ? "failed"
                        : status === "pending"
                          ? "active"
                          : "active",
                  detail:
                    status === "success"
                      ? "Verified"
                      : status === "failed"
                        ? "Failed"
                        : status === "pending"
                          ? "In progress..."
                          : s.detail,
                };
              }
              if (status === "success" && s.id === "password" && (step === "email_otp" || step === "whatsapp_otp")) {
                return s.id === "password" ? { ...s, status: "done", detail: "Verified" } : s;
              }
              return s;
            }),
          );
          if ((step === "email_otp" || step === "whatsapp_otp") && status === "success") {
            setSteps((prev) =>
              prev.map((s) => (s.id === "password" ? { ...s, status: "done", detail: "Verified" } : s)),
            );
          }
          if (step === "puf" && status === "pending") {
            setSteps((prev) =>
              prev.map((s) => {
                if (s.id === "password" || s.id === "email_otp")
                  return { ...s, status: "done", detail: "Verified" };
                if (s.id === "puf") return { ...s, status: "active", detail: "Verifying device..." };
                return s;
              }),
            );
          }
        }
        if (msg.event === "auth_complete") {
          setSteps((prev) => prev.map((s) => ({ ...s, status: "done" as StepStatus, detail: "Verified" })));
        }
      } catch {
        /* ignore */
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="bank-card p-5">
      <div className="mb-4 flex items-center justify-between border-b border-[var(--border)] pb-3">
        <h3 className="text-sm font-semibold text-[var(--text)]">Authentication Monitor</h3>
        <span className="status-label">
          <span className={`status-dot ${connected ? "bg-[var(--success)]" : "bg-[var(--error)]"}`} />
          {connected ? "Live" : "Offline"}
        </span>
      </div>
      <div className="space-y-1">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 px-2 py-2.5 ${
                step.status === "active"
                  ? "bg-[var(--primary-subtle)]"
                  : step.status === "done"
                    ? "bg-[var(--success-subtle)]"
                    : step.status === "failed"
                      ? "bg-[var(--error-subtle)]"
                      : ""
              }`}
            >
              <div
                className={`flex h-8 w-8 shrink-0 items-center justify-center ${
                  step.status === "done"
                    ? "text-[var(--success)]"
                    : step.status === "active"
                      ? "text-[var(--primary)]"
                      : step.status === "failed"
                        ? "text-[var(--error)]"
                        : "text-[var(--text-tertiary)]"
                }`}
              >
                {step.status === "done" ? <CheckCircle2 className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--text)]">{step.label}</p>
                <p className="truncate text-xs text-[var(--text-tertiary)]">{step.detail}</p>
              </div>
              {step.status === "active" && <span className="status-dot animate-pulse bg-[var(--primary)]" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
