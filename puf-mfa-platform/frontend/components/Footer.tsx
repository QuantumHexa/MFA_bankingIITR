import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--surface)] py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 text-xs text-[var(--text-tertiary)] sm:flex-row">
        <p>© 2026 SecureVault. All rights reserved.</p>
        <div className="flex items-center gap-4">
          <span>Multi-factor secured</span>
          <Link href="/admin" className="transition-colors duration-150 hover:text-[var(--text-secondary)]">
            Admin
          </Link>
        </div>
      </div>
    </footer>
  );
}
