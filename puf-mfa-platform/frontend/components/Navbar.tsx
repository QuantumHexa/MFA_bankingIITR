import Link from "next/link";
import { Landmark } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
            <Landmark className="h-4 w-4" />
          </div>
          <span className="font-bold text-[var(--primary)]">SecureVault</span>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Link href="/login" className="text-sm font-medium text-[var(--muted)] hover:text-[var(--primary)]">
            Login
          </Link>
          <Link href="/signup" className="btn-primary py-2 text-sm">
            Sign Up
          </Link>
        </div>
      </div>
    </header>
  );
}
