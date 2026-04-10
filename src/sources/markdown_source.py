# src/sources/markdown_source.py
# Responsible for reading .md files from a given directory path.
# Returns raw file contents. Does NOT parse — parsing happens in utils/parser.py.

import os
from pathlib import Path
from typing import Dict, List, Union


def load_markdown_files(directory_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Reads all .md files from the given directory (non-recursive).

    Args:
        directory_path: Absolute or relative path to a folder containing .md files.

    Returns:
        A list of dicts, each with:
        - "file": the filename (e.g. "tone.md")
        - "content": the full raw text of the file

    Raises:
        FileNotFoundError: If the directory does not exist.
    """
    path = Path(directory_path)

    if not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {path}")

    results = []

    for filename in sorted(os.listdir(path)):
        if not filename.endswith(".md"):
            continue

        file_path = path / filename

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

            if content:
                results.append({"file": filename, "content": content})

    return results
