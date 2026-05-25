"""Role enumeration for RBAC system with 8 distinct roles."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Enum representing all RBAC roles in Office Hero.

    Roles follow ServiceTitan/PestPac/Jobber industry standards.
    """

    Owner = "owner"
    # ``Admin`` is the role string emitted by the admin-web shell (see
    # ``apps/admin-web/src/__tests__/App.test.tsx`` and
    # ``apps/admin-web/src/__tests__/UsersPage.test.tsx``). It is reserved for
    # the ADR-060 tenant-admin work and treated as opaque on the API side until
    # then; do not remove without updating those frontend tests first.
    Admin = "admin"
    Operator = "operator"
    OperatorStaff = "operator_staff"
    TenantAdmin = "tenant_admin"
    Sales = "sales"
    Dispatcher = "dispatcher"
    Technician = "technician"
    TechnicianHelper = "technician_helper"
