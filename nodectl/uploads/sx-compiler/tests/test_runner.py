import pytest

from fixtures.runner import main


def test_harness_only_succeeds() -> None:
    assert main(["--harness-only"]) == 0


def test_non_harness_mode_exits() -> None:
    with pytest.raises(SystemExit):
        main([])
