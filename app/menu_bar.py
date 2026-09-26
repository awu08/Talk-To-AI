"""Menu Bar: System tray icon and application menu management.

This module provides the menu bar interface for the Talk-To-AI application,
including the system tray icon, context menu, and settings window management.
The tray icon serves as the primary UI, displaying the application state
(recording/idle) and providing access to settings and quit functions.

The menu includes modern styling with hover effects and separators, providing
a native-feeling macOS/Windows experience.

Author: Allen Wu
Version: 1.0.0
"""

import os
import sys
import logging
from typing import Optional
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMainWindow
from PyQt6.QtGui import QIcon, QCursor
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

# Menu styling constants
MENU_STYLESHEET: str = """
    QMenu {
        background-color: #ffffff;
        color: #1a1a1a;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        padding: 6px 0px;
    }
    
    QMenu::item {
        padding: 10px 20px;
        background-color: transparent;
        margin: 2px 4px;
        border-radius: 4px;
        font-size: 13px;
    }
    
    QMenu::item:selected {
        background-color: #007AFF;
        color: #ffffff;
    }
    
    QMenu::item:pressed {
        background-color: #0056b3;
    }
    
    QMenu::separator {
        height: 1px;
        background-color: #e0e0e0;
        margin: 4px 0px;
    }
"""


class MenuBar:
    """Manages the system tray icon, context menu, and settings window.
    
    This class handles the primary UI for the Talk-To-AI application. The system
    tray icon serves as the main access point, showing recording state via icon
    changes and providing a context menu for settings and quit functions.
    
    The tray icon responds to clicks by displaying a context menu with styled
    appearance. The settings window is created on-demand and cached for quick
    reopening.
    
    Attributes:
        config (ConfigManager): Configuration manager for application settings
        hotkey_listener (HotkeyListener): Hotkey listener for settings updates
        ai_handler (AIHandler): AI handler for clearing conversation history
        tray_icon (QSystemTrayIcon): System tray icon instance
        menu (QMenu): Context menu displayed on tray icon click
        settings_window (Optional[QMainWindow]): Settings window (created on demand)
        settings_panel (Optional[SettingsPanel]): Settings panel widget
        
    Features:
    - System tray icon with recording state indication
    - Context menu with Settings and Quit options
    - Modern styling with hover effects
    - On-demand settings window creation and caching
    - Icon changing to indicate recording state
    
    Example:
        >>> menu_bar = MenuBar(config, hotkey_listener, ai_handler)
        >>> # Tray icon now visible; user can click to access settings
        >>> menu_bar.change_icon("unmuted_microphone.png")  # Show recording state
        
    Note:
        Requires PyQt6 and Qt runtime. Tray icon may not be visible on headless
        or minimal desktop environments.
    """

    def __init__(
        self, 
        config, 
        hotkey_listener, 
        ai_handler
    ) -> None:
        """Initialize the menu bar and system tray icon.
        
        Creates the system tray icon with the muted microphone image and sets up
        the context menu with Settings and Quit options. Applies modern styling
        to the menu for a polished appearance.
        
        Args:
            config: ConfigManager instance providing application settings
            hotkey_listener: HotkeyListener instance for access in settings
            ai_handler: AIHandler instance for conversation history management
            
        Side Effects:
            - Creates system tray icon and makes it visible
            - Initializes context menu with styled appearance
            - Logs initialization message
            
        Raises:
            FileNotFoundError: If muted_microphone.png icon file not found
            RuntimeError: If Qt platform is not available (headless environment)
        """
        self.config = config
        self.hotkey_listener = hotkey_listener
        self.ai_handler = ai_handler
        self.settings_window: Optional[QMainWindow] = None
        self.settings_panel = None

        # Create system tray icon from image file
        current_dir: str = os.path.dirname(os.path.abspath(__file__))
        icon_path: str = os.path.join(current_dir, "..", "muted_microphone.png")
        
        if not os.path.exists(icon_path):
            logger.error(f"Icon file not found: {icon_path}")
            raise FileNotFoundError(f"Microphone icon not found at {icon_path}")
        
        icon: QIcon = QIcon(icon_path)
        self.tray_icon: QSystemTrayIcon = QSystemTrayIcon(icon)

        # Create styled context menu
        self.menu: QMenu = QMenu()
        self.menu.setStyleSheet(MENU_STYLESHEET)

        # Add Settings action
        settings_action = self.menu.addAction("Settings")
        settings_action.triggered.connect(self.show_settings)

        # Add separator between settings and quit
        self.menu.addSeparator()

        # Add Quit action
        quit_action = self.menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app)

        # Connect tray icon click to show menu
        self.tray_icon.activated.connect(self.on_tray_icon_clicked)
        self.tray_icon.show()
        
        logger.info("System tray menu initialized")

    def on_tray_icon_clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle system tray icon click and show context menu.
        
        When the user clicks the tray icon, displays the context menu at the
        cursor position. Uses the ActivationReason to handle different click
        types appropriately (single click, double click, etc.).
        
        Args:
            reason (QSystemTrayIcon.ActivationReason): The type of activation
                (Trigger for single click, DoubleClick for double click, etc.)
                
        Side Effects:
            - Displays context menu at cursor position if single click (Trigger)
            - Menu positioning uses current mouse cursor position
            
        Note:
            Only responds to Trigger (single click). Double clicks and other
            activation reasons are ignored.
        """
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Display menu at cursor location
            self.menu.popup(QCursor.pos())
            logger.debug("Context menu displayed at cursor")

    def show_settings(self) -> None:
        """Open or bring to front the settings window.
        
        Creates the settings window on first call and caches it for subsequent
        opens. On subsequent calls, brings the existing window to the foreground.
        This is more efficient than recreating the window each time.
        
        The settings window contains the SettingsPanel with all configuration
        options (hotkeys, API settings, voice settings, response mode).
        
        Window Management:
            - First call: Creates QMainWindow with SettingsPanel as central widget
            - Subsequent calls: Brings cached window to foreground
            - Closing settings window hides it (doesn't destroy it)
            - Window can be reopened multiple times from tray menu
        
        Side Effects:
            - Creates settings window and panel on first call (cached for reuse)
            - Subsequent calls bring existing window to foreground
            - Sets window geometry to reasonable defaults (100, 100, 450, 550)
            - Stores reference to settings_window in settings_panel
            - Logs debug message
            
        Raises:
            Does not raise exceptions. Logs error if window creation fails.
            
        Note:
            The settings_window is stored in self so it persists between calls.
            The SettingsPanel stores a reference to the window so the close button
            can hide it without closing the entire application.
        """
        try:
            if self.settings_window is None:
                logger.debug("Creating settings window")
                
                # Create main window container for settings panel
                self.settings_window = QMainWindow()
                self.settings_window.setWindowTitle("Talk-To-AI Settings")
                self.settings_window.setGeometry(100, 100, 450, 550)
                
                # Create settings panel with access to config and handlers
                from app.settings_panel import SettingsPanel
                self.settings_panel = SettingsPanel(
                    self.config, 
                    self.hotkey_listener, 
                    self.ai_handler
                )
                self.settings_window.setCentralWidget(self.settings_panel)
                
                # Store reference to settings_window in panel for close button
                self.settings_panel.settings_window = self.settings_window
                
                logger.debug("Settings window and panel created")
            
            # Bring existing window to foreground
            self.settings_window.show()
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            logger.debug("Settings window brought to foreground")
            
        except Exception as e:
            logger.error(f"Error opening settings window: {e}", exc_info=True)

    def change_icon(self, icon_name: str) -> None:
        """Change the system tray icon to indicate application state.
        
        Updates the tray icon image to show recording state (unmuted microphone)
        or idle state (muted microphone). The icon change provides visual feedback
        that the hotkey was successfully detected.
        
        Args:
            icon_name (str): Filename of the icon to display (e.g.,
                "unmuted_microphone.png", "muted_microphone.png"). File must
                exist in the project root directory.
                
        Side Effects:
            - Updates tray icon display
            - Logs debug message with icon name
            
        Raises:
            Does not raise exceptions. Logs error and returns if icon not found.
            
        Example:
            >>> menu_bar.change_icon("unmuted_microphone.png")  # Recording
            >>> menu_bar.change_icon("muted_microphone.png")    # Idle
            
        Note:
            Icon file should be in project root (parent of app/ directory).
            Supported formats: PNG, JPG, SVG (depends on Qt image plugin support).
        """
        try:
            current_dir: str = os.path.dirname(os.path.abspath(__file__))
            icon_path: str = os.path.join(current_dir, "..", icon_name)

            if not os.path.exists(icon_path):
                logger.error(f"Icon file not found: {icon_path}")
                return

            icon: QIcon = QIcon(icon_path)
            self.tray_icon.setIcon(icon)
            logger.debug(f"Tray icon changed to: {icon_name}")
            
        except Exception as e:
            logger.error(f"Error changing icon: {e}", exc_info=True)

    def quit_app(self) -> None:
        """Gracefully quit the application.
        
        Terminates the application with exit code 0 (success). Called when user
        selects "Quit" from the context menu.
        
        Side Effects:
            - Logs info message
            - Calls sys.exit(0) which terminates the process
            - All threads (including daemon threads) are cleaned up
            
        Note:
            This is a hard exit. No cleanup code is executed. If cleanup is needed
            before exit, consider adding signal handlers instead of calling exit
            directly.
        """
        logger.info("Application quit initiated by user")
        sys.exit(0)