# PyInstaller recipe for the Windows build: a folder (onedir) with a windowed Lavenzure.exe.
# Run through scripts/build.py (it writes src/_version.py first and zips the result).
# Only what is listed here, plus the Python modules main.py imports, ends up in the package:
# docs/, README, CLAUDE.md, tests/, .claude/ and any .env are NOT included.
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT / "src")],
    datas=[
        (str(ROOT / "config.yaml"), "."),                       # default settings (read-only)
        (str(ROOT / "data"), "data"),                           # care lines, facts and jokes
        (str(ROOT / "assets" / "flame"), "assets/flame"),       # pre-baked flame clips
    ],
    hiddenimports=[
        # keyring finds its Windows backend through entry points, which PyInstaller cannot see
        "keyring.backends.Windows",
        "win32ctypes.core",
        "win32ctypes.pywin32",
        "win32ctypes.pywin32.pywintypes",
        "win32ctypes.pywin32.win32cred",
        "_version",   # written by scripts/write_version.py; the build fails loudly if it is missing
    ],
    excludes=["tkinter", "matplotlib", "pytest", "ruff", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lavenzure",
    console=False,                                              # no console window
    icon=str(ROOT / "assets" / "icon" / "lavenzure.ico"),
    upx=False,                                                  # UPX triggers antivirus warnings
)
coll = COLLECT(exe, a.binaries, a.datas, name="Lavenzure", upx=False)
