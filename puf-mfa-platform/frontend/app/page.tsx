"use client";

import Link from "next/link";
import { ArrowRight, Cpu, KeyRound, MessageCircle } from "lucide-react";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";

const factors = [
  {
    icon: KeyRound,
    title: "Password",
    desc: "Encrypted credential verification as your first security layer.",
  },
  {
    icon: MessageCircle,
    title: "OTP",
    desc: "One-time passcode sent to your registered email address.",
  },
  {
    icon: Cpu,
    title: "Device",
    desc: "Optional hardware verification for high-security accounts.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <Navbar />

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-6xl px-6 pb-16 pt-20 sm:pt-28">
          <p className="text-sm font-medium tracking-wide text-[var(--primary)]">SecureVault</p>
          <h1 className="mt-3 max-w-xl text-4xl font-semibold tracking-tight text-[var(--text)] sm:text-5xl">
            Net Banking
          </h1>
          <p className="mt-4 max-w-md text-base leading-relaxed text-[var(--text-secondary)]">
            Access your accounts securely with multi-factor authentication.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/login" className="btn-primary">
              Sign In <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/signup" className="btn-outline">
              Open an Account
            </Link>
          </div>
        </section>

        {/* Security layers */}
        <section className="border-t border-[var(--border)] bg-[var(--surface)]">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <h2 className="text-sm font-semibold text-[var(--text)]">How we protect your login</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Every session is verified through independent security checks.
            </p>
            <div className="mt-10 grid gap-10 sm:grid-cols-3">
              {factors.map((f, i) => (
                <div key={f.title} className="flex gap-4">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-[var(--border)] bg-[var(--bg)] text-xs font-semibold tabular-nums text-[var(--primary)]">
                    {i + 1}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <f.icon className="h-4 w-4 text-[var(--primary)]" />
                      <h3 className="text-sm font-semibold text-[var(--text)]">{f.title}</h3>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">{f.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
