"""slowapi rate limiter setup."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global limiter instance — key by client IP address
limiter = Limiter(key_func=get_remote_address)
