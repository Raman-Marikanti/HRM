import os
import sys
from urllib.parse import urlparse

# Ensure project root is on sys.path so `import app...` works when running this script
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from app.core.config import DATABASE_URL
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("DATABASE_URL not set. Set the environment variable or update app/core/config.py")
    sys.exit(2)

# Normalize SQLAlchemy-style URL (postgresql+psycopg://) to libpq-style for psycopg
if DATABASE_URL.startswith("postgresql+psycopg://"):
    conn_str = DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)
else:
    conn_str = DATABASE_URL

print(f"Using connection string: {conn_str}")

try:
    import psycopg
except Exception as e:
    print("psycopg is not installed in the active Python environment:", e)
    sys.exit(3)

try:
    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, employee_code, roles FROM users ORDER BY id DESC LIMIT 100;")
            rows = cur.fetchall()
            if not rows:
                print("No rows found in users table.")
            else:
                print(f"Found {len(rows)} rows:")
                for r in rows:
                    print(r)
except Exception as e:
    print("Error connecting or querying the database:", e)
    sys.exit(1)

sys.exit(0)
