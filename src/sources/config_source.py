# src/sources/config_source.py
# Responsible for reading YAML configuration files.
# Currently used to load the intent map.

from pathlib import Path
from typing import Any, Dict, Union

import yaml


def load_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Reads and parses a YAML file.

    Args:
        file_path: Path to the .yaml file.

    Returns:
        Parsed content as a Python dict.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not valid YAML.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")

    if data is None:
        return {}

    return data
