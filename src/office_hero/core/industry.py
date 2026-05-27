"""Industry enum — identifies the vertical a Tenant operates in.

Copied onto each Job row at creation time so historical Job data is not
broken if a Tenant later changes their industry setting.
"""

from __future__ import annotations

from enum import StrEnum


class Industry(StrEnum):
    """Industry verticals supported by Office Hero."""

    PLUMBING = "plumbing"
    HVAC = "hvac"
    PEST_CONTROL = "pest_control"
    GENERIC = "generic"
