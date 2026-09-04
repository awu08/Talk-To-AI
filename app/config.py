"""Manages application settings stored in a JSON file in the user's home directory."""

import os
import json
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """Handles loading and saving application configuration settings."""

    def __init__(self):
        self.config_folder = os.path.expanduser("~/.shortcutai")
        os.makedirs(self.config_folder, exist_ok=True)
        self.settings_file = os.path.join(self.config_folder, "settings.json")
        self.settings = self.load_settings()

    def load_settings(self):
        """Load settings from file or create default settings if they don't exist."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                logger.error("Settings file is corrupted, using defaults")
                return self._get_default_settings()
        else:
            logger.info("No settings file found, creating defaults")
            default_settings = self._get_default_settings()
            self._save_settings(default_settings)
            return default_settings

    def _get_default_settings(self):
        """Return default application settings."""
        return {
            "hotkeys": {"start": "cmd+option+space", "stop": "esc"},
            "api": {"provider": "", "model": "", "api_key": ""},
            "voice": {"speed": 1.0, "voice_name": "Alex"},
            "response_mode": {"voice": True, "popup": True},
        }

    def _save_settings(self, settings):
        """Write settings to file."""
        try:
            with open(self.settings_file, "w") as file:
                json.dump(settings, file, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, section, key):
        """Retrieve a setting value."""
        return self.settings.get(section, {}).get(key)

    def set(self, section, key, value):
        """Update a setting value and save to file."""
        if section not in self.settings:
            self.settings[section] = {}
        self.settings[section][key] = value
        self._save_settings(self.settings)
        logger.debug(f"Updated {section}.{key} = {value}")