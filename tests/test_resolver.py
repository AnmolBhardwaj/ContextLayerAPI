# tests/test_resolver.py

import pytest

from src.core.resolver import resolve_context


def test_known_domain_and_intent():
    all_sections, source_files, active_intent, include_keys = resolve_context(
        domain="banking",
        intent="summarise",
    )
    assert isinstance(all_sections, dict)
    assert len(all_sections) > 0
    assert active_intent == "summarise"
    assert "summarise_guidelines" in include_keys


def test_unknown_intent_falls_back_to_default():
    _, _, active_intent, _ = resolve_context(
        domain="banking",
        intent="nonexistent_intent_xyz",
    )
    assert active_intent == "default"


def test_unknown_domain_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        resolve_context(domain="nonexistent_domain_xyz", intent="summarise")


def test_source_files_are_populated():
    _, source_files, _, _ = resolve_context(
        domain="ecommerce",
        intent="support",
    )
    assert len(source_files) > 0
    assert all(isinstance(f, str) for f in source_files)
