"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Cpu, KeyRound, MessageCircle, ShieldCheck } from "lucide-react";

type StepStatus = "pending" | "active" | "done" | "failed";

type Step = {
  id: string;
  label: string;
  icon: typeof KeyRound;
  status: StepStatus;
  detail?: string;
};

const DEFAULT_STEPS: Step[] = [
  { id: "password", label: "Password", icon: KeyRound, status: "pending", detail: "Waiting for login" },
  { id: "whatsapp_otp", label: "WhatsApp OTP", icon: MessageCircle, status: "pending", detail: "Pending" },
  { id: "puf", label: "Device (PUF)", icon: Cpu, status: "pending", detail: "Optional factor" },
  { id: "complete", label: "Access Granted", icon: ShieldCheck, status: "pending", detail: "Pending" },
];

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/ws/auth";

export function LiveAuthStepper() {
  const [steps, setSteps] = useState<Step[]>(DEFAULT_STEPS);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let ws: WebSocket;
    try {
      ws = new WebSocket(WS_URL);
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
          const step = msg.data?.step as string;
          const status = msg.data?.status as string;
          setSteps((prev) =>
            prev.map((s) => {
              if (s.id === step) {
                return {
                  ...s,
                  status: status === "success" ? "done" : status === "failed" ? "failed" : status === "pending" ? "active" : "active",
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
              if (status === "success" && s.id === "password" && step === "whatsapp_otp") {
                return s.id === "password" ? { ...s, status: "done", detail: "Verified" } : s;
              }
              return s;
            }),
          );
          if (step === "whatsapp_otp" && status === "success") {
            setSteps((prev) => prev.map((s) => (s.id === "password" ? { ...s, status: "done", detail: "Verified" } : s)));
          }
          if (step === "puf" && status === "pending") {
            setSteps((prev) =>
              prev.map((s) => {
                if (s.id === "password" || s.id === "whatsapp_otp") return { ...s, status: "done", detail: "Verified" };
                if (s.id === "puf") return { ...s, status: "active", detail: "Verifying device..." };
                return s;
              }),
            );
          }
        }
        if (msg.event === "auth_complete") {
          setSteps((prev) =>
            prev.map((s) => ({ ...s, status: "done" as StepStatus, detail: "Verified" })),
          );
        }
      } catch {
        /* ignore */
      }
    };

    return () => ws.close();
  }, []);

  return (
    <div className="bank-card rounded-2xl p-6">
      <div className="mb-5 flex items-center justify-between">
        <h3 className="font-semibold text-[var(--primary)]">Live Authentication Monitor</h3>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            connected ? "bg-[var(--success)]/10 text-[var(--success)]" : "bg-red-500/10 text-red-500"
          }`}
        >
          {connected ? "Connected" : "Offline"}
        </span>
      </div>
      <div className="space-y-3">
        {steps.map((step) => {
          const Icon = step.icon;
          return (
            <div
              key={step.id}
              className={`flex items-center gap-4 rounded-xl border p-4 transition-all ${
                step.status === "active"
                  ? "border-[var(--primary)] bg-[var(--primary)]/5"
                  : step.status === "done"
                    ? "border-[var(--success)]/30 bg-[var(--success)]/5"
                    : step.status === "failed"
                      ? "border-red-400/30 bg-red-400/5"
                      : "border-[var(--border)] opacity-60"
              }`}
            >
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                  step.status === "done"
                    ? "bg-[var(--success)]/15 text-[var(--success)]"
                    : step.status === "active"
                      ? "bg-[var(--primary)]/10 text-[var(--primary)]"
                      : step.status === "failed"
                        ? "bg-red-400/15 text-red-500"
                        : "bg-[var(--border)]/50 text-[var(--muted)]"
                }`}
              >
                {step.status === "done" ? <CheckCircle2 className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{step.label}</p>
                <p className="truncate text-xs text-[var(--muted)]">{step.detail}</p>
              </div>
              {step.status === "active" && (
                <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-[var(--primary)]" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
