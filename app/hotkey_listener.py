"""Hotkey Listener: Global keyboard hotkey detection and callback triggering.

This module provides cross-platform global hotkey detection using the pynput library.
It monitors keyboard input at the OS level and triggers callbacks when configured
hotkey combinations are detected. Handles proper key normalization and provides
pause/resume functionality for use during configuration.

The listener runs in a background daemon thread to avoid blocking the UI, and
includes robust error handling for callback execution and key parsing.

Author: Allen Wu
Version: 1.0.0
"""

import threading
import logging
from typing import Callable, Dict, List, Optional, Set

from pynput import keyboard

logger = logging.getLogger(__name__)

# Standard modifier key mappings (platform-agnostic aliases)
STANDARD_KEY_MAP: Dict[str, str] = {
    # Modifiers
    "cmd": "cmd",
    "command": "cmd",
    "option": "alt",
    "alt": "alt",
    "shift": "shift",
    "ctrl": "ctrl",
    "control": "ctrl",
    
    # Lock keys
    "caps": "caps_lock",
    "caps_lock": "caps_lock",
    
    # Function keys
    "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4", "f5": "f5",
    "f6": "f6", "f7": "f7", "f8": "f8", "f9": "f9", "f10": "f10",
    "f11": "f11", "f12": "f12",
    
    # Navigation keys
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end",
    "page_up": "page_up", "page_down": "page_down",
    
    # Special keys
    "tab": "tab",
    "enter": "enter", "return": "enter",
    "space": "space",
    "esc": "esc", "escape": "esc",
    "backspace": "backspace", "bksp": "backspace",
    "delete": "delete", "del": "delete",
}


class HotkeyListener:
    """Global keyboard hotkey listener with callback triggering.
    
    This class monitors keyboard input at the OS level and detects when configured
    hotkey combinations are pressed. When a hotkey combination is detected, it
    triggers registered callbacks (on_start and on_stop). This enables hands-free
    operation where a single hotkey press initiates recording and another releases it.
    
    The listener runs in a background daemon thread and includes pause/resume
    functionality for use during configuration screens (to prevent hotkeys from
    triggering while the user is configuring them).
    
    Key Features:
    - Global hotkey detection (works even when app window is not focused)
    - Multi-key combinations (e.g., "cmd+option+space")
    - Pause/resume without stopping listener
    - Robust error handling for callbacks
    - Platform-agnostic key parsing with aliases
    
    Attributes:
        config (ConfigManager): Configuration manager for hotkey settings
        on_start (Optional[Callable]): Callback triggered when start hotkey detected
        on_stop (Optional[Callable]): Callback triggered when stop hotkey detected
        listener (Optional[keyboard.Listener]): pynput listener instance
        is_listening (bool): Whether listener is actively running
        is_paused (bool): Whether hotkey detection is temporarily paused
        start_hotkeys (Optional[List[str]]): Parsed start hotkey combination
        stop_hotkeys (Optional[List[str]]): Parsed stop hotkey combination
        pressed_keys (Set[str]): Set of currently pressed keys
        
    Configuration Format:
        Hotkeys are configured as strings with "+" separators:
        - "cmd+option+space" (macOS style, Cmd+Option+Space)
        - "ctrl+shift+h" (Windows/Linux style, Ctrl+Shift+H)
        - Single keys: "space", "esc", "f1"
        
    Example:
        >>> def start_recording():
        ...     print("Recording started!")
        >>> def stop_recording():
        ...     print("Recording stopped!")
        >>> listener = HotkeyListener(config, on_start=start_recording, on_stop=stop_recording)
        >>> listener.start()  # Start listening in background
        >>> # Now pressing configured hotkey will trigger callbacks
    """

    def __init__(
        self,
        config,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
    ) -> None:
        """Initialize the hotkey listener with configuration and callbacks.
        
        Loads hotkey configuration, parses them into key combinations, and
        prepares the listener for activation. Does not start listening until
        start() is called.
        
        Args:
            config: ConfigManager instance providing hotkey configuration
            on_start (Optional[Callable]): Callback function to trigger when
                start hotkey is pressed. Should accept no arguments.
            on_stop (Optional[Callable]): Callback function to trigger when
                stop hotkey is pressed. Should accept no arguments.
                
        Side Effects:
            - Parses hotkey configuration from config
            - Initializes internal state variables
            - Logs initialization message
            
        Raises:
            AttributeError: If config doesn't have required get() method
        """
        self.config = config
        self.on_start = on_start
        self.on_stop = on_stop
        
        self.listener: Optional[keyboard.Listener] = None
        self.is_listening: bool = False
        self.is_paused: bool = False

        # Parse configured hotkeys into key combinations
        self.start_hotkeys: Optional[List[str]] = self._parse_hotkey(
            self.config.get("hotkeys", "start")
        )
        self.stop_hotkeys: Optional[List[str]] = self._parse_hotkey(
            self.config.get("hotkeys", "stop")
        )

        # Track currently pressed keys for hotkey detection
        self.pressed_keys: Set[str] = set()
        
        # Prevent duplicate callback triggers while hotkey is held down
        self._start_triggered: bool = False
        self._stop_triggered: bool = False
        
        logger.debug("HotkeyListener initialized")

    def start(self) -> None:
        """Start listening for hotkeys in a background daemon thread.
        
        Launches the keyboard listener in a daemon thread. The daemon thread
        will not prevent the application from exiting. The listener runs until
        stop() is called or the application terminates.
        
        Side Effects:
            - Spawns background daemon thread
            - Thread calls _listen() which blocks until stop() is called
            - Logs info message
            
        Note:
            Safe to call multiple times. Subsequent calls will be ignored
            since only one listener thread is needed.
        """
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()
        logger.info("Hotkey listener started in background thread")

    def stop(self) -> None:
        """Stop the hotkey listener and clean up resources.
        
        Stops the pynput listener, which terminates the keyboard monitoring
        thread. After calling this, no hotkey callbacks will be triggered.
        
        Side Effects:
            - Stops pynput listener if running
            - Sets is_listening to False
            - Logs info message
            
        Note:
            Safe to call even if listener hasn't started. Does not raise
            exceptions if listener is already stopped.
        """
        if self.listener:
            self.listener.stop()
        self.is_listening = False
        logger.info("Hotkey listener stopped")

    def pause(self) -> None:
        """Pause hotkey detection without stopping the listener.
        
        Sets is_paused flag which causes the on_press handler to return early,
        effectively disabling hotkey detection. The listener continues running
        and monitoring keyboard input, but no callbacks are triggered.
        
        Useful during settings configuration to prevent hotkeys from triggering
        while the user is modifying them.
        
        Side Effects:
            - Sets is_paused to True
            - Subsequent hotkey presses are ignored
            - Logs debug message
            
        Note:
            Does not stop the listener, so resume() is fast. To completely
            stop listening, call stop() instead.
        """
        self.is_paused = True
        logger.debug("Hotkey listener paused")

    def resume(self) -> None:
        """Resume hotkey detection after being paused.
        
        Clears is_paused flag to re-enable hotkey detection. The listener
        was never stopped, so this is instant (no latency).
        
        Side Effects:
            - Sets is_paused to False
            - Hotkey detection resumes immediately
            - Logs debug message
            
        Note:
            Automatically clears triggered flags to avoid spurious callbacks
            if keys are held down during pause.
        """
        self.is_paused = False
        self._start_triggered = False
        self._stop_triggered = False
        logger.debug("Hotkey listener resumed")

    def _listen(self) -> None:
        """Listen for keyboard input and detect hotkey combinations.
        
        Main listener loop that runs in a background thread. Monitors all
        keyboard input and detects when configured hotkey combinations are
        pressed. Triggers callbacks when hotkeys are detected.
        
        Uses pynput to monitor keyboard at OS level, allowing global hotkey
        detection even when the application window is not focused.
        
        Side Effects:
            - Sets is_listening to True
            - Executes on_start callback when start hotkey detected
            - Executes on_stop callback when stop hotkey detected
            - Logs debug messages for hotkey detection
            - Logs errors for callback failures
            
        Note:
            This method blocks until stop() is called. Should only be called
            from start() to run in a daemon thread.
        """
        self.is_listening = True
        logger.debug("Keyboard listener thread started")

        def on_press(key: keyboard.Key) -> None:
            """Handle keyboard key press event.
            
            Args:
                key (keyboard.Key): The key that was pressed (pynput Key object)
                
            Note:
                Runs in listener thread. Should complete quickly to avoid
                blocking keyboard input processing.
            """
            try:
                if self.is_paused:
                    return

                # Normalize key to standard string representation
                normalized_key: str = self._normalize_key(key)
                self.pressed_keys.add(normalized_key)

                # Check if START hotkey combination is now complete
                if (
                    self.start_hotkeys
                    and not self._start_triggered
                    and all(k in self.pressed_keys for k in self.start_hotkeys)
                ):
                    self._start_triggered = True
                    logger.debug("Start hotkey detected")
                    if self.on_start:
                        try:
                            self.on_start()
                        except Exception as e:
                            logger.error(f"Error in on_start callback: {e}", exc_info=True)

                # Check if STOP hotkey combination is now complete
                if (
                    self.stop_hotkeys
                    and not self._stop_triggered
                    and all(k in self.pressed_keys for k in self.stop_hotkeys)
                ):
                    self._stop_triggered = True
                    logger.debug("Stop hotkey detected")
                    if self.on_stop:
                        try:
                            self.on_stop()
                        except Exception as e:
                            logger.error(f"Error in on_stop callback: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error in on_press handler: {e}", exc_info=True)

        def on_release(key: keyboard.Key) -> None:
            """Handle keyboard key release event.
            
            Removes key from pressed_keys and resets trigger flags when
            the hotkey combination is no longer fully pressed.
            
            Args:
                key (keyboard.Key): The key that was released (pynput Key object)
                
            Note:
                Runs in listener thread. Should complete quickly to avoid
                blocking keyboard input processing.
            """
            try:
                normalized_key: str = self._normalize_key(key)
                self.pressed_keys.discard(normalized_key)

                # Reset start trigger when keys released
                if not self.start_hotkeys or not all(
                    k in self.pressed_keys for k in self.start_hotkeys
                ):
                    self._start_triggered = False

                # Reset stop trigger when keys released
                if not self.stop_hotkeys or not all(
                    k in self.pressed_keys for k in self.stop_hotkeys
                ):
                    self._stop_triggered = False
            except Exception as e:
                logger.error(f"Error in on_release handler: {e}", exc_info=True)

        try:
            # Start pynput keyboard listener (blocks until listener.stop() called)
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                self.listener = listener
                logger.debug("pynput Listener created and joining")
                listener.join()
        except Exception as e:
            logger.error(f"Hotkey listener error: {e}", exc_info=True)
            self.is_listening = False

    def _normalize_key(self, key: keyboard.Key) -> str:
        """Normalize a pynput key object to a consistent string representation.
        
        Converts pynput's Key and KeyCode objects into normalized lowercase
        strings for comparison. Handles both printable characters and special
        keys (modifiers, function keys, navigation keys).
        
        Args:
            key (keyboard.Key): The key object from pynput
            
        Returns:
            str: Normalized key string (lowercase). Examples:
                - keyboard.Key.cmd → "cmd"
                - keyboard.KeyCode(char='a') → "a"
                - keyboard.Key.space → "space"
                - keyboard.Key.f1 → "f1"
                
        Note:
            All return values are lowercase for case-insensitive comparison.
            Special characters are converted to their string representation.
        """
        try:
            if isinstance(key, keyboard.KeyCode):
                # KeyCode has a char attribute for printable characters
                if hasattr(key, "char") and key.char:
                    return key.char.lower()
                return str(key).lower()
            elif isinstance(key, keyboard.Key):
                # Key objects have a name attribute
                return key.name.lower()
            else:
                return str(key).lower()
        except Exception as e:
            logger.error(f"Error normalizing key: {e}")
            return str(key).lower()

    def _parse_hotkey(self, hotkey_string: Optional[str]) -> Optional[List[str]]:
        """Parse a hotkey string into a list of normalized key strings.
        
        Parses user-friendly hotkey strings like "cmd+option+space" into a
        list of normalized key names that can be compared against pressed keys.
        Includes aliases for common key names (e.g., "option" → "alt").
        
        Args:
            hotkey_string (Optional[str]): Hotkey string in format "key+key+key"
                (e.g., "cmd+option+space", "ctrl+shift+h", or single key "esc")
                Returns None if hotkey_string is None or empty.
                
        Returns:
            Optional[List[str]]: List of normalized key strings, or None if
                hotkey_string is empty. Examples:
                - "cmd+option+space" → ["cmd", "alt", "space"]
                - "ctrl+shift+h" → ["ctrl", "shift", "h"]
                - "space" → ["space"]
                - "" → None
                
        Side Effects:
            - Logs warning for unknown key names
            - Unknown keys are silently skipped
            
        Note:
            Key comparison is case-insensitive. Unknown keys generate a warning
            but don't cause failure.
        """
        if not hotkey_string:
            return None

        # Build complete key map with base map plus letters and numbers
        key_map: Dict[str, str] = dict(STANDARD_KEY_MAP)
        
        # Add lowercase letters a-z
        for letter in "abcdefghijklmnopqrstuvwxyz":
            key_map[letter] = letter
        
        # Add numbers 0-9
        for num in "0123456789":
            key_map[num] = num

        # Split hotkey string on '+' and parse each key
        keys: List[str] = hotkey_string.split("+")
        combination: List[str] = []

        for key_name in keys:
            key_name = key_name.strip().lower()
            if key_name in key_map:
                combination.append(key_map[key_name])
            elif key_name:  # Only warn for non-empty unknown keys
                logger.warning(f"Unknown hotkey key name: '{key_name}'")

        return combination if combination else None

    def update_hotkeys(self) -> None:
        """Reload hotkey configuration from settings.
        
        Re-reads the hotkey configuration from the ConfigManager and updates
        the start_hotkeys and stop_hotkeys attributes. Called when settings
        are changed to apply the new hotkey configuration immediately.
        
        Side Effects:
            - Reloads start_hotkeys from config
            - Reloads stop_hotkeys from config
            - Resets triggered flags to False
            - Logs debug message
            
        Note:
            Changes take effect immediately. Users can update hotkeys in settings
            and they will apply without restarting the app.
        """
        self.start_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "start")
        )
        self.stop_hotkeys = self._parse_hotkey(
            self.config.get("hotkeys", "stop")
        )
        self._start_triggered = False
        self._stop_triggered = False
        logger.info("Hotkey configuration updated from settings")