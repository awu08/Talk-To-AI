# PyInstaller recipe for Talk-To-AI.app
#
# Don't run this directly; use ./build_app.sh, which also makes the icon,
# signs the app and packs it into a .dmg.

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))  # noqa: F821 (SPECPATH is set by PyInstaller)
sys.path.insert(0, ROOT)
from app import __version__  # noqa: E402

APP_NAME = "Talk-To-AI"
BUNDLE_ID = "com.awu08.talktoai"
ICON = os.path.join(ROOT, "build", "Talk-To-AI.icns")

datas, binaries, hiddenimports = [], [], []

# Whisper: faster-whisper's voice-detection model + CTranslate2's native libraries
for package in ("faster_whisper", "ctranslate2"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

# Google speech (backup engine): needs its bundled `flac` encoder on macOS
datas += collect_data_files("speech_recognition", includes=["flac-mac", "version.txt"])
hiddenimports += collect_submodules("speech_recognition")

# Libraries that pick their platform backend at runtime
hiddenimports += [
    "pynput.keyboard._darwin",
    "pynput.mouse._darwin",
    "pyttsx3.drivers",
    "pyttsx3.drivers.nsss",
    "pyttsx3.drivers.dummy",
]
# Gemini (google-genai) is imported lazily, so list it explicitly
hiddenimports += collect_submodules("google.genai")

a = Analysis(  # noqa: F821
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "torch",
              "pandas", "scipy", "bs4", "lxml", "google.generativeai"],
    noarchive=False,
)

# Drop large data files the app never reads:
#  - Google API discovery documents (~100 MB; only used for APIs we don't call)
#  - Offline Sphinx speech data and non-Mac flac encoders from speech_recognition
UNUSED_DATA = ("googleapiclient/discovery_cache/documents", "pocketsphinx-data",
               "flac-linux", "flac-win32")
def _used(entry):
    return not any(part in entry[0].replace(os.sep, "/") for part in UNUSED_DATA)


a.datas = [entry for entry in a.datas if _used(entry)]
a.binaries = [entry for entry in a.binaries if _used(entry)]  # flac encoders count as binaries

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    console=False,          # a GUI app, no Terminal window
    argv_emulation=False,
    target_arch=None,       # build for the Mac you're on (Apple Silicon or Intel)
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

app = BUNDLE(  # noqa: F821
    coll,
    name=f"{APP_NAME}.app",
    icon=ICON if os.path.exists(ICON) else None,
    bundle_identifier=BUNDLE_ID,
    version=__version__,
    info_plist={
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": __version__,
        "CFBundleVersion": __version__,
        "LSUIElement": True,  # menu bar app: no Dock icon
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription":
            "Talk-To-AI listens to your question while you hold the shortcut, "
            "and sends it to the AI you chose.",
        "NSHumanReadableCopyright": "© 2026 Allen Wu. MIT License.",
    },
)
