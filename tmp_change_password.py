import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "db.sqlite3"
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute(
    "SELECT id, username, email, password FROM auth_user WHERE username = ?",
    ("seller",),
)
rows = cur.fetchall()
print("FOUND", rows)
if not rows:
    raise SystemExit("seller user not found")
userid = rows[0][0]
from django.contrib.auth.hashers import make_password

# We have no Django settings loaded, so use a minimal pbkdf2_sha256 implementation
from hashlib import pbkdf2_hmac
import os

password = "921967"
salt = os.urandom(12)
iterations = 260000
hash_bytes = pbkdf2_hmac("sha256", password.encode(), salt, iterations)
encoded = hash_bytes.hex()
hash_string = f"pbkdf2_sha256${iterations}${salt.hex()}${encoded}"
cur.execute("UPDATE auth_user SET password = ? WHERE id = ?", (hash_string, userid))
conn.commit()
print("UPDATED seller password hash for id", userid)
conn.close()
