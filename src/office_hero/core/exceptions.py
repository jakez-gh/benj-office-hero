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


class VehicleNotFoundError(Exception):
    """Raised when a vehicle cannot be located in the caller's tenant scope."""

    def __init__(self, message: str = "Vehicle not found", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class VehicleCrewNotFoundError(Exception):
    """Raised when a vehicle crew cannot be located in the caller's tenant scope."""

    def __init__(self, message: str = "Vehicle crew not found", request_id: str | None = None):
        self.message = message
        self.request_id = request_id
        super().__init__(message)


class CrewAssignmentConflictError(Exception):
    """Raised when a vehicle already has a crew assigned for the requested work_date.

    Carries ``existing_crew_id`` so the caller (API layer) can surface it in the
    409 response body and the UI can offer the user a link to the existing crew.
    """

    def __init__(
        self,
        message: str = "Vehicle already has a crew for this date",
        existing_crew_id=None,
        request_id: str | None = None,
    ):
        self.message = message
        self.existing_crew_id = existing_crew_id
        self.request_id = request_id
        super().__init__(message)


class InvalidCrewMemberError(Exception):
    """Raised when a user cannot be placed on a vehicle crew.

    Carries ``user_id`` and a short ``reason`` string so the API layer can
    construct a 422 response with actionable context for the caller.
    """

    def __init__(
        self,
        message: str = "Invalid crew member",
        user_id=None,
        reason: str | None = None,
        request_id: str | None = None,
    ):
        self.message = message
        self.user_id = user_id
        self.reason = reason
        self.request_id = request_id
        super().__init__(message)
