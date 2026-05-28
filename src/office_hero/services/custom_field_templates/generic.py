"""Generic custom-field template — accepts any string-keyed dict.

Used when a Tenant has no specific industry configured or when the industry
is explicitly ``GENERIC``.
"""

from __future__ import annotations

from office_hero.core.industry import Industry


class GenericTemplate:
    """Pass-through template; accepts any dict with string keys."""

    industry: Industry = Industry.GENERIC

    def validate(self, custom_fields: dict) -> dict:
        """Accept any dict — return it unchanged."""
        return dict(custom_fields)
