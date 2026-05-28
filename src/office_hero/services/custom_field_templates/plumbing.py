"""Plumbing industry custom-field template.

Phase 4: pass-through only — any dict with string keys is accepted.
Phase 6 will add real validation rules (examples documented below).

Expected Phase-6 fields:
  - ``fixture_type``: one of "toilet", "sink", "tub", "water_heater", "pipe", "other"
  - ``warranty_months``: int (0..120)
  - ``pipe_material``: one of "copper", "pvc", "cpvc", "pex", "galvanized", "cast_iron"
  - ``shut_off_location``: str (free-text description)
"""

from __future__ import annotations

from office_hero.core.industry import Industry


class PlumbingTemplate:
    """Plumbing-vertical custom-field validator (Phase 4 pass-through)."""

    industry: Industry = Industry.PLUMBING

    def validate(self, custom_fields: dict) -> dict:
        """Accept any dict — Phase 6 will add field-level rules here."""
        return dict(custom_fields)
