"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Cpu, KeyRound, MessageCircle, ShieldCheck } from "lucide-react";

const steps = [
  { id: 1, label: "Password", icon: KeyRound, status: "done" as const },
  { id: 2, label: "WhatsApp OTP", icon: MessageCircle, status: "active" as const },
  { id: 3, label: "PUF Device", icon: Cpu, status: "pending" as const },
  { id: 4, label: "Access Granted", icon: ShieldCheck, status: "pending" as const },
];

export function AuthStepper() {
  return (
    <div className="glass rounded-2xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="font-semibold">Live Auth Flow</h3>
        <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-400">
          WebSocket Connected
        </span>
      </div>

      <div className="space-y-4">
        {steps.map((step, i) => {
          const Icon = step.icon;
          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.15 }}
              className={`flex items-center gap-4 rounded-xl border p-4 transition-all ${
                step.status === "active" ? "step-active" : step.status === "done" ? "step-done" : "opacity-50"
              }`}
            >
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                  step.status === "done"
                    ? "bg-emerald-400/15 text-emerald-400"
                    : step.status === "active"
                      ? "bg-cyan-400/15 text-cyan-400"
                      : "bg-white/5 text-[var(--muted)]"
                }`}
              >
                {step.status === "done" ? <CheckCircle2 className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
              </div>
              <div className="flex-1">
                <p className="font-medium">{step.label}</p>
                <p className="text-xs text-[var(--muted)]">
                  {step.status === "done" && "Verified successfully"}
                  {step.status === "active" && "Waiting for WhatsApp code..."}
                  {step.status === "pending" && "Pending previous step"}
                </p>
              </div>
              {step.status === "active" && (
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400 shadow-neon" />
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
