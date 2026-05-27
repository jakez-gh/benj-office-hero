"""HVAC industry custom-field template.

Phase 4: pass-through only — any dict with string keys is accepted.
Phase 6 will add real validation rules (examples documented below).

Expected Phase-6 fields:
  - ``unit_model``: str (equipment model identifier)
  - ``refrigerant_lbs``: float (≥ 0)
  - ``filter_size``: str (e.g. "16x20x1", "20x25x4")
  - ``system_type``: one of "central_air", "heat_pump", "mini_split", "furnace", "boiler"
  - ``last_service_date``: ISO date string
"""

from __future__ import annotations

from office_hero.core.industry import Industry


class HvacTemplate:
    """HVAC-vertical custom-field validator (Phase 4 pass-through)."""

    industry: Industry = Industry.HVAC

    def validate(self, custom_fields: dict) -> dict:
        """Accept any dict — Phase 6 will add field-level rules here."""
        return dict(custom_fields)
