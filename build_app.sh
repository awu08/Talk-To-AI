#!/bin/bash
# Build Talk-To-AI.app and a .dmg installer.
#
# Usage (from the project folder, on a Mac):
#     bash build_app.sh             build into dist/
#     bash build_app.sh --install   build, then put the app straight into /Applications
#   (if your shell says "command not found: bash", use /bin/bash instead)
#
# Result:
#     dist/Talk-To-AI.app           the app (or /Applications/Talk-To-AI.app with --install)
#     dist/Talk-To-AI-<version>.dmg the installer to share
#
# It builds for the kind of Mac you're on (Apple Silicon or Intel).

set -eo pipefail
cd "$(dirname "$0")"

# Make sure macOS's own tools are reachable even if ~/.zshrc broke PATH.
# Appended (not prepended) so your own Python still comes first.
export PATH="$PATH:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [[ "$(uname)" != "Darwin" ]]; then
    echo "This builds a Mac app, so it has to run on a Mac." >&2
    exit 1
fi

APP="dist/Talk-To-AI.app"
INSTALLED="/Applications/Talk-To-AI.app"

INSTALL=false
for arg in "$@"; do
    case "$arg" in
        --install) INSTALL=true ;;
        *) echo "Unknown option: $arg (did you mean --install?)" >&2; exit 1 ;;
    esac
done

# Find a Python 3.10+ (macOS's built-in /usr/bin/python3 is too old)
find_python() {
    for candidate in "${PYTHON:-}" \
        /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 \
        /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
        /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
        [[ -z "$candidate" ]] && continue
        if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# The build needs a few GB of free space (bundled libraries, then the .dmg)
FREE_GB=$(df -k . | awk 'NR==2 {print int($4 / 1048576)}')
if (( FREE_GB < 3 )); then
    echo "Only ${FREE_GB} GB free on this disk; the build needs about 3 GB." >&2
    echo "Free up some space (empty the Trash, delete old downloads) and try again." >&2
    exit 1
fi

echo "==> Setting up the build environment"
if [[ -x venv/bin/python ]] && ! venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    echo "    The existing venv uses an old Python; making a new one"
    rm -rf venv
fi
if [[ ! -x venv/bin/python ]]; then
    PYTHON="$(find_python)" || {
        echo "Couldn't find Python 3.10 or newer. Install it from https://www.python.org/downloads/" >&2
        exit 1
    }
    echo "    Using $PYTHON"
    "$PYTHON" -m venv venv
fi
VENV_PY="venv/bin/python"
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r requirements.txt pyinstaller

VERSION="$("$VENV_PY" -c 'import app; print(app.__version__)')"
echo "    Talk-To-AI $VERSION, $(uname -m)"

echo "==> Drawing the app icon"
rm -rf build/icon
"$VENV_PY" packaging/make_icon.py build/icon
iconutil -c icns build/icon/Talk-To-AI.iconset -o build/Talk-To-AI.icns

echo "==> Building the app (this takes a few minutes)"
rm -rf "$APP"
"$VENV_PY" -m PyInstaller --noconfirm --clean \
    --distpath dist --workpath build/pyinstaller \
    packaging/Talk-To-AI.spec

echo "==> Signing (ad-hoc, for running on your own Mac)"
codesign --force --deep --sign - "$APP"

echo "==> Making the .dmg"
rm -rf build/pyinstaller  # temporary build files; frees space for the .dmg
DMG="dist/Talk-To-AI-$VERSION.dmg"
STAGING="build/dmg"
rm -rf "$STAGING" "$DMG"
mkdir -p "$STAGING"
# Move the app in (instant, no second copy on disk) and always move it back
mv "$APP" "$STAGING/"
trap 'mv "$STAGING/Talk-To-AI.app" "$APP" 2>/dev/null || true' EXIT
ln -s /Applications "$STAGING/Applications"
hdiutil create -quiet -volname "Talk-To-AI" -srcfolder "$STAGING" -ov -format UDZO "$DMG"
mv "$STAGING/Talk-To-AI.app" "$APP"
trap - EXIT
rm -rf "$STAGING"

if $INSTALL; then
    echo "==> Installing to /Applications"
    if pgrep -x "Talk-To-AI" >/dev/null; then
        echo "    Quitting the running Talk-To-AI"
        pkill -x "Talk-To-AI" || true
        sleep 1
    fi
    rm -rf "$INSTALLED"
    mv "$APP" "$INSTALLED"  # a move, not a copy: no extra disk space needed
    echo
    echo "Done! Talk-To-AI is installed in Applications."
    echo "  Installer: $DMG"
    echo
    echo "Starting it now…"
    open "$INSTALLED"
else
    echo
    echo "Done!"
    echo "  App:       $APP"
    echo "  Installer: $DMG"
    echo
    echo "Try it now with:  open \"$APP\""
    echo "Or next time, build straight into Applications with:  bash build_app.sh --install"
fi
