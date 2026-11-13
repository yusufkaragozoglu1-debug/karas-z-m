"""Run the dev server with production-like settings (DEBUG=False) on http://localhost:8000.

Usage (from the project root):  python scripts/run_prodlike.py [port]

- Forces DJANGO_DEBUG=False even if .env / .env.local say True.
- Takes DJANGO_SECRET_KEY and the Transaction-pooler DATABASE_URL (port 6543, what Vercel
  will use) from the *commented* "Vercel" lines in .env.local, so nothing is hard-coded here.
- Allows plain http on localhost (SECURE_SSL_REDIRECT off) so you can browse it locally.
This talks to the REAL database configured in .env.local.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def vercel_value(name):
    """Read `# NAME=value` from .env.local (the lines prepared for the Vercel dashboard)."""
    path = ROOT / ".env.local"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"# {name}="):
                return line.split("=", 1)[1].strip()
    return ""


overrides = {
    "DJANGO_DEBUG": "False",
    "ALLOWED_HOSTS": "localhost,127.0.0.1",
    "SECURE_SSL_REDIRECT": "False",
}
secret = vercel_value("DJANGO_SECRET_KEY") or os.environ.get("DJANGO_SECRET_KEY", "")
database = vercel_value("DATABASE_URL")
if secret:
    overrides["DJANGO_SECRET_KEY"] = secret
if database:
    overrides["DATABASE_URL"] = database

# settings.py loads .env then .env.local (override=True); re-apply our values afterwards.
import dotenv  # noqa: E402

_original = dotenv.load_dotenv


def _load_dotenv(*args, **kwargs):
    result = _original(*args, **kwargs)
    os.environ.update(overrides)
    return result


dotenv.load_dotenv = _load_dotenv
os.environ.update(overrides)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

port = sys.argv[1] if len(sys.argv) > 1 else "8000"
from django.core.management import execute_from_command_line  # noqa: E402

print(f"DEBUG=False | DB port {'6543 (transaction pooler)' if database else 'from .env.local'} | http://localhost:{port}")
execute_from_command_line(["manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"])
