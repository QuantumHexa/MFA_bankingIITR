import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-[var(--border)] py-8 text-center text-xs text-[var(--muted)]">
      <p>© 2026 SecureVault Bank · PUF-MFA Security Demo</p>
      <p className="mt-1">
        <Link href="/admin" className="hover:text-[var(--primary)]">
          Admin Panel
        </Link>
      </p>
    </footer>
  );
}
