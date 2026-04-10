# src/utils/parser.py
# Parses raw markdown text into a structured dict of sections.
# Only parses ## level headings. All other heading levels are ignored.

import re
from typing import Dict


def parse_markdown_sections(raw_content: str) -> Dict[str, str]:
    """
    Parses a markdown string into a dict keyed by ## section headings.

    Rules:
    - Only ## headings are treated as section keys.
    - Section key is the heading text, stripped and lowercased,
      with spaces replaced by underscores.
    - Section value is all text between this ## and the next ##,
      stripped of leading/trailing whitespace.
    - Sections with empty content after stripping are excluded.
    - The # title heading and any ### or deeper headings are ignored.

    Args:
        raw_content: Full text of a markdown file.

    Returns:
        Dict mapping section_key -> content string.

    Example:
        Input:
            # Product Info
            ## Tone
            Be confident and clear.
            ## Key Features
            - Cashback rewards
            - Zero annual fee

        Output:
            {
                "tone": "Be confident and clear.",
                "key_features": "- Cashback rewards\\n- Zero annual fee"
            }
    """
    sections: Dict[str, str] = {}

    # Split on ## headings only (not ### or deeper).
    # Pattern: line starting with exactly two hashes followed by a space.
    parts = re.split(r"(?m)^## (.+)$", raw_content)

    # parts[0] is everything before the first ## heading (usually the # title) — skip it.
    # After that, parts come in pairs: [heading_text, content_block, ...].
    i = 1
    while i < len(parts) - 1:

        heading = parts[i].strip()
        content = parts[i + 1].strip()

        if heading and content:
            # Normalise key: lowercase, spaces to underscores.
            key = heading.lower().replace(" ", "_")
            sections[key] = content

        i += 2

    return sections
