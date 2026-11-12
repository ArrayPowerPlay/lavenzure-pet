"""Tests for config.get: dotted lookups into config.yaml with defaults."""
import config


def test_reads_nested_value():
    """A dotted path walks nested mappings."""
    assert config.get("system_status.cpu_threshold_percent") == 90


def test_missing_key_returns_default():
    """Unknown keys (at any depth) fall back to the default."""
    assert config.get("nope.nothing", 42) == 42
    assert config.get("llm.does_not_exist") is None


def test_path_through_non_mapping_returns_default():
    """Walking past a scalar value returns the default instead of raising."""
    assert config.get("llm.model.deeper", "d") == "d"
