"""Unit tests for the custom-field template registry and industry templates."""

from __future__ import annotations

from office_hero.core.industry import Industry
from office_hero.services.custom_field_templates.generic import GenericTemplate
from office_hero.services.custom_field_templates.hvac import HvacTemplate
from office_hero.services.custom_field_templates.pest_control import PestControlTemplate
from office_hero.services.custom_field_templates.plumbing import PlumbingTemplate
from office_hero.services.custom_field_templates.registry import get_template


def test_registry_returns_template_per_industry() -> None:
    """Each Industry value maps to the correct template class."""
    assert isinstance(get_template(Industry.PLUMBING), PlumbingTemplate)
    assert isinstance(get_template(Industry.HVAC), HvacTemplate)
    assert isinstance(get_template(Industry.PEST_CONTROL), PestControlTemplate)
    assert isinstance(get_template(Industry.GENERIC), GenericTemplate)


def test_generic_template_accepts_any_dict() -> None:
    """GenericTemplate.validate() passes through any dict unchanged."""
    t = GenericTemplate()
    payload = {"foo": "bar", "nested": {"x": 1}, "list": [1, 2, 3]}
    result = t.validate(payload)
    assert result == payload


def test_plumbing_template_passes_through_for_now() -> None:
    """PlumbingTemplate.validate() is a Phase-4 pass-through (no rules yet)."""
    t = PlumbingTemplate()
    payload = {"fixture_type": "toilet", "warranty_months": 12}
    result = t.validate(payload)
    assert result == payload


def test_hvac_template_passes_through_for_now() -> None:
    """HvacTemplate.validate() is a Phase-4 pass-through."""
    t = HvacTemplate()
    payload = {"unit_model": "Carrier-XR15", "filter_size": "20x25x4"}
    result = t.validate(payload)
    assert result == payload


def test_pest_control_template_passes_through_for_now() -> None:
    """PestControlTemplate.validate() is a Phase-4 pass-through."""
    t = PestControlTemplate()
    payload = {"pest_type": "termite", "epa_registration_number": "1234-5678"}
    result = t.validate(payload)
    assert result == payload


def test_templates_do_not_share_dict_reference() -> None:
    """validate() must return a copy, not the same dict object."""
    t = GenericTemplate()
    original = {"key": "value"}
    result = t.validate(original)
    assert result is not original
    result["extra"] = "added"
    assert "extra" not in original


def test_registry_industry_attribute_is_correct() -> None:
    """Each template has the right industry class attribute."""
    assert get_template(Industry.PLUMBING).industry == Industry.PLUMBING
    assert get_template(Industry.HVAC).industry == Industry.HVAC
    assert get_template(Industry.PEST_CONTROL).industry == Industry.PEST_CONTROL
    assert get_template(Industry.GENERIC).industry == Industry.GENERIC
