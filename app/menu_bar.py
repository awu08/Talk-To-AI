"""Manages the system tray icon, context menu, and settings panel for the voice assistant."""

import os
import sys
import logging
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon
from app.settings_panel import SettingsPanel

logger = logging.getLogger(__name__)


class MenuBar:
    """Manages the system tray icon and application menu."""

    def __init__(self, config, hotkey_listener):
        """Initialize the menu bar and system tray icon."""
        self.config = config
        self.hotkey_listener = hotkey_listener

        # Create and display tray icon
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "..", "muted_microphone.png")
        icon = QIcon(icon_path)
        self.tray_icon = QSystemTrayIcon(icon)

        # Create context menu
        self.menu = QMenu()
        quit_action = self.menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()
        logger.debug("System tray icon initialized")

        # Initialize settings panel
        self.settings_panel = SettingsPanel(config, hotkey_listener)
        self.settings_panel.show()

    def change_icon(self, icon_name):
        """Change the system tray icon."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "..", icon_name)
        
        if not os.path.exists(icon_path):
            logger.error(f"Icon file not found: {icon_path}")
            return
        
        icon = QIcon(icon_path)
        self.tray_icon.setIcon(icon)
        logger.debug(f"Icon changed to {icon_name}")

    def quit_app(self):
        """Quit the application."""
        logger.info("Application quit requested")
        sys.exit(0)