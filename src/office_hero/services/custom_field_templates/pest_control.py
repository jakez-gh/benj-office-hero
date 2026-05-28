"""Pest control industry custom-field template.

Phase 4: pass-through only — any dict with string keys is accepted.
Phase 6 will add real validation rules (examples documented below).

Expected Phase-6 fields:
  - ``pest_type``: one of "termite", "rodent", "ant", "cockroach", "bed_bug",
    "wasp", "mosquito", "other"
  - ``chemical_used``: str (product name)
  - ``epa_registration_number``: str (format: NNN-NNNN or NNN-NNNN-NNNNN)
  - ``treatment_area_sqft``: float (> 0)
  - ``follow_up_days``: int (0..90, 0 = no follow-up needed)
"""

from __future__ import annotations

from office_hero.core.industry import Industry


class PestControlTemplate:
    """Pest-control-vertical custom-field validator (Phase 4 pass-through)."""

    industry: Industry = Industry.PEST_CONTROL

    def validate(self, custom_fields: dict) -> dict:
        """Accept any dict — Phase 6 will add field-level rules here."""
        return dict(custom_fields)
