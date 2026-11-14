"""Tests for version: git-describe output becomes the app's version string."""
import pytest

import version


@pytest.mark.parametrize(
    ("described", "expected"),
    [
        ("v0.1.0", "0.1.0"),
        ("v0.1.0-rc.1", "0.1.0-rc.1"),
        ("v0.1.0-3-gabc1234", "0.1.1.dev3+gabc1234"),
        ("v1.4.9-12-g0f1e2d3", "1.4.10.dev12+g0f1e2d3"),
        ("v0.1.0-rc.1-3-gabc1234", "0.1.0-rc.1.dev3+gabc1234"),
        ("v0.1.0\n", "0.1.0"),
    ],
)
def test_from_describe(described, expected):
    """Tagged commits give the plain version; later commits give a dev version."""
    assert version.from_describe(described) == expected


@pytest.mark.parametrize("junk", ["", "abc1234", "release-1", "v1.2"])
def test_from_describe_rejects_non_version_tags(junk):
    """Anything that is not ``vX.Y.Z...`` is not a version."""
    assert version.from_describe(junk) is None


def test_display_name(monkeypatch):
    """The Settings footer / tray tooltip text."""
    monkeypatch.setattr(version, "get_version", lambda: "0.1.0")
    assert version.display_name() == "Lavenzure v0.1.0"
    monkeypatch.setattr(version, "get_version", lambda: "dev")
    assert version.display_name() == "Lavenzure (dev)"


def test_get_version_without_anything_is_dev(monkeypatch):
    """No build file and no git tags -> ``dev``."""
    version.get_version.cache_clear()
    monkeypatch.setattr(version, "git_version", lambda: None)
    monkeypatch.setitem(__import__("sys").modules, "_version", None)  # import _version fails
    assert version.get_version() == "dev"
    version.get_version.cache_clear()
