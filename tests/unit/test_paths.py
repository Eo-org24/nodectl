from __future__ import annotations

from pathlib import Path

import pytest

from backend.paths import safe_join


@pytest.mark.parametrize(
    "user_path",
    [
        "/absolute",
        "../escape",
        "dir/../escape",
        "dir/\nname",
        "dir/\x00name",
        "dir//name",
    ],
)
def test_safe_join_rejects_invalid_paths(user_path: str):
    with pytest.raises(ValueError):
        safe_join(Path("/tmp/root"), user_path)


def test_safe_join_returns_resolved_path(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    assert safe_join(root, "nested/file.txt") == root / "nested/file.txt"
