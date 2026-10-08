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


# --------------------------------------------------- hotkey permissions
#
# Global hotkeys on macOS need two permissions:
#   - Accessibility       (Privacy & Security → Accessibility)
#   - Input Monitoring    (Privacy & Security → Input Monitoring)
# Both are checked here, and macOS is asked to add the app to each list so
# the user only has to turn the switches on.

_AX_PATH = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
_IOKIT_PATH = "/System/Library/Frameworks/IOKit.framework/IOKit"
_CF_PATH = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
_IOHID_LISTEN_EVENT = 1          # kIOHIDRequestTypeListenEvent
_IOHID_ACCESS_GRANTED = 0        # kIOHIDAccessTypeGranted

PANES = {
    "Accessibility": "Privacy_Accessibility",
    "Input Monitoring": "Privacy_ListenEvent",
}


def has_accessibility_permission() -> Optional[bool]:
    """Whether macOS lets this process control/observe input (Accessibility).

    Returns None when it can't be checked (not macOS, or the check failed).
    """
    if not IS_MAC:
        return None
    try:
        services = ctypes.cdll.LoadLibrary(_AX_PATH)
        services.AXIsProcessTrusted.restype = ctypes.c_bool
        return bool(services.AXIsProcessTrusted())
    except Exception as e:
        logger.debug(f"Couldn't check Accessibility permission: {e}")
        return None


def has_input_monitoring_permission() -> Optional[bool]:
    """Whether macOS lets this process read keystrokes from other apps (Input Monitoring).

    Returns None when it can't be checked (not macOS, or macOS older than 10.15).
    """
    if not IS_MAC:
        return None
    try:
        iokit = ctypes.cdll.LoadLibrary(_IOKIT_PATH)
        iokit.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        iokit.IOHIDCheckAccess.restype = ctypes.c_uint32
        return iokit.IOHIDCheckAccess(_IOHID_LISTEN_EVENT) == _IOHID_ACCESS_GRANTED
    except Exception as e:
        logger.debug(f"Couldn't check Input Monitoring permission: {e}")
        return None


def request_accessibility() -> None:
    """Ask macOS to add this app to the Accessibility list (shows its own prompt once)."""
    if not IS_MAC:
        return
    try:
        cf = ctypes.cdll.LoadLibrary(_CF_PATH)
        services = ctypes.cdll.LoadLibrary(_AX_PATH)
        cf.CFDictionaryCreate.restype = ctypes.c_void_p
        cf.CFDictionaryCreate.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
                                          ctypes.POINTER(ctypes.c_void_p), ctypes.c_long,
                                          ctypes.c_void_p, ctypes.c_void_p]
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        services.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        services.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool

        prompt_key = ctypes.c_void_p.in_dll(services, "kAXTrustedCheckOptionPrompt")
        true_value = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
        keys = (ctypes.c_void_p * 1)(prompt_key.value)
        values = (ctypes.c_void_p * 1)(true_value.value)
        key_callbacks = ctypes.addressof(ctypes.c_char.in_dll(cf, "kCFTypeDictionaryKeyCallBacks"))
        value_callbacks = ctypes.addressof(
            ctypes.c_char.in_dll(cf, "kCFTypeDictionaryValueCallBacks"))
        options = cf.CFDictionaryCreate(None, keys, values, 1, key_callbacks, value_callbacks)
        try:
            services.AXIsProcessTrustedWithOptions(options)
        finally:
            cf.CFRelease(options)
    except Exception as e:
        logger.debug(f"Couldn't request Accessibility permission: {e}")


def request_input_monitoring() -> None:
    """Ask macOS to add this app to the Input Monitoring list (shows its own prompt once)."""
    if not IS_MAC:
        return
    try:
        iokit = ctypes.cdll.LoadLibrary(_IOKIT_PATH)
        iokit.IOHIDRequestAccess.argtypes = [ctypes.c_uint32]
        iokit.IOHIDRequestAccess.restype = ctypes.c_bool
        iokit.IOHIDRequestAccess(_IOHID_LISTEN_EVENT)
    except Exception as e:
        logger.debug(f"Couldn't request Input Monitoring permission: {e}")


def missing_hotkey_permissions() -> list:
    """Names of the hotkey permissions that are definitely not granted."""
    missing = []
    if has_accessibility_permission() is False:
        missing.append("Accessibility")
    if has_input_monitoring_permission() is False:
        missing.append("Input Monitoring")
    return missing


def open_privacy_settings(pane: str = "Privacy_Accessibility") -> None:
    """Open System Settings at a Privacy & Security pane (e.g. Privacy_Microphone)."""
    if IS_MAC:
        subprocess.Popen(["/usr/bin/open",
                          f"x-apple.systempreferences:com.apple.preference.security?{pane}"])


def hotkey_permission_message(missing: list) -> str:
    """Tell the user exactly which switches to turn on."""
    who = permission_target()
    if len(missing) == 2:
        where = "**Accessibility** and **Input Monitoring**"
        steps = (f"turn on **{who}** in both. I've opened Accessibility for you; after that, "
                 f"go back to Privacy & Security and open Input Monitoring.")
    else:
        where = f"**{missing[0]}**"
        steps = f"turn on **{who}** there. I've opened that page for you."
    return (f"**Hotkeys need permission.** In System Settings → Privacy & Security → "
            f"{where}: {steps}\n\nThen quit and reopen {APP_NAME}.")


def accessibility_message() -> str:
    """Kept for compatibility: the message when only Accessibility is missing."""
    return hotkey_permission_message(["Accessibility"])


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
