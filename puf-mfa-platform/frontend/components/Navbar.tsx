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
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary)] text-white">
            <Landmark className="h-4 w-4" />
          </div>
          <span className="font-bold text-[var(--primary)]">SecureVault</span>
        </Link>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          {user ? (
            <>
              {user.role === "admin" && (
                <Link
                  href="/admin"
                  className={`flex items-center gap-1.5 text-sm font-medium ${
                    pathname === "/admin" ? "text-[var(--primary)]" : "text-[var(--muted)] hover:text-[var(--primary)]"
                  }`}
                >
                  <Shield className="h-4 w-4" /> Admin
                </Link>
              )}
              <Link
                href="/dashboard"
                className={`flex items-center gap-1.5 text-sm font-medium ${
                  pathname === "/dashboard" ? "text-[var(--primary)]" : "text-[var(--muted)] hover:text-[var(--primary)]"
                }`}
              >
                <LayoutDashboard className="h-4 w-4" /> Dashboard
              </Link>
              <button onClick={logout} className="btn-outline flex items-center gap-1.5 py-2 text-sm">
                <LogOut className="h-4 w-4" /> Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm font-medium text-[var(--muted)] hover:text-[var(--primary)]">
                Login
              </Link>
              <Link href="/signup" className="btn-primary py-2 text-sm">
                Sign Up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
