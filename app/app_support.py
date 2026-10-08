"""App Support: Things a packaged Mac app needs that a script run from Terminal doesn't.

    - Logging to a file (an app has no Terminal window to print to)
    - Making sure only one copy runs at a time
    - Checking the Accessibility permission global hotkeys need
    - "Open at login" via a per-user LaunchAgent

Everything here also works when running `python3 main.py`; the wording of
permission messages just changes from "Talk-To-AI" to "your terminal app".

Author: Allen Wu
Version: 1.1.0
"""

import ctypes
import logging
import logging.handlers
import os
import plistlib
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)

APP_NAME: str = "Talk-To-AI"
BUNDLE_ID: str = "com.awu08.talktoai"
IS_MAC: bool = sys.platform == "darwin"
IS_FROZEN: bool = bool(getattr(sys, "frozen", False))  # True inside the packaged .app

CONFIG_DIR: str = os.path.expanduser("~/.talktoai")
LAUNCH_AGENT_PATH: str = os.path.expanduser(f"~/Library/LaunchAgents/{BUNDLE_ID}.plist")


def permission_target() -> str:
    """Name of the thing macOS asks permission for: the app itself, or the terminal."""
    return APP_NAME if IS_FROZEN else "your terminal app"


# ---------------------------------------------------------------- logging

def log_file_path() -> str:
    if IS_MAC:
        folder = os.path.expanduser(f"~/Library/Logs/{APP_NAME}")
    else:
        folder = os.path.join(CONFIG_DIR, "logs")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "talk-to-ai.log")


def setup_logging() -> None:
    """Log INFO and above to the console and to a small rotating log file.

    On macOS the file is in ~/Library/Logs/Talk-To-AI/, which also shows up
    in the Console app.
    """
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                                  datefmt="%Y-%m-%d %H:%M:%S")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path(), maxBytes=1_000_000, backupCount=2, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as e:
        logger.warning(f"Couldn't open log file: {e}")


# --------------------------------------------------------- single instance

_lock = None  # kept alive for the life of the process


def acquire_single_instance_lock() -> bool:
    """Return False if another copy of the app is already running."""
    global _lock
    from PyQt6.QtCore import QLockFile
    os.makedirs(CONFIG_DIR, exist_ok=True)
    _lock = QLockFile(os.path.join(CONFIG_DIR, "app.lock"))
    _lock.setStaleLockTime(0)  # a lock left by a crashed copy is detected by its PID
    return _lock.tryLock(200)


# ---------------------------------------------------- accessibility check

def has_accessibility_permission() -> Optional[bool]:
    """Whether macOS lets this process watch the keyboard (needed for hotkeys).

    Returns None when it can't be checked (not macOS, or the check failed).
    """
    if not IS_MAC:
        return None
    try:
        services = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        services.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(services.AXIsProcessTrusted())
    except Exception as e:
        logger.debug(f"Couldn't check Accessibility permission: {e}")
        return None


def open_privacy_settings(pane: str = "Privacy_Accessibility") -> None:
    """Open System Settings at a Privacy & Security pane (e.g. Privacy_Microphone)."""
    if IS_MAC:
        subprocess.Popen(["/usr/bin/open",
                          f"x-apple.systempreferences:com.apple.preference.security?{pane}"])


def accessibility_message() -> str:
    who = permission_target()
    return (f"**Hotkeys need permission.** In System Settings → Privacy & Security → "
            f"**Accessibility**, turn on **{who}**, then quit and reopen {APP_NAME}.\n\n"
            f"I've opened that page for you.")


# ---------------------------------------------------------- open at login

def bundle_path() -> Optional[str]:
    """Path to Talk-To-AI.app when running as the packaged app, else None."""
    if not (IS_MAC and IS_FROZEN):
        return None
    # sys.executable = …/Talk-To-AI.app/Contents/MacOS/Talk-To-AI
    path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
    return path if path.endswith(".app") else None


def login_item_supported() -> bool:
    return bundle_path() is not None


def is_login_item_enabled() -> bool:
    return os.path.exists(LAUNCH_AGENT_PATH)


def set_login_item(enabled: bool) -> bool:
    """Turn "Open at login" on or off. Returns True on success."""
    try:
        if not enabled:
            if os.path.exists(LAUNCH_AGENT_PATH):
                os.remove(LAUNCH_AGENT_PATH)
            logger.info("Open at login turned off")
            return True
        app = bundle_path()
        if app is None:
            return False
        os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
        with open(LAUNCH_AGENT_PATH, "wb") as f:
            plistlib.dump({
                "Label": BUNDLE_ID,
                "ProgramArguments": ["/usr/bin/open", "-a", app],
                "RunAtLoad": True,
                "ProcessType": "Interactive",
            }, f)
        logger.info(f"Open at login turned on ({app})")
        return True
    except OSError as e:
        logger.error(f"Couldn't change Open at login: {e}")
        return False
