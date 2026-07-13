from pathlib import Path

import pytest

from sx.config import Part0Config, load_part0


def test_load_part0_returns_mapping_wrapper() -> None:
    config = load_part0()
    assert isinstance(config, Part0Config)
    assert isinstance(config.values, dict)


def test_part0_contains_w001_required_fields() -> None:
    config = load_part0().values
    assert config["inference_mode"] == "api"
    assert config["api"]["model"] == "deepseek-v4-pro"
    assert "max_cost_per_batch_usd" in config["api"]
    assert "max_cost_per_unit_warn_usd" in config["api"]
    assert config["ingest"]["source_origin"]["allowed"] == ["self", "third_party"]
    assert config["ingest"]["skip"]


def test_load_part0_rejects_non_mapping(tmp_path: Path) -> None:
    config_path = tmp_path / "part0.yaml"
    config_path.write_text("- not-a-mapping\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_part0(config_path)

