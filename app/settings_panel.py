"""Settings Panel: Configuration UI for Talk-To-AI application.

This module provides the settings interface for the Talk-To-AI application,
allowing users to configure hotkeys, API providers and credentials, voice
settings, and response modes. All changes are automatically saved to the
configuration file.

The settings panel is displayed in a window accessible from the system tray
menu. It provides a user-friendly interface for all configurable options,
with real-time saving of changes.

Author: Allen Wu
Version: 1.0.0
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

# Voice option constants
AVAILABLE_VOICES: list = ["Alex", "Victoria", "Moira", "Fiona"]

# Voice speed slider constants
VOICE_SPEED_MIN: int = 50
VOICE_SPEED_MAX: int = 200
VOICE_SPEED_DEFAULT: int = 100

# AI provider options
AI_PROVIDERS: list = ["", "Claude", "ChatGPT", "Gemini"]

# Window geometry constants
SETTINGS_WINDOW_WIDTH: int = 400
SETTINGS_WINDOW_HEIGHT: int = 600
SETTINGS_WINDOW_X: int = 100
SETTINGS_WINDOW_Y: int = 100


class SettingsPanel(QMainWindow):
    """UI panel for configuring all Talk-To-AI application settings.
    
    This class provides a comprehensive settings interface organized into
    logical sections: Hotkeys, API Settings, Voice Settings, and Response Mode.
    All changes are automatically persisted to the configuration file.
    
    The panel is designed to be embedded in a QMainWindow and includes widgets
    for every configurable option in the application. Each setting change
    immediately updates the configuration through the ConfigManager.
    
    Features:
    - Organized sections for different setting categories
    - Real-time configuration saving on every change
    - Password-masked API key field for security
    - Voice speed slider with visual feedback
    - Clear Chat History button for conversation context management
    
    Attributes:
        config (ConfigManager): Configuration manager for reading/writing settings
        hotkey_listener (HotkeyListener): Hotkey listener for future updates
        ai_handler (AIHandler): AI handler for clearing conversation history
        
        Hotkey Widgets:
            start_hotkey (QLineEdit): Display-only field for start hotkey
            stop_hotkey (QLineEdit): Display-only field for stop hotkey
            
        API Widgets:
            api_provider (QComboBox): Dropdown to select AI provider
            api_model (QLineEdit): Text field for model name
            api_key (QLineEdit): Password field for API key
            
        Voice Widgets:
            voice_speed (QSlider): Slider for voice speed (50-200%)
            voice_name (QComboBox): Dropdown to select voice
            
        Response Mode Widgets:
            response_voice (QCheckBox): Enable/disable voice response
            response_popup (QCheckBox): Enable/disable popup response
    
    Example:
        >>> from app.config import ConfigManager
        >>> config = ConfigManager()
        >>> panel = SettingsPanel(config, hotkey_listener, ai_handler)
        >>> # panel can now be added to a QMainWindow as central widget
    """

    def __init__(
        self,
        config,
        hotkey_listener,
        ai_handler
    ) -> None:
        """Initialize settings panel with all configuration widgets.
        
        Creates a settings panel with organized sections for hotkeys, API settings,
        voice settings, and response modes. Loads current values from configuration
        and connects all widgets to the settings_change callback for real-time saving.
        
        Args:
            config: ConfigManager instance providing current settings
            hotkey_listener: HotkeyListener instance (for future hotkey updates)
            ai_handler: AIHandler instance for clearing conversation history
            
        Side Effects:
            - Creates all UI widgets and organizes them in layout
            - Loads current settings from config into widgets
            - Connects all widgets to settings_change callback
            - Logs initialization message
            
        Raises:
            AttributeError: If config/hotkey_listener/ai_handler don't have
                required methods (get, set, clear_history)
        """
        super().__init__()
        self.config = config
        self.hotkey_listener = hotkey_listener
        self.ai_handler = ai_handler

        # Set window properties
        self.setWindowTitle("Talk-To-AI Settings")
        self.setGeometry(
            SETTINGS_WINDOW_X,
            SETTINGS_WINDOW_Y,
            SETTINGS_WINDOW_WIDTH,
            SETTINGS_WINDOW_HEIGHT
        )

        # Create central widget and main layout
        central_widget: QWidget = QWidget()
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout()
        central_widget.setLayout(layout)

        # ===== HOTKEYS SECTION =====
        layout.addWidget(QLabel("Hotkeys"))
        
        self.start_hotkey: QLineEdit = QLineEdit()
        self.start_hotkey.setText(self.config.get("hotkeys", "start") or "")
        self.start_hotkey.setReadOnly(True)
        layout.addWidget(QLabel("Start Hotkey:"))
        layout.addWidget(self.start_hotkey)

        self.stop_hotkey: QLineEdit = QLineEdit()
        self.stop_hotkey.setText(self.config.get("hotkeys", "stop") or "")
        self.stop_hotkey.setReadOnly(True)
        layout.addWidget(QLabel("Stop Hotkey:"))
        layout.addWidget(self.stop_hotkey)

        layout.addWidget(QLabel(""))

        # ===== API SETTINGS SECTION =====
        layout.addWidget(QLabel("API Settings"))
        
        self.api_provider: QComboBox = QComboBox()
        self.api_provider.addItems(AI_PROVIDERS)
        self.api_provider.setCurrentText(self.config.get("api", "provider") or "")
        self.api_provider.currentTextChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Provider:"))
        layout.addWidget(self.api_provider)
        
        self.api_model: QLineEdit = QLineEdit()
        self.api_model.setText(self.config.get("api", "model") or "")
        self.api_model.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Model:"))
        layout.addWidget(self.api_model)
        
        self.api_key: QLineEdit = QLineEdit()
        self.api_key.setText(self.config.get("api", "api_key") or "")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("API Key:"))
        layout.addWidget(self.api_key)
        
        layout.addWidget(QLabel(""))

        # ===== VOICE SETTINGS SECTION =====
        layout.addWidget(QLabel("Voice Settings"))
        
        self.voice_speed: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.voice_speed.setMinimum(VOICE_SPEED_MIN)
        self.voice_speed.setMaximum(VOICE_SPEED_MAX)
        voice_speed_value: float = self.config.get("voice", "speed") or 1.0
        self.voice_speed.setValue(int(voice_speed_value * 100))
        self.voice_speed.sliderMoved.connect(self.settings_change)
        layout.addWidget(QLabel("Speed (50-200%):"))
        layout.addWidget(self.voice_speed)
        
        self.voice_name: QComboBox = QComboBox()
        self.voice_name.addItems(AVAILABLE_VOICES)
        self.voice_name.setCurrentText(self.config.get("voice", "voice_name") or "Alex")
        self.voice_name.currentTextChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Voice:"))
        layout.addWidget(self.voice_name)
        
        layout.addWidget(QLabel(""))

        # ===== RESPONSE MODE SECTION =====
        layout.addWidget(QLabel("Response Mode"))
        
        self.response_voice: QCheckBox = QCheckBox("Voice Response")
        self.response_voice.setChecked(self.config.get("response_mode", "voice") or True)
        self.response_voice.stateChanged.connect(self.settings_change)
        layout.addWidget(self.response_voice)
        
        self.response_popup: QCheckBox = QCheckBox("Popup Response")
        self.response_popup.setChecked(self.config.get("response_mode", "popup") or True)
        self.response_popup.stateChanged.connect(self.settings_change)
        layout.addWidget(self.response_popup)
        
        layout.addWidget(QLabel(""))

        # ===== CLEAR HISTORY SECTION =====
        clear_history_button: QPushButton = QPushButton("Clear Chat History")
        clear_history_button.clicked.connect(self.clear_chat_history)
        layout.addWidget(clear_history_button)
        
        layout.addWidget(QLabel(""))
        # ===== END CLEAR HISTORY SECTION =====
        
        # ===== CLOSE BUTTON =====
        close_button: QPushButton = QPushButton("Close")
        close_button.clicked.connect(lambda: self.settings_window.hide() if hasattr(self, 'settings_window') else self.hide())
        layout.addWidget(close_button)

        logger.debug("SettingsPanel initialized successfully")

    def settings_change(self) -> None:
        """Save all settings changes to the configuration file.
        
        Called whenever any setting widget changes (text field, slider, checkbox,
        or dropdown). Reads all current widget values and saves them to the
        configuration through the ConfigManager. This ensures settings are
        persisted immediately and survive application restarts.
        
        Side Effects:
            - Reads all widget values
            - Writes updated values to config
            - Config writes to settings.json file
            - Logs debug message for each setting update
            
        Raises:
            Does not raise exceptions. Logs errors if config write fails.
            
        Note:
            This method is connected to every settings widget's change signal,
            so it's called frequently. This ensures zero data loss if app crashes,
            but also means config file is rewritten often. This is acceptable
            for small JSON files.
        """
        try:
            # Save hotkey settings
            self.config.set("hotkeys", "start", self.start_hotkey.text())
            self.config.set("hotkeys", "stop", self.stop_hotkey.text())
            
            # Save API settings
            self.config.set("api", "provider", self.api_provider.currentText())
            self.config.set("api", "model", self.api_model.text())
            self.config.set("api", "api_key", self.api_key.text())
            
            # Save voice settings (convert slider 0-200 to 0.5-2.0 multiplier)
            self.config.set("voice", "speed", self.voice_speed.value() / 100)
            self.config.set("voice", "voice_name", self.voice_name.currentText())
            
            # Save response mode settings
            self.config.set("response_mode", "voice", self.response_voice.isChecked())
            self.config.set("response_mode", "popup", self.response_popup.isChecked())
            
            logger.debug("Settings updated and saved to configuration")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)

    def clear_chat_history(self) -> None:
        """Clear the AI conversation history and reset context.
        
        Resets the conversation history in the AIHandler, effectively starting
        fresh with a new conversation context. This removes all previous messages
        from memory, so the next AI response won't reference past interactions.
        
        Useful when:
        - User wants to start a new conversation topic
        - User wants to reset AI context for privacy
        - Conversation history becomes too large
        
        Side Effects:
            - Calls ai_handler.clear_history() to reset conversation
            - Logs info message
            - Prints console message for user feedback
            
        Raises:
            Does not raise exceptions. Logs errors if clearing fails.
            
        Note:
            This does not affect saved settings or configuration. It only
            clears the in-memory conversation history for the current session.
        """
        try:
            self.ai_handler.clear_history()
            logger.info("User cleared chat history from settings panel")
            print("Chat history cleared! Starting fresh.")
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}", exc_info=True)
            print(f"Failed to clear chat history: {e}")