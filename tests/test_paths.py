"""Tests for paths: bundled files are found from source and from a packaged build."""
import sys

import paths


def test_source_layout_finds_the_bundled_files():
    """Running from source, resources are in the project folder."""
    assert paths.resource("config.yaml").is_file()
    assert paths.resource("data", "care_lines.json").is_file()
    assert paths.resource("assets", "flame", "baked_flame.npz").is_file()


def test_packaged_build_uses_the_pyinstaller_folder(monkeypatch, tmp_path):
    """Frozen (PyInstaller): resources come from ``sys._MEIPASS``."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert paths.is_frozen()
    assert paths.resource("data", "x.json") == tmp_path / "data" / "x.json"
