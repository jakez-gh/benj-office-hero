"""Domain-specific exceptions for authentication, permissions, and tenant isolation."""

from __future__ import annotations


class AuthError(Exception):
    """Raised when authentication or token validation fails."""

    def __init__(self, message: str = "Authentication failed", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class PermissionError(Exception):
    """Raised when a user lacks required permissions."""

    def __init__(self, message: str = "Permission denied", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class TenantError(Exception):
    """Raised when tenant isolation or validation fails."""

    def __init__(self, message: str = "Tenant error", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)
