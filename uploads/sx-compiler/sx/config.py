"""Part 0 configuration loader.

Implements D16's single-source-of-truth requirement by loading operating
constants from `part0.yaml` rather than duplicating values in code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Part0Config:
    """Loaded Part 0 configuration.

    Implements D16 and the Phase 0 rule that operating constants live only in
    `part0.yaml`.
    """

    values: dict[str, Any]


def load_part0(path: str | Path = "part0.yaml") -> Part0Config:
    """Load the repo's Part 0 configuration file."""

    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError("part0.yaml must contain a mapping at the top level")
    return Part0Config(values=loaded)
