"""Build the Windows release: ``dist/Lavenzure-<version>-win-x64.zip`` plus its ``.sha256`` file.

Usage (Windows, from the project folder)::

    uv run python scripts/build.py            # version from the latest git tag
    uv run python scripts/build.py 0.1.0      # explicit version (used by CI)

Steps: write ``src/_version.py`` -> PyInstaller (``lavenzure.spec``) -> zip the ``Lavenzure``
folder (with ``LICENSE`` when the repo has one) -> SHA-256 of the zip. Needs ``pyinstaller``
(the ``dev`` group of ``pyproject.toml``, installed by ``uv sync``). Build on Windows, not in WSL's Linux Python.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def run(*command: str) -> None:
    """Run a command in the project folder; stop the build if it fails."""
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def zip_folder(folder: Path, target: Path) -> None:
    """Zip ``folder`` so that extracting gives one ``Lavenzure`` folder."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, Path(folder.name) / path.relative_to(folder))


def sha256_of(path: Path) -> str:
    """Hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    """Run the whole build; returns the process exit code."""
    version_args = [argv[1]] if len(argv) > 1 else []
    result = subprocess.run([sys.executable, "scripts/write_version.py", *version_args],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    version = result.stdout.strip()
    print(f"Building Lavenzure {version}")

    for folder in (DIST, BUILD):
        shutil.rmtree(folder, ignore_errors=True)
    run(sys.executable, "scripts/run_pyinstaller.py", "--noconfirm", "--clean",
        "--distpath", str(DIST), "--workpath", str(BUILD), "lavenzure.spec")

    app_folder = DIST / "Lavenzure"
    license_file = ROOT / "LICENSE"
    if license_file.is_file():
        shutil.copy2(license_file, app_folder / "LICENSE")

    archive = DIST / f"Lavenzure-{version}-win-x64.zip"
    zip_folder(app_folder, archive)
    checksum = sha256_of(archive)
    (DIST / f"{archive.name}.sha256").write_text(f"{checksum} *{archive.name}\n", encoding="ascii")
    print(f"{archive}  ({archive.stat().st_size / 1e6:.0f} MB)\nSHA256 {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
