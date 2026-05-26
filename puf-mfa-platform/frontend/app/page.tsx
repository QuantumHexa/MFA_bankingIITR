"use client";

import Link from "next/link";
import { ArrowRight, Cpu, KeyRound, MessageCircle, ShieldCheck } from "lucide-react";
import { Footer } from "@/components/Footer";
import { LiveAuthStepper } from "@/components/LiveAuthStepper";
import { Navbar } from "@/components/Navbar";

const factors = [
  {
    icon: KeyRound,
    title: "Password",
    desc: "Something you know — first gate of authentication.",
  },
  {
    icon: MessageCircle,
    title: "WhatsApp OTP",
    desc: "Something you receive — one-time code on your phone.",
  },
  {
    icon: Cpu,
    title: "PUF Device",
    desc: "Something you have — unclonable hardware identity.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <Navbar />

      <main className="mx-auto max-w-5xl px-6 py-16">
        {/* Hero */}
        <section className="text-center">
          <div className="mx-auto mb-4 inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-1.5 text-xs font-medium text-[var(--primary)]">
            <ShieldCheck className="h-3.5 w-3.5" />
            Multi-Factor Authentication Demo
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--primary)] md:text-4xl">
            Secure Banking Login
          </h1>
          <p className="mx-auto mt-4 max-w-lg text-[var(--muted)]">
            This demo shows how SecureVault protects every login with three independent
            security factors — including hardware-based device authentication.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link href="/login" className="btn-primary">
              Try Secure Login <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/signup" className="btn-outline">
              Create Account
            </Link>
          </div>
        </section>

        {/* 3 Factors */}
        <section className="mt-16 grid gap-4 sm:grid-cols-3">
          {factors.map((f) => (
            <div key={f.title} className="bank-card rounded-xl p-5 text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-[var(--primary)]/10 text-[var(--primary)]">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-xs leading-relaxed text-[var(--muted)]">{f.desc}</p>
            </div>
          ))}
        </section>

        {/* Live monitor */}
        <section className="mt-16">
          <p className="mb-4 text-center text-sm text-[var(--muted)]">
            Watch authentication events in real-time as users log in
          </p>
          <LiveAuthStepper />
        </section>
      </main>

      <Footer />
    </div>
  );
}
