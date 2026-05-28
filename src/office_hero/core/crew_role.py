"""CrewRole enum — the per-crew role of a technician on a vehicle crew.

This is distinct from the user's RBAC :class:`~office_hero.core.roles.Role`.
A user with RBAC role ``Technician`` typically takes ``LEAD``; a user with
RBAC role ``TechnicianHelper`` defaults to ``HELPER``.
"""

from __future__ import annotations

from enum import StrEnum


class CrewRole(StrEnum):
    """Crew-level role for a :class:`~office_hero.models.vehicle_crew.VehicleCrewMember`."""

    LEAD = "lead"
    """Journey-responsible technician; at most one per crew."""

    HELPER = "helper"
    """Supporting technician; can be multiple per crew."""

    TRAINEE = "trainee"
    """Counted toward crew size but cannot lead a Job."""
