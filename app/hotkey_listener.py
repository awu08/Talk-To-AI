"""Monitors keyboard input and triggers callbacks when configured hotkey combinations are pressed and released."""

import threading
import logging
from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Listens for global keyboard hotkeys and triggers callbacks."""

    def __init__(self, config, on_start=None, on_stop=None):
        """Initialize the hotkey listener."""
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        self.listener = None
        self.is_listening = False

        self.start_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "start")
        )
        self.stop_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "stop")
        )

        self.pressed_keys = set()

    def start(self):
        """Start listening for hotkeys in a background thread."""
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()

    def stop(self):
        """Stop the hotkey listener."""
        if self.listener:
            self.listener.stop()
        self.is_listening = False

    def pause(self):
        """Pause hotkey detection without stopping the listener."""
        self.is_listening = False

    def resume(self):
        """Resume hotkey detection."""
        self.is_listening = True

    def _listen(self):
        """Listen for keyboard input and detect hotkey combinations."""
        self.is_listening = True

        def on_press(key):
            # Normalize key representation
            if isinstance(key, keyboard.KeyCode):
                normalized_key = (
                    key.char if hasattr(key, "char") and key.char else str(key)
                )
            else:
                normalized_key = key

            self.pressed_keys.add(normalized_key)

            if not self.is_listening:
                return

            # Check START hotkey
            if self.start_hotkeys:
                if all(k in self.pressed_keys for k in self.start_hotkeys):
                    logger.debug("Start hotkey detected")
                    if self.on_start:
                        self.on_start()

            # Check STOP hotkey
            if self.stop_hotkeys:
                if all(k in self.pressed_keys for k in self.stop_hotkeys):
                    logger.debug("Stop hotkey detected")
                    if self.on_stop:
                        self.on_stop()

        def on_release(key):
            # Normalize key representation
            if isinstance(key, keyboard.KeyCode):
                normalized_key = (
                    key.char if hasattr(key, "char") and key.char else str(key)
                )
            else:
                normalized_key = key

            self.pressed_keys.discard(normalized_key)

        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            self.listener = listener
            listener.join()

    def _parse_hotkey(self, hotkey):
        """Parse a hotkey string into a list of pynput key objects."""
        if not hotkey:
            return None

        key_map = {
            "cmd": keyboard.Key.cmd,
            "option": keyboard.Key.alt,
            "shift": keyboard.Key.shift,
            "ctrl": keyboard.Key.ctrl,
            "caps": keyboard.Key.caps_lock,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "home": keyboard.Key.home,
            "end": keyboard.Key.end,
            "page_up": keyboard.Key.page_up,
            "page_down": keyboard.Key.page_down,
            "tab": keyboard.Key.tab,
            "enter": keyboard.Key.enter,
            "space": keyboard.Key.space,
            "esc": keyboard.Key.esc,
            "escape": keyboard.Key.esc,
            "backspace": keyboard.Key.backspace,
            "delete": keyboard.Key.delete,
            "0": "0",
            "1": "1",
            "2": "2",
            "3": "3",
            "4": "4",
            "5": "5",
            "6": "6",
            "7": "7",
            "8": "8",
            "9": "9",
            "a": "a",
            "b": "b",
            "c": "c",
            "d": "d",
            "e": "e",
            "f": "f",
            "g": "g",
            "h": "h",
            "i": "i",
            "j": "j",
            "k": "k",
            "l": "l",
            "m": "m",
            "n": "n",
            "o": "o",
            "p": "p",
            "q": "q",
            "r": "r",
            "s": "s",
            "t": "t",
            "u": "u",
            "v": "v",
            "w": "w",
            "x": "x",
            "y": "y",
            "z": "z",
            "backtick": "`",
            "minus": "-",
            "equal": "=",
            "bracket_left": "[",
            "bracket_right": "]",
            "backslash": "\\",
            "semicolon": ";",
            "quote": "'",
            "comma": ",",
            "period": ".",
            "slash": "/",
        }

        keys = hotkey.split("+")
        combination = []

        for key in keys:
            key = key.strip().lower()
            if key in key_map:
                combination.append(key_map[key])
            else:
                logger.warning(f"Unknown hotkey: {key}")

        return combination if combination else None

    def update_hotkeys(self):
        """Reload hotkey configuration from settings."""
        self.start_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "start")
        )
        self.stop_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "stop")
        )
        logger.debug("Hotkeys updated")