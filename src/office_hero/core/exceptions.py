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


class GeocodingError(Exception):
    """Raised when a geocoding adapter fails (network, timeout, parse, allowlist)."""

    def __init__(self, message: str = "Geocoding failed", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class CustomerNotFoundError(Exception):
    """Raised when a customer cannot be located in the caller's tenant scope."""

    def __init__(self, message: str = "Customer not found", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class LocationNotFoundError(Exception):
    """Raised when a location cannot be located in the caller's tenant scope."""

    def __init__(self, message: str = "Location not found", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class DuplicateEmailError(Exception):
    """Raised when a customer email already exists in the same tenant (active)."""

    def __init__(
        self,
        message: str = "A customer with this email already exists in this tenant",
        request_id: str | None = None,
    ):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class JobNotFoundError(Exception):
    """Raised when a job cannot be located in the caller's tenant scope."""

    def __init__(self, message: str = "Job not found", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class InvalidJobTransitionError(Exception):
    """Raised when an illegal job status transition is attempted.

    Carries the source and target statuses so the HTTP exception handler
    can surface them in a structured 422 response body.
    """

    def __init__(
        self,
        from_status,
        to_status,
        message: str | None = None,
        request_id: str | None = None,
    ):
        from office_hero.core.job_status import JobStatus

        self.from_status: JobStatus = from_status
        self.to_status: JobStatus = to_status
        self.message = message or (f"Invalid job status transition: {from_status} -> {to_status}")
        self.request_id = request_id
        super().__init__(self.message)


class CustomFieldValidationError(Exception):
    """Raised when custom_fields fail industry-template validation.

    Carries the field name and a list of human-readable error strings so the
    HTTP exception handler can surface them in a structured 422 response body.
    """

    def __init__(
        self,
        field_name: str,
        errors: list[str],
        message: str | None = None,
        request_id: str | None = None,
    ):
        self.field_name = field_name
        self.errors = errors
        self.message = message or f"Custom field validation failed for '{field_name}'"
        self.request_id = request_id
        super().__init__(self.message)
