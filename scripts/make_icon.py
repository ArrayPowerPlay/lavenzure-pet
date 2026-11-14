"""Draw the app icon ``assets/icon/lavenzure.ico`` from the pet's own portrait (the tray icon).

Run it again only if the character's look changes; the result is committed. Usage (Windows venv):
``.venv-win/Scripts/python.exe scripts/make_icon.py``.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from ui.tray_icon import render_portrait  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(image) -> bytes:
    """The image encoded as PNG."""
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data)


def main() -> None:
    """Write the .ico (one PNG-encoded image per size; Windows Vista+ reads these)."""
    QGuiApplication([])
    portrait = render_portrait()
    images = [portrait.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation) for size in SIZES]
    blobs = [png_bytes(image) for image in images]
    header = bytearray(b"\x00\x00\x01\x00" + len(blobs).to_bytes(2, "little"))
    offset = 6 + 16 * len(blobs)
    body = bytearray()
    for size, blob in zip(SIZES, blobs, strict=True):
        entry = bytearray()
        entry += bytes([size % 256, size % 256, 0, 0])          # 256 is stored as 0
        entry += (1).to_bytes(2, "little") + (32).to_bytes(2, "little")
        entry += len(blob).to_bytes(4, "little") + (offset + len(body)).to_bytes(4, "little")
        header += entry
        body += blob
    target = ROOT / "assets" / "icon" / "lavenzure.ico"
    target.write_bytes(bytes(header) + bytes(body))
    print(f"wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
