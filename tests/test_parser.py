# tests/test_parser.py

import pytest

from src.utils.parser import parse_markdown_sections


def test_single_section():
    raw = "## Hello World\nSome content here."
    result = parse_markdown_sections(raw)
    assert result == {"hello_world": "Some content here."}


def test_multiple_sections():
    raw = "## First Section\nContent A.\n## Second Section\nContent B."
    result = parse_markdown_sections(raw)
    assert "first_section" in result
    assert "second_section" in result
    assert result["first_section"] == "Content A."
    assert result["second_section"] == "Content B."


def test_empty_sections_are_skipped():
    raw = "## Empty Section\n   \n## Real Section\nContent."
    result = parse_markdown_sections(raw)
    assert "empty_section" not in result
    assert "real_section" in result


def test_key_normalisation():
    raw = "## Tone And Style\nBe friendly."
    result = parse_markdown_sections(raw)
    assert "tone_and_style" in result


def test_empty_input():
    result = parse_markdown_sections("")
    assert result == {}
