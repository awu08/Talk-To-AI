"""Configuration Manager: Settings storage and retrieval.

This module provides centralized configuration management for the Talk-To-AI application.
Settings are persisted to JSON files in the user's home directory (~/.shortcutai/),
allowing settings to survive application restarts. 

The ConfigManager supports:
- Loading and saving settings to JSON files
- Type-safe access via dict-style API
- Default settings that can be reset to
- Graceful handling of corrupted settings files
- Preservation of sensitive data (API keys) during resets

Author: Allen Wu
Version: 1.0.0
"""

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Configuration file paths
CONFIG_DIRECTORY: str = "~/.talktoai"
SETTINGS_FILE: str = "settings.json"
DEFAULT_SETTINGS_FILE: str = "settings_default.json"


class ConfigManager:
    """Manages application configuration settings with persistent JSON storage.
    
    This class handles loading, saving, and managing all application settings.
    Settings are stored in JSON format in the user's home directory for persistence
    across application restarts. The class provides a simple dict-like interface for
    accessing and modifying settings.
    
    Configuration Structure:
        settings.json contains four main sections:
        - hotkeys: Global keyboard shortcuts {"start": str, "stop": str}
        - api: AI provider configuration {"provider": str, "model": str, "api_key": str}
        - voice: Text-to-speech settings {"speed": float, "voice_name": str}
        - response_mode: Output preferences {"voice": bool, "popup": bool}
    
    Attributes:
        config_folder (str): Path to ~/.shortcutai directory
        settings_file (str): Path to settings.json
        default_settings_file (str): Path to settings_default.json (backup)
        settings (Dict[str, Dict]): In-memory settings dictionary
        
    File Locations:
        - ~/.shortcutai/settings.json - Current application settings
        - ~/.shortcutai/settings_default.json - Default settings template
        
    Example:
        >>> config = ConfigManager()
        >>> api_key = config.get("api", "api_key")
        >>> config.set("api", "model", "claude-3-5-sonnet-20241022")
        >>> config.reset_to_default()  # Reset to defaults (preserves API key)
    """

    def __init__(self) -> None:
        """Initialize the config manager and create default settings if needed.
        
        Creates the ~/.shortcutai directory if it doesn't exist, loads existing
        settings from disk, and creates a default settings template for reset
        functionality.
        
        Side Effects:
            - Creates ~/.shortcutai directory if it doesn't exist
            - Loads settings.json if it exists
            - Creates settings_default.json on first run
            - Logs initialization messages
            
        Raises:
            OSError: If directory creation fails (unlikely on modern systems)
        """
        # Expand ~ to user's home directory
        self.config_folder: str = os.path.expanduser("~/.talktoai")        
        os.makedirs(self.config_folder, exist_ok=True)
        
        self.settings_file: str = os.path.join(self.config_folder, "settings.json")
        self.default_settings_file: str = os.path.join(
            self.config_folder, "settings_default.json"
        )
        
        # Load current settings from disk
        self.settings: Dict[str, Any] = self.load_settings()

        # Create default settings file on first run for reset functionality
        if not os.path.exists(self.default_settings_file):
            self._create_default_settings_file()
            
        logger.debug(f"ConfigManager initialized. Settings at {self.settings_file}")

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file or create defaults if file doesn't exist.
        
        Attempts to load settings from settings.json. If the file doesn't exist,
        returns default settings and saves them to disk. If the file is corrupted
        (invalid JSON), logs an error and returns defaults.
        
        Returns:
            Dict[str, Any]: Dictionary of current application settings with structure:
                {
                    "hotkeys": {"start": str, "stop": str},
                    "api": {"provider": str, "model": str, "api_key": str},
                    "voice": {"speed": float, "voice_name": str},
                    "response_mode": {"voice": bool, "popup": bool}
                }
                
        Side Effects:
            - Creates settings.json if it doesn't exist
            - Logs warnings for missing or corrupted settings files
            
        Raises:
            Does not raise exceptions. Returns defaults on any error.
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as file:
                    settings = json.load(file)
                logger.debug("Settings loaded from file")
                return settings
            except json.JSONDecodeError as e:
                logger.error(f"Settings file corrupted (invalid JSON): {e}")
                logger.info("Reverting to default settings")
                return self._get_default_settings()
            except Exception as e:
                logger.error(f"Error reading settings file: {e}")
                return self._get_default_settings()
        else:
            logger.info("Settings file not found. Creating with default values")
            default_settings = self._get_default_settings()
            self._save_settings(default_settings)
            return default_settings

    def _get_default_settings(self) -> Dict[str, Dict[str, Any]]:
        """Return default application settings.
        
        Provides the canonical set of default settings used when initializing
        or resetting the application. These defaults ensure the app starts
        with sensible values for all configuration options.
        
        Returns:
            Dict[str, Dict[str, Any]]: Default settings structure with all required keys:
                {
                    "hotkeys": {"start": "cmd+option+space", "stop": "esc"},
                    "api": {"provider": "", "model": "", "api_key": ""},
                    "voice": {"speed": 1.0, "voice_name": "Alex"},
                    "response_mode": {"voice": True, "popup": True}
                }
                
        Note:
            These defaults are designed for macOS. Windows/Linux users may need
            to update hotkey values (e.g., "cmd" → "ctrl").
        """
        return {
            "hotkeys": {
                "start": "cmd+option+space",
                "stop": "esc"
            },
            "api": {
                "provider": "",
                "model": "",
                "api_key": ""
            },
            "voice": {
                "speed": 1.0,
                "voice_name": "Alex"
            },
            "response_mode": {
                "voice": True,
                "popup": True
            }
        }

    def _create_default_settings_file(self) -> None:
        """Create a default settings file that users can reset to.
        
        Writes the default settings to settings_default.json as a template.
        This file is used by reset_to_default() to restore settings while
        preserving API credentials.
        
        Side Effects:
            - Creates settings_default.json in config directory
            - Logs info message on success
            - Logs error message on failure (but doesn't raise)
            
        Raises:
            Does not raise exceptions. Logs errors instead.
        """
        try:
            default_settings = self._get_default_settings()
            with open(self.default_settings_file, "w") as file:
                json.dump(default_settings, file, indent=2)
            logger.info("Default settings template created")
        except Exception as e:
            logger.error(f"Failed to create default settings file: {e}")

    def _save_settings(self, settings: Dict[str, Any]) -> None:
        """Write settings dictionary to settings.json file.
        
        Persists the settings dictionary to disk as formatted JSON. This is called
        after any settings update to ensure changes survive application restart.
        
        Args:
            settings (Dict[str, Any]): Dictionary of settings to save to disk
            
        Side Effects:
            - Writes to settings.json file
            - Overwrites existing file if present
            - Logs errors on write failure (but doesn't raise)
            
        Raises:
            Does not raise exceptions. Logs errors instead.
            
        Note:
            Uses indent=2 for readable JSON output. File is compatible with
            manual editing if user wants to configure settings outside the UI.
        """
        try:
            with open(self.settings_file, "w") as file:
                json.dump(settings, file, indent=2)
            logger.debug("Settings saved to file")
        except Exception as e:
            logger.error(f"Failed to save settings to file: {e}")

    def get(self, section: str, key: str) -> Any:
        """Retrieve a setting value from a specific section.
        
        Provides dict-like access to nested settings. Returns None if either
        the section or key doesn't exist (safe access, no KeyError).
        
        Args:
            section (str): Settings section name (e.g., "api", "hotkeys", "voice")
            key (str): Setting key within the section (e.g., "provider", "start")
            
        Returns:
            Any: The setting value (typically str, float, or bool). Returns None
                if section or key doesn't exist.
                
        Example:
            >>> api_key = config.get("api", "api_key")  # Returns str or None
            >>> speed = config.get("voice", "speed")     # Returns float or None
            >>> start_key = config.get("hotkeys", "start")  # Returns str or None
            
        Note:
            Safe to call with non-existent sections/keys - returns None instead
            of raising KeyError. This allows lenient access patterns.
        """
        return self.settings.get(section, {}).get(key)

    def set(self, section: str, key: str, value: Any) -> None:
        """Update a setting value and persist to disk.
        
        Updates a setting in the specified section and immediately saves changes
        to settings.json. If the section doesn't exist, creates it. This ensures
        settings are preserved even if the application crashes.
        
        Args:
            section (str): Settings section name (e.g., "api", "hotkeys", "voice").
                Created if it doesn't exist.
            key (str): Setting key within the section (e.g., "provider", "model")
            value (Any): The new value to set (typically str, float, or bool)
            
        Side Effects:
            - Updates self.settings dictionary
            - Persists changes to settings.json
            - Logs debug message with new value
            
        Raises:
            Does not raise exceptions. Logs errors on write failure.
            
        Example:
            >>> config.set("api", "provider", "Claude")
            >>> config.set("voice", "speed", 1.5)
            >>> config.set("hotkeys", "start", "cmd+shift+space")
            
        Note:
            Changes are immediately saved to disk, so this is safe to call
            frequently without explicit save() call.
        """
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self._save_settings(self.settings)
        logger.debug(f"Updated {section}.{key} = {value}")

    def reset_to_default(self) -> None:
        """Reset all settings to defaults while preserving API credentials.
        
        Resets all settings (hotkeys, voice, response_mode) to their default values,
        but preserves the current API configuration (provider, model, api_key).
        This is useful when users want to restore default behavior while keeping
        their authentication credentials.
        
        Side Effects:
            - Loads settings from settings_default.json
            - Overwrites current settings (except API section)
            - Persists changes to settings.json
            - Logs info message on success
            
        Raises:
            Does not raise exceptions. Logs errors on failure.
            
        Note:
            API settings are intentionally preserved because users don't want to
            lose their API keys and provider configuration during reset.
            
        Example:
            >>> config.reset_to_default()
            >>> # Hotkeys, voice, and response_mode are reset
            >>> # But api.provider, api.model, api.api_key are preserved
        """
        try:
            if not os.path.exists(self.default_settings_file):
                logger.error("Default settings file not found. Cannot reset.")
                return

            with open(self.default_settings_file, "r") as f:
                default_settings = json.load(f)

            # Preserve current API settings (credentials, provider, model)
            if "api" in self.settings:
                default_settings["api"] = self.settings["api"]
                logger.debug("Preserved API settings during reset")

            self.settings = default_settings
            self._save_settings(self.settings)
            logger.info("Settings reset to default (API configuration preserved)")
            
        except Exception as e:
            logger.error(f"Failed to reset settings to default: {e}")

    def save_as_default(self) -> None:
        """Save current settings as the new default settings.
        
        Overwrites settings_default.json with the current settings, making
        the current configuration the new "default" state. Useful when users
        have customized their setup and want to preserve it as the baseline.
        
        Side Effects:
            - Overwrites settings_default.json with current settings
            - Logs info message on success
            
        Raises:
            Does not raise exceptions. Logs errors on failure.
            
        Note:
            This changes what reset_to_default() will reset to. Use carefully
            as it affects the reset functionality going forward.
            
        Example:
            >>> config.set("voice", "speed", 1.5)
            >>> config.set("hotkeys", "start", "cmd+shift+space")
            >>> config.save_as_default()
            >>> # These settings are now the new defaults
        """
        try:
            with open(self.default_settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
            logger.info("Current settings saved as new defaults")
        except Exception as e:
            logger.error(f"Failed to save current settings as default: {e}")