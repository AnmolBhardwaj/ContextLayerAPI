# src/core/builder.py
# Responsible for filtering resolved sections down to what the active intent requires.
# Accepts include_keys from the resolver — no YAML reload needed here.

from typing import Dict, List


def build_context(
    all_sections: Dict[str, str],
    include_keys: List[str],
) -> Dict[str, str]:
    """
    Filters the full section map to only the keys requested by the active intent.

    Args:
        all_sections:  Merged dict of {section_key: content} from resolver.
        include_keys:  List of section keys to include (from intent map).

    Returns:
        Dict containing only the sections matched by include_keys.
        If include_keys is empty, returns all sections unchanged.

    Notes:
        Keys present in include_keys but absent from all_sections are silently
        skipped (no KeyError). This handles intent maps that reference sections
        not present in every domain.
    """
    if not include_keys:
        return dict(all_sections)

    return {key: all_sections[key] for key in include_keys if key in all_sections}
