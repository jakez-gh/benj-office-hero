"""Main entry point for Office Hero API."""

import sys

from dotenv import load_dotenv

load_dotenv()  # load .env for local dev; no-op in production where env vars are set directly

# Ensure stdout/stderr use UTF-8 on Windows (default encoding is cp1252 there).
# Without this, structlog's console renderer may raise UnicodeEncodeError when
# error messages contain non-ASCII characters.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from office_hero.api.app import create_app  # noqa: E402

app = create_app()
