"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Landmark, LayoutDashboard, LogOut, Shield } from "lucide-react";
import { useAuth } from "./AuthProvider";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center bg-[var(--primary)] text-white">
            <Landmark className="h-4 w-4" />
          </div>
          <div className="leading-tight">
            <span className="block text-sm font-semibold text-[var(--text)]">SecureVault</span>
            <span className="block text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
              Net Banking
            </span>
          </div>
        </Link>
        <nav className="flex items-center gap-1 sm:gap-3">
          <ThemeToggle />
          {user ? (
            <>
              {user.role === "admin" && (
                <Link
                  href="/admin"
                  className={`flex items-center gap-1.5 px-2 py-1.5 text-sm font-medium transition-colors duration-150 ${
                    pathname === "/admin"
                      ? "text-[var(--primary)]"
                      : "text-[var(--text-secondary)] hover:text-[var(--text)]"
                  }`}
                >
                  <Shield className="h-4 w-4" />
                  <span className="hidden sm:inline">Admin</span>
                </Link>
              )}
              <Link
                href="/dashboard"
                className={`flex items-center gap-1.5 px-2 py-1.5 text-sm font-medium transition-colors duration-150 ${
                  pathname === "/dashboard"
                    ? "text-[var(--primary)]"
                    : "text-[var(--text-secondary)] hover:text-[var(--text)]"
                }`}
              >
                <LayoutDashboard className="h-4 w-4" />
                <span className="hidden sm:inline">Accounts</span>
              </Link>
              <button onClick={logout} className="btn-outline flex items-center gap-1.5 py-1.5 text-sm">
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="px-2 py-1.5 text-sm font-medium text-[var(--text-secondary)] transition-colors duration-150 hover:text-[var(--text)]"
              >
                Login
              </Link>
              <Link href="/signup" className="btn-primary py-2 text-sm">
                Open Account
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
