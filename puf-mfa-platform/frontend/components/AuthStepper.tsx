"use client";

import { CheckCircle2, Cpu, KeyRound, MessageCircle, ShieldCheck } from "lucide-react";

const steps = [
  { id: 1, label: "Password", icon: KeyRound, status: "done" as const },
  { id: 2, label: "OTP Verification", icon: MessageCircle, status: "active" as const },
  { id: 3, label: "Device Check", icon: Cpu, status: "pending" as const },
  { id: 4, label: "Access Granted", icon: ShieldCheck, status: "pending" as const },
];

export function AuthStepper() {
  return (
    <div className="bank-card p-5">
      <div className="mb-4 flex items-center justify-between border-b border-[var(--border)] pb-3">
        <h3 className="text-sm font-semibold text-[var(--text)]">Authentication Flow</h3>
        <span className="status-label">
          <span className="status-dot bg-[var(--success)]" />
          Connected
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
                    : ""
              }`}
            >
              <div
                className={`flex h-8 w-8 items-center justify-center ${
                  step.status === "done"
                    ? "text-[var(--success)]"
                    : step.status === "active"
                      ? "text-[var(--primary)]"
                      : "text-[var(--text-tertiary)]"
                }`}
              >
                {step.status === "done" ? <CheckCircle2 className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-[var(--text)]">{step.label}</p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {step.status === "done" && "Verified successfully"}
                  {step.status === "active" && "Waiting for OTP code…"}
                  {step.status === "pending" && "Pending previous step"}
                </p>
              </div>
              {step.status === "active" && <span className="status-dot animate-pulse bg-[var(--primary)]" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
