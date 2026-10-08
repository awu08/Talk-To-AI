#!/bin/bash
# Build Talk-To-AI.app and a .dmg installer.
#
# Usage (from the project folder, on a Mac):
#     bash build_app.sh
#   (or, if your shell says "command not found: bash":  /bin/bash build_app.sh)
#
# Result:
#     dist/Talk-To-AI.app           the app (drag it into Applications)
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
DMG="dist/Talk-To-AI-$VERSION.dmg"
STAGING="build/dmg"
rm -rf "$STAGING" "$DMG"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"
hdiutil create -quiet -volname "Talk-To-AI" -srcfolder "$STAGING" -ov -format UDZO "$DMG"

echo
echo "Done!"
echo "  App:       $APP"
echo "  Installer: $DMG"
echo
echo "Try it now with:  open \"$APP\""
