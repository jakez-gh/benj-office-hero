"""Custom field template protocol — pluggable per-industry validation seam.

Phase 4 scope: define the protocol and ship pass-through implementations.
Phase 6 will add real validation rules by populating each template's
``validate()`` method — no plumbing changes required.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from office_hero.core.industry import Industry


@runtime_checkable
class CustomFieldTemplate(Protocol):
    """Protocol every industry template must satisfy."""

    industry: Industry  # class-level attribute

    def validate(self, custom_fields: dict) -> dict:
        """Validate *custom_fields* and return the canonicalised dict.

        Raises :class:`~office_hero.core.exceptions.CustomFieldValidationError`
        when the payload violates the template's schema rules.
        """
        ...
