"""Custom-field template registry.

Provides a single mapping from :class:`~office_hero.core.industry.Industry`
to the corresponding template instance. ``get_template`` is the only
public entry point; callers must never import templates directly so Phase 6
rule additions are transparent.
"""

from __future__ import annotations

from office_hero.core.industry import Industry
from office_hero.services.custom_field_templates import CustomFieldTemplate
from office_hero.services.custom_field_templates.generic import GenericTemplate
from office_hero.services.custom_field_templates.hvac import HvacTemplate
from office_hero.services.custom_field_templates.pest_control import PestControlTemplate
from office_hero.services.custom_field_templates.plumbing import PlumbingTemplate

_REGISTRY: dict[Industry, CustomFieldTemplate] = {
    Industry.PLUMBING: PlumbingTemplate(),
    Industry.HVAC: HvacTemplate(),
    Industry.PEST_CONTROL: PestControlTemplate(),
    Industry.GENERIC: GenericTemplate(),
}


def get_template(industry: Industry) -> CustomFieldTemplate:
    """Return the template for *industry*; fall back to ``GENERIC`` if unknown."""
    return _REGISTRY.get(industry, _REGISTRY[Industry.GENERIC])
