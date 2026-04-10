# src/core/resolver.py
# Responsible for resolving context sections for a given domain + intent request.
# Returns a 4-tuple: (all_sections, source_files, active_intent, include_keys)
# include_keys is passed to builder.py to avoid a redundant YAML reload.

from pathlib import Path
from typing import Dict, List, Tuple

from src.core.settings import (
    DEFAULT_INTENT,
    DOMAINS_PATH,
    GLOBAL_PATH,
    INTENT_MAP_PATH,
)
from src.sources.config_source import load_yaml_file
from src.sources.markdown_source import load_markdown_files
from src.utils.parser import parse_markdown_sections


def resolve_context(
    domain: str,
    intent: str,
) -> Tuple[Dict[str, str], List[str], str, List[str]]:
    """
    Loads and parses markdown context files for the requested domain,
    then resolves which sections to include based on the intent map.

    Args:
        domain:  Domain identifier (e.g. "banking"). Already validated upstream.
        intent:  Intent identifier (e.g. "summarise"). Already validated upstream.

    Returns:
        A 4-tuple:
        - all_sections  – merged dict of {section_key: content} from domain + global files
        - source_files  – list of filenames that were read
        - active_intent – resolved intent (falls back to DEFAULT_INTENT if unknown)
        - include_keys  – list of section keys the builder should keep

    Raises:
        FileNotFoundError: If the domain directory does not exist.
    """
    domain_dir: Path = DOMAINS_PATH / domain

    if not domain_dir.is_dir():
        raise FileNotFoundError(
            f"Domain '{domain}' not found. "
            f"Expected directory: {domain_dir}"
        )

    # --- Load intent map ---
    intent_map: Dict = load_yaml_file(INTENT_MAP_PATH)

    # --- Resolve active intent (fall back to default if unknown) ---
    if intent in intent_map:
        active_intent = intent
    else:
        active_intent = DEFAULT_INTENT

    # --- Determine which section keys to include ---
    include_keys: List[str] = intent_map.get(active_intent, {}).get("include", [])

    # --- Load domain-specific markdown files ---
    domain_files = load_markdown_files(domain_dir)

    # --- Load global markdown files (if the directory exists) ---
    global_files: List[Dict] = []
    if GLOBAL_PATH.is_dir():
        global_files = load_markdown_files(GLOBAL_PATH)

    all_raw_files = domain_files + global_files

    # --- Parse all markdown into sections ---
    all_sections: Dict[str, str] = {}
    source_files: List[str] = []

    for file_entry in all_raw_files:
        file_name: str = file_entry["file"]
        raw_content: str = file_entry["content"]

        sections = parse_markdown_sections(raw_content)
        all_sections.update(sections)
        source_files.append(file_name)

    return all_sections, source_files, active_intent, include_keys


def list_domain_sections(domain: str) -> List[str]:
    """
    Returns a sorted list of section keys available for a domain.
    Reads only the domain directory (not global files).

    Args:
        domain: Domain identifier. Already validated upstream.

    Raises:
        FileNotFoundError: If the domain directory does not exist.
    """
    domain_dir: Path = DOMAINS_PATH / domain

    if not domain_dir.is_dir():
        raise FileNotFoundError(f"Domain '{domain}' not found.")

    all_sections: Dict[str, str] = {}
    for file_entry in load_markdown_files(domain_dir):
        all_sections.update(parse_markdown_sections(file_entry["content"]))

    return sorted(all_sections.keys())


def list_available_domains() -> List[str]:
    """Returns a sorted list of domain names (excludes directories starting with '_')."""
    if not DOMAINS_PATH.is_dir():
        return []
    return sorted(
        entry.name
        for entry in DOMAINS_PATH.iterdir()
        if entry.is_dir() and not entry.name.startswith("_")
    )


def list_available_intents() -> List[str]:
    """Returns the list of intent keys defined in intent_map.yaml."""
    intent_map = load_yaml_file(INTENT_MAP_PATH)
    return sorted(intent_map.keys())


def get_domain_info(domain: str) -> dict:
    """
    Returns file count and section count for a domain.

    Raises:
        FileNotFoundError: If the domain directory does not exist.
    """
    domain_dir: Path = DOMAINS_PATH / domain

    if not domain_dir.is_dir():
        raise FileNotFoundError(f"Domain '{domain}' not found.")

    files = load_markdown_files(domain_dir)
    all_sections: Dict[str, str] = {}

    for file_entry in files:
        all_sections.update(parse_markdown_sections(file_entry["content"]))

    return {"name": domain, "files": len(files), "sections": len(all_sections)}
