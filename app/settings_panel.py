"""Provides a UI for configuring hotkeys, API settings, voice preferences, and response modes. Includes interactive hotkey picker that listens for keyboard input."""

import logging
from threading import Thread
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QCheckBox,
    QComboBox,
)
from PyQt6.QtCore import Qt
from pynput import keyboard

logger = logging.getLogger(__name__)


class SettingsPanel(QMainWindow):
    """Configuration panel for voice assistant settings."""

    def __init__(self, config, hotkey_listener):
        """Initialize the settings panel."""
        super().__init__()
        self.config = config
        self.hotkey_listener = hotkey_listener
        self.is_picking_hotkey = False
        self.pressed_keys = set()
        self.current_field = None
        self.had_keys = False

        self.setWindowTitle("ShortcutAI Settings")
        self.setGeometry(100, 100, 400, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Hotkeys section
        layout.addWidget(QLabel("Hotkeys"))

        self.start_hotkey = QLineEdit()
        self.start_hotkey.setText(self.config.get("hotkeys", "start"))
        self.start_hotkey.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Start Hotkey:"))
        layout.addWidget(self.start_hotkey)

        self.stop_hotkey = QLineEdit()
        self.stop_hotkey.setText(self.config.get("hotkeys", "stop"))
        self.stop_hotkey.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Stop Hotkey:"))
        layout.addWidget(self.stop_hotkey)

        layout.addWidget(QLabel(""))

        # API settings section
        layout.addWidget(QLabel("API Settings"))

        self.api_provider = QComboBox()
        self.api_provider.addItems(["", "Claude", "ChatGPT", "Gemini"])
        self.api_provider.setCurrentText(self.config.get("api", "provider"))
        self.api_provider.currentTextChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Provider:"))
        layout.addWidget(self.api_provider)

        self.api_model = QLineEdit()
        self.api_model.setText(self.config.get("api", "model"))
        self.api_model.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Model:"))
        layout.addWidget(self.api_model)

        self.api_key = QLineEdit()
        self.api_key.setText(self.config.get("api", "api_key"))
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.textChanged.connect(self.settings_change)
        layout.addWidget(QLabel("API Key:"))
        layout.addWidget(self.api_key)

        layout.addWidget(QLabel(""))

        # Voice settings section
        layout.addWidget(QLabel("Voice Settings"))

        self.voice_speed = QSlider(Qt.Orientation.Horizontal)
        self.voice_speed.setMinimum(50)
        self.voice_speed.setMaximum(200)
        self.voice_speed.setValue(int(self.config.get("voice", "speed") * 100))
        self.voice_speed.sliderMoved.connect(self.settings_change)
        layout.addWidget(QLabel("Speed:"))
        layout.addWidget(self.voice_speed)

        self.voice_name = QComboBox()
        self.voice_name.addItems(["Alex", "Victoria", "Moira", "Fiona"])
        self.voice_name.setCurrentText(self.config.get("voice", "voice_name"))
        self.voice_name.currentTextChanged.connect(self.settings_change)
        layout.addWidget(QLabel("Voice:"))
        layout.addWidget(self.voice_name)

        layout.addWidget(QLabel(""))

        # Response mode section
        layout.addWidget(QLabel("Response Mode"))

        self.response_voice = QCheckBox("Voice Response")
        self.response_voice.setChecked(self.config.get("response_mode", "voice"))
        self.response_voice.stateChanged.connect(self.settings_change)
        layout.addWidget(self.response_voice)

        self.response_popup = QCheckBox("Popup Response")
        self.response_popup.setChecked(self.config.get("response_mode", "popup"))
        self.response_popup.stateChanged.connect(self.settings_change)
        layout.addWidget(self.response_popup)

        layout.addWidget(QLabel(""))

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        logger.debug("Settings panel initialized")

    def start_hotkey_picking(self, field):
        """Start listening for a hotkey combination."""
        self.is_picking_hotkey = True
        self.pressed_keys = set()
        self.current_field = field
        self.had_keys = False

        field.setEnabled(False)
        field.setText("Press your hotkey...")

        # Pause global hotkey listener
        self.hotkey_listener.pause()

        # Start listening in background thread
        thread = Thread(target=self._listen_for_hotkey, daemon=True)
        thread.start()
        logger.debug("Hotkey picking started")

    def _listen_for_hotkey(self):
        """Listen for keypresses and capture hotkey combination."""
        listener = None
        try:

            def on_press(key):
                if self.is_picking_hotkey:
                    self.pressed_keys.add(key)
                    self.had_keys = True
                    self.update_preview()

            def on_release(key):
                if not self.is_picking_hotkey:
                    return False

                if key in self.pressed_keys:
                    self.pressed_keys.discard(key)

                    # If all keys released and we had keys, save
                    if not self.pressed_keys and self.had_keys:
                        self.save_hotkey()
                        return False

                return True

            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.start()

            # Wait until picking is done
            while self.is_picking_hotkey:
                pass

            if listener:
                listener.stop()
        except Exception as e:
            logger.error(f"Hotkey picker error: {e}")
            self.is_picking_hotkey = False
            self.hotkey_listener.resume()

    def update_preview(self):
        """Display the currently pressed keys in the input field."""
        if self.current_field and self.pressed_keys:
            key_strings = []
            for key in self.pressed_keys:
                try:
                    if hasattr(key, "name"):
                        key_strings.append(key.name)
                    elif hasattr(key, "char"):
                        key_strings.append(key.char)
                    else:
                        key_strings.append(str(key))
                except Exception:
                    key_strings.append(str(key))

            key_strings.sort()
            hotkey_str = "+".join(key_strings)
            self.current_field.setText(hotkey_str)

    def save_hotkey(self):
        """Save the captured hotkey and resume the global hotkey listener."""
        self.is_picking_hotkey = False

        if self.current_field:
            self.current_field.setEnabled(True)

        # Resume global hotkey listener
        self.hotkey_listener.resume()

        # Update hotkey listener with new hotkeys
        self.hotkey_listener.update_hotkeys()

        # Save to config
        self.settings_change()
        logger.debug("Hotkey saved and listener resumed")

    def settings_change(self):
        """Save all settings changes to config."""
        self.config.set("hotkeys", "start", self.start_hotkey.text())
        self.config.set("hotkeys", "stop", self.stop_hotkey.text())

        self.config.set("api", "provider", self.api_provider.currentText())
        self.config.set("api", "model", self.api_model.text())
        self.config.set("api", "api_key", self.api_key.text())

        self.config.set("voice", "speed", self.voice_speed.value() / 100)
        self.config.set("voice", "voice_name", self.voice_name.currentText())

        self.config.set("response_mode", "voice", self.response_voice.isChecked())
        self.config.set("response_mode", "popup", self.response_popup.isChecked())

        logger.debug("Settings saved")