"""Role enumeration for RBAC system with 8 distinct roles."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Enum representing all RBAC roles in Office Hero.

    Roles follow ServiceTitan/PestPac/Jobber industry standards.
    """

    Owner = "owner"
    Operator = "operator"
    OperatorStaff = "operator_staff"
    TenantAdmin = "tenant_admin"
    Sales = "sales"
    Dispatcher = "dispatcher"
    Technician = "technician"
    TechnicianHelper = "technician_helper"

    def __str__(self) -> str:
        return self.value
