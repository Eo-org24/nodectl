from __future__ import annotations

from pathlib import Path


def _contains_control_chars(value: str) -> bool:
    return any(ord(char) < 32 for char in value)


def safe_join(root: Path, user_path: str) -> Path:
    if not user_path or "\x00" in user_path or _contains_control_chars(user_path):
        raise ValueError("Invalid path.")
    raw_parts = user_path.split("/")
    if any(part == "" for part in raw_parts):
        raise ValueError("Empty path components are not allowed.")
    supplied = Path(user_path)
    if supplied.is_absolute():
        raise ValueError("Absolute paths are not allowed.")
    parts = supplied.parts
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Path traversal is not allowed.")
    resolved_root = root.resolve()
    candidate = (resolved_root / supplied).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("Path escapes managed root.")
    return candidate
