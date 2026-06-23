"""One-off: set site_auth_phrase for existing users."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "puf_mfa.db"
PHRASE = "fine for me"

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT username, role, site_auth_phrase FROM users")
print("Before:", cur.fetchall())
cur.execute("UPDATE users SET site_auth_phrase = ? WHERE role != 'admin'", (PHRASE,))
conn.commit()
cur.execute("SELECT username, role, site_auth_phrase FROM users")
print("After:", cur.fetchall())
conn.close()
print("Done.")
