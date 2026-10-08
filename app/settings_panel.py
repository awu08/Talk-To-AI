"""Settings Panel: Configuration UI for Talk-To-AI application.

This module provides the settings interface for the Talk-To-AI application,
allowing users to configure hotkeys, API providers and credentials, voice
settings, and response modes. All changes are automatically saved to the
configuration file.

The window uses a macOS-style layout: a sidebar of sections on the left and
grouped, rounded cards on the right. Every widget still writes straight to
the ConfigManager the moment it changes.

Author: Allen Wu
Version: 1.1.0
"""

import logging
import re
from typing import Any, List

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QPushButton, QScrollArea, QSlider, QStackedWidget,
    QVBoxLayout, QWidget,
)

from app import app_support, models_catalog
from app.theme import COLORS, icon
from app.transcriber import DEFAULT_ENGINE, DEFAULT_MODEL, WHISPER_MODELS
from app.widgets import Card, KeycapField, SettingRow, ToggleSwitch, label

logger = logging.getLogger(__name__)

# Voice option constants
SYSTEM_DEFAULT_VOICE: str = "System default"  # stored in settings as ""
FALLBACK_VOICES: list = ["Samantha", "Daniel", "Karen", "Moira"]  # if the list can't be read

# Voice speed slider constants
VOICE_SPEED_MIN: int = 50
VOICE_SPEED_MAX: int = 200
VOICE_SPEED_DEFAULT: int = 100

# Speech recognition engines: (label, stored value)
SPEECH_ENGINES: list = [
    ("Whisper (on this Mac)", "whisper"),
    ("Google (online)", "google"),
]

# AI provider options
AI_PROVIDERS: list = ["", "Claude", "ChatGPT", "Gemini"]

# Last entry in the model dropdown: lets the user type any model ID
OTHER_MODEL: str = "__other__"
OTHER_MODEL_LABEL: str = "Other…"

# Window geometry constants
SETTINGS_WINDOW_WIDTH: int = 760
SETTINGS_WINDOW_HEIGHT: int = 690
SETTINGS_WINDOW_X: int = 100
SETTINGS_WINDOW_Y: int = 100
SIDEBAR_WIDTH: int = 210

# Sidebar sections: (label, icon name)
SECTIONS: List[tuple] = [
    ("General", "keyboard"),
    ("AI Model", "sparkles"),
    ("Voice", "wave"),
]


def _bool_setting(value: Any, default: bool = True) -> bool:
    """Read a stored boolean, falling back to `default` only when it is unset."""
    return default if value is None else bool(value)


class SettingsPanel(QMainWindow):
    """UI panel for configuring all Talk-To-AI application settings.

    The window is split into a sidebar and three pages:
        - General: shortcuts, response mode, Open at login and conversation history
        - AI Model: provider, model name and API key
        - Voice: speech recognition engine, voice and speaking speed

    All changes are automatically persisted to the configuration file.

    Attributes:
        config (ConfigManager): Configuration manager for reading/writing settings
        hotkey_listener (HotkeyListener): Hotkey listener for future updates
        ai_handler (AIHandler): AI handler for clearing conversation history

        Hotkey Widgets:
            start_hotkey (KeycapField): Start shortcut; click it to record a new one
            stop_hotkey (KeycapField): Stop shortcut; click it to record a new one

        API Widgets:
            api_provider (QComboBox): Dropdown to select AI provider
            model_choice (QComboBox): Listed models for the provider, plus "Other…"
            api_model (QLineEdit): Custom model ID, shown when "Other…" is picked
            api_key (QLineEdit): Password field for API key

        Voice Widgets:
            voice_speed (QSlider): Slider for voice speed (50-200%)
            voice_name (QComboBox): Dropdown to select voice

        Response Mode Widgets:
            response_voice (ToggleSwitch): Enable/disable voice response
            response_popup (ToggleSwitch): Enable/disable popup response

    Example:
        >>> from app.config import ConfigManager
        >>> config = ConfigManager()
        >>> panel = SettingsPanel(config, hotkey_listener, ai_handler)
        >>> panel.show()
    """

    def __init__(self, config, hotkey_listener, ai_handler) -> None:
        """Initialize settings window with all configuration widgets.

        Args:
            config: ConfigManager instance providing current settings
            hotkey_listener: HotkeyListener instance (for future hotkey updates)
            ai_handler: AIHandler instance for clearing conversation history
        """
        super().__init__()
        self.config = config
        self.hotkey_listener = hotkey_listener
        self.ai_handler = ai_handler
        self._loading: bool = True  # suppress saves while widgets are filled in

        self.setWindowTitle("Talk-To-AI Settings")
        self.setGeometry(SETTINGS_WINDOW_X, SETTINGS_WINDOW_Y,
                         SETTINGS_WINDOW_WIDTH, SETTINGS_WINDOW_HEIGHT)
        self.setMinimumSize(640, 460)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.pages.addWidget(self._page(self._build_general_page()))
        self.pages.addWidget(self._page(self._build_ai_page()))
        self.pages.addWidget(self._page(self._build_voice_page()))
        root_layout.addWidget(self.pages, 1)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        self._loading = False
        # A provider with no saved model: save the recommended one shown in the list
        if self._provider_value() and not self.config.get("api", "model"):
            self.settings_change()
        logger.debug("SettingsPanel initialized successfully")

    # ------------------------------------------------------------------ layout

    def _build_sidebar(self) -> QWidget:
        container = QWidget()
        container.setFixedWidth(SIDEBAR_WIDTH)
        container.setStyleSheet(f"background: {COLORS['sidebar']};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 22, 0, 16)
        layout.setSpacing(0)

        brand = QHBoxLayout()
        brand.setContentsMargins(20, 0, 16, 14)
        brand.setSpacing(10)
        badge = QPushButton()
        badge.setIcon(icon("mic", "#ffffff", 16))
        badge.setIconSize(QSize(16, 16))
        badge.setFixedSize(28, 28)
        badge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        badge.setStyleSheet(
            f"background: {COLORS['accent']}; border-radius: 8px; padding: 0;"
        )
        brand.addWidget(badge)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Talk-To-AI", "rowTitle"))
        names.addWidget(label("Settings", "muted"))
        brand.addLayout(names, 1)
        layout.addLayout(brand)

        section = label("PREFERENCES", "section")
        section.setContentsMargins(18, 6, 0, 4)
        layout.addWidget(section)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setIconSize(QSize(16, 16))
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for name, icon_name in SECTIONS:
            item = QListWidgetItem(icon(icon_name, COLORS["accent"], 16), name)
            item.setSizeHint(QSize(0, 34))
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._tint_sidebar_icons)
        layout.addWidget(self.sidebar, 1)

        footer = label("Settings save automatically", "muted")
        footer.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(footer)
        return container

    def _tint_sidebar_icons(self, current: int) -> None:
        """White icon on the selected row, accent-colored icons elsewhere."""
        for row, (_, icon_name) in enumerate(SECTIONS):
            color = "#ffffff" if row == current else COLORS["accent"]
            self.sidebar.item(row).setIcon(icon(icon_name, color, 16))

    def _page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    def _page_body(self, title: str, subtitle: str) -> tuple:
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(32, 26, 32, 28)
        layout.setSpacing(8)
        layout.addWidget(label(title, "title"))
        layout.addWidget(label(subtitle, "subtitle", wrap=True))
        layout.addSpacing(12)
        return body, layout

    @staticmethod
    def _section(layout: QVBoxLayout, title: str) -> None:
        layout.addSpacing(8)
        layout.addWidget(label(title.upper(), "section"))

    # --------------------------------------------------------------- shortcuts

    def _wire_hotkey(self, field: KeycapField, row: SettingRow, which: str,
                     other: KeycapField) -> None:
        """Connect a shortcut recorder to saving, validation and the listener."""
        def started() -> None:
            other.cancel()
            row.set_hint("Hold modifiers and press a key · click again to cancel")
            if self.hotkey_listener is not None:
                self.hotkey_listener.pause()  # don't fire hotkeys while typing them

        def finished() -> None:
            if self.hotkey_listener is not None:
                self.hotkey_listener.resume()

        def recorded(raw: str) -> None:
            previous = self.config.get("hotkeys", which) or ""
            error = self._hotkey_problem(raw, which, other.raw_text())
            if error:
                field.set_raw_text(previous)
                self._flash_hint(row, error, "error")
                return
            self.settings_change()
            if self.hotkey_listener is not None:
                self.hotkey_listener.update_hotkeys()
            logger.info(f"{which} hotkey set to {raw}")
            self._flash_hint(row, "✓ Saved", "success")

        def rejected(reason: str) -> None:
            self._flash_hint(row, reason, "error")

        def restore_hint_if_cancelled() -> None:
            # Runs after `recorded`, so a "Saved"/error message isn't overwritten.
            if row.hint_label.property("role") not in ("error", "success"):
                row.reset_hint()

        field.recording_started.connect(started)
        field.recording_finished.connect(finished)
        field.recording_finished.connect(
            lambda: QTimer.singleShot(0, restore_hint_if_cancelled))
        field.hotkey_recorded.connect(recorded)
        field.rejected.connect(rejected)

    @staticmethod
    def _hotkey_problem(raw: str, which: str, other_raw: str) -> str:
        """Return a reason the shortcut can't be used, or "" if it's fine."""
        keys = set(raw.split("+"))
        if keys == set(other_raw.split("+")):
            other_name = "Stop and send" if which == "start" else "Start listening"
            return f"Already used for {other_name}. Pick a different shortcut."
        modifiers = {"cmd", "option", "ctrl", "shift"}
        main_key = raw.split("+")[-1]
        is_function_key = re.fullmatch(r"f([1-9]|1[0-2])", main_key) is not None
        if which == "start" and not (keys & (modifiers - {"shift"})) and not is_function_key:
            return "Add ⌘, ⌥ or ⌃ so it doesn't fire while you type."
        return ""

    def _flash_hint(self, row: SettingRow, text: str, role: str) -> None:
        row.set_hint(text, role)
        QTimer.singleShot(2600, row.reset_hint)

    # ------------------------------------------------------------- page: general

    def _build_general_page(self) -> QWidget:
        body, layout = self._page_body(
            "General", "How you start a question and how the answer comes back."
        )

        # ===== HOTKEYS SECTION =====
        self._section(layout, "Shortcuts")
        card = Card()
        self.start_hotkey: KeycapField = KeycapField(self.config.get("hotkeys", "start") or "")
        self.stop_hotkey: KeycapField = KeycapField(self.config.get("hotkeys", "stop") or "")
        start_row = card.add_row(SettingRow("Start listening",
                                            "Press anywhere to ask a question",
                                            self.start_hotkey))
        stop_row = card.add_row(SettingRow("Stop and send",
                                           "Ends recording and sends it to the AI",
                                           self.stop_hotkey))
        self._wire_hotkey(self.start_hotkey, start_row, "start", self.stop_hotkey)
        self._wire_hotkey(self.stop_hotkey, stop_row, "stop", self.start_hotkey)
        layout.addWidget(card)
        tip = label("Click a shortcut to change it.", "muted")
        tip.setContentsMargins(2, 0, 0, 0)
        layout.addWidget(tip)

        # ===== RESPONSE MODE SECTION =====
        self._section(layout, "Responses")
        card = Card()
        self.response_voice: ToggleSwitch = ToggleSwitch()
        self.response_voice.setChecked(
            _bool_setting(self.config.get("response_mode", "voice")))
        self.response_voice.stateChanged.connect(self.settings_change)
        card.add_row(SettingRow("Speak responses", "Read the answer out loud",
                                self.response_voice))

        self.response_popup: ToggleSwitch = ToggleSwitch()
        self.response_popup.setChecked(
            _bool_setting(self.config.get("response_mode", "popup")))
        self.response_popup.stateChanged.connect(self.settings_change)
        card.add_row(SettingRow("Show response window", "Display the answer as text on screen",
                                self.response_popup))
        layout.addWidget(card)

        # ===== APP SECTION =====
        self._section(layout, "App")
        card = Card()
        self.open_at_login: ToggleSwitch = ToggleSwitch()
        supported = app_support.login_item_supported()
        self.open_at_login.setChecked(supported and app_support.is_login_item_enabled())
        self.open_at_login.setEnabled(supported)
        self.open_at_login.toggled.connect(self._on_open_at_login)
        card.add_row(SettingRow(
            "Open at login",
            "Start Talk-To-AI automatically when you log in" if supported
            else "Available when running the Talk-To-AI app (not from Terminal)",
            self.open_at_login))
        layout.addWidget(card)

        # ===== CLEAR HISTORY SECTION =====
        self._section(layout, "Conversation")
        card = Card()
        clear_history_button = QPushButton("Clear history")
        clear_history_button.setProperty("variant", "danger")
        clear_history_button.setIcon(icon("trash", COLORS["red"], 14))
        clear_history_button.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_history_button.clicked.connect(self.clear_chat_history)
        self.history_status = label("", "success")
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)
        controls_layout.addWidget(self.history_status)
        controls_layout.addWidget(clear_history_button)
        card.add_row(SettingRow("Chat history",
                                "The AI remembers earlier questions until you clear it",
                                controls))
        layout.addWidget(card)

        layout.addStretch(1)

        # ===== CLOSE BUTTON =====
        footer = QHBoxLayout()
        footer.addStretch(1)
        close_button = QPushButton("Done")
        close_button.setProperty("variant", "primary")
        close_button.setMinimumWidth(88)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.hide)
        footer.addWidget(close_button)
        layout.addSpacing(12)
        layout.addLayout(footer)
        return body

    # ------------------------------------------------------------------ page: AI

    def _build_ai_page(self) -> QWidget:
        body, layout = self._page_body(
            "AI Model", "Choose who answers your questions."
        )

        # ===== API SETTINGS SECTION =====
        self._section(layout, "Provider")
        card = Card()
        self.api_provider: QComboBox = QComboBox()
        self.api_provider.addItems(AI_PROVIDERS)
        self.api_provider.setItemText(0, "Choose…")
        self.api_provider.setCurrentText(self.config.get("api", "provider") or "Choose…")
        self.api_provider.setMinimumWidth(160)
        self.api_provider.currentTextChanged.connect(self._on_provider_changed)
        card.add_row(SettingRow("Provider", "Claude, ChatGPT or Gemini", self.api_provider))

        # Model: pick from a described list, or "Other…" to type any model ID
        self.model_choice: QComboBox = QComboBox()
        self.model_choice.setMaxVisibleItems(12)
        self.model_description = label("", "rowHint", wrap=True)
        self.api_model: QLineEdit = QLineEdit()  # custom model ID, shown for "Other…"
        self.api_model.setPlaceholderText("Model ID, e.g. gemini-3.7-flash")
        self.model_docs = label("", "muted", wrap=True)
        self.model_docs.setOpenExternalLinks(True)
        self.model_docs.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

        model_box = QWidget()
        model_layout = QVBoxLayout(model_box)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(6)
        model_layout.addWidget(self.model_choice)
        model_layout.addWidget(self.model_description)
        model_layout.addWidget(self.api_model)
        model_layout.addWidget(self.model_docs)
        card.add_row(SettingRow("Model", "Pick one, or choose Other… to use any model",
                                model_box, stacked=True))
        layout.addWidget(card)

        self._fill_models(self.config.get("api", "model") or "")
        self.model_choice.currentIndexChanged.connect(self._on_model_changed)
        self.api_model.textChanged.connect(self.settings_change)

        self._section(layout, "Credentials")
        card = Card()
        self.api_key: QLineEdit = QLineEdit()
        self.api_key.setText(self.config.get("api", "api_key") or "")
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("Paste your API key")
        self.api_key.textChanged.connect(self.settings_change)
        reveal = self.api_key.addAction(icon("eye", COLORS["text_tertiary"], 16),
                                        QLineEdit.ActionPosition.TrailingPosition)
        reveal.setToolTip("Show or hide key")
        reveal.triggered.connect(self._toggle_key_visibility)
        card.add_row(SettingRow("API key", "", self.api_key, stacked=True))
        card.add_row(SettingRow(
            "Stored only on this Mac",
            "Saved in ~/.talktoai/settings.json and sent only to the provider you pick.",
            icon_name="lock",
        ))
        layout.addWidget(card)

        layout.addStretch(1)
        return body

    # ------------------------------------------------------------ model picker

    def _fill_models(self, selected_id: str) -> None:
        """List the current provider's models and select `selected_id`.

        A listed ID selects that entry; any other non-empty ID selects
        "Other…" with the ID filled in; an empty ID selects the provider's
        recommended model.
        """
        provider = self._provider_value()
        self.model_choice.blockSignals(True)
        self.model_choice.clear()
        for model in models_catalog.models_for(provider):
            self.model_choice.addItem(f"{model.name}  ·  {model.tags}", model.id)
        if self.model_choice.count():
            self.model_choice.insertSeparator(self.model_choice.count())
        self.model_choice.addItem(OTHER_MODEL_LABEL, OTHER_MODEL)

        listed = models_catalog.find_model(provider, selected_id)
        if listed:
            self.model_choice.setCurrentIndex(self.model_choice.findData(listed.id))
        elif selected_id:
            self.model_choice.setCurrentIndex(self.model_choice.findData(OTHER_MODEL))
            self.api_model.blockSignals(True)
            self.api_model.setText(selected_id)
            self.api_model.blockSignals(False)
        else:
            default = models_catalog.default_model(provider)
            index = self.model_choice.findData(default.id) if default else -1
            self.model_choice.setCurrentIndex(max(0, index))
        self.model_choice.setEnabled(bool(provider))
        self.model_choice.blockSignals(False)
        self._update_model_details()

    def _update_model_details(self) -> None:
        """Show the selected model's description, or the custom-ID field for Other…"""
        provider = self._provider_value()
        is_other = self.model_choice.currentData() == OTHER_MODEL
        self.api_model.setVisible(is_other)
        if not provider:
            self.model_description.setText("Choose a provider first.")
            self.model_docs.setText("")
            return
        if is_other:
            self.model_description.setText("Type the exact model ID from your provider.")
            url = models_catalog.MODEL_DOCS.get(provider, "")
            link = f'<a href="{url}" style="color:{COLORS["accent_hover"]};">' \
                   f'{provider} model list</a>' if url else "your provider's docs"
            self.model_docs.setText(f"Find model IDs in the {link}.")
            return
        model = models_catalog.find_model(provider, self.model_choice.currentData())
        if model:
            self.model_description.setText(model.description)
            self.model_docs.setText(f"Model ID: {model.id}")

    def _on_model_changed(self, _index: int) -> None:
        self._update_model_details()
        if self.model_choice.currentData() == OTHER_MODEL:
            self.api_model.setFocus()
        self.settings_change()

    def _model_value(self) -> str:
        """The model ID to save: the listed model, or the typed one for Other…"""
        if self.model_choice.currentData() == OTHER_MODEL:
            return self.api_model.text().strip()
        return self.model_choice.currentData() or ""

    def _on_provider_changed(self, _text: str) -> None:
        # Switching provider: keep the model if it belongs to the new provider,
        # otherwise pick the new provider's recommended model.
        current = self._model_value()
        provider = self._provider_value()
        keep = current if models_catalog.find_model(provider, current) else ""
        self.api_model.blockSignals(True)
        self.api_model.clear()
        self.api_model.blockSignals(False)
        self._fill_models(keep)
        self.settings_change()

    def _provider_value(self) -> str:
        """Selected provider name, or "" when the placeholder item is selected."""
        return "" if self.api_provider.currentIndex() == 0 else self.api_provider.currentText()

    def _toggle_key_visibility(self) -> None:
        hidden = self.api_key.echoMode() == QLineEdit.EchoMode.Password
        self.api_key.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password)

    # --------------------------------------------------------------- page: voice

    def _build_voice_page(self) -> QWidget:
        body, layout = self._page_body(
            "Voice", "How it hears you, and how spoken answers sound."
        )

        # ===== SPEECH RECOGNITION SECTION =====
        self._section(layout, "Listening")
        card = Card()
        self.speech_engine: QComboBox = QComboBox()
        for label_text, value in SPEECH_ENGINES:
            self.speech_engine.addItem(label_text, value)
        engine = self.config.get("speech", "engine") or DEFAULT_ENGINE
        self.speech_engine.setCurrentIndex(max(0, self.speech_engine.findData(engine)))
        self.speech_engine.setMinimumWidth(180)
        self.speech_engine.currentIndexChanged.connect(self._on_engine_changed)
        card.add_row(SettingRow("Speech recognition",
                                "Whisper runs on this Mac: free, private and more accurate",
                                self.speech_engine))

        self.speech_model: QComboBox = QComboBox()
        for label_text, model, size in WHISPER_MODELS:
            self.speech_model.addItem(f"{label_text}  ·  {size}", model)
        model = self.config.get("speech", "model") or DEFAULT_MODEL
        self.speech_model.setCurrentIndex(max(0, self.speech_model.findData(model)))
        self.speech_model.setMinimumWidth(180)
        self.speech_model.currentIndexChanged.connect(self.settings_change)
        self.speech_model_row = card.add_row(SettingRow(
            "Whisper accuracy",
            "Bigger is more accurate but slower. Downloads once the first time it's used.",
            self.speech_model))
        layout.addWidget(card)
        self._on_engine_changed(update=False)

        # ===== VOICE SETTINGS SECTION =====
        self._section(layout, "Speech")
        card = Card()
        self.voice_name: QComboBox = QComboBox()
        self.voice_name.addItem(SYSTEM_DEFAULT_VOICE)
        self.voice_name.addItems(self._installed_voices())
        saved_voice = self.config.get("voice", "voice_name") or ""
        if saved_voice and self.voice_name.findText(saved_voice) >= 0:
            self.voice_name.setCurrentText(saved_voice)
        else:
            self.voice_name.setCurrentIndex(0)  # missing (e.g. old "Alex") → default
        self.voice_name.setMaxVisibleItems(14)
        self.voice_name.setMinimumWidth(180)
        self.voice_name.currentTextChanged.connect(self.settings_change)
        card.add_row(SettingRow("Voice", "Voices installed on this Mac. Add more in System "
                                "Settings → Accessibility → Spoken Content", self.voice_name))

        self.voice_speed: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.voice_speed.setMinimum(VOICE_SPEED_MIN)
        self.voice_speed.setMaximum(VOICE_SPEED_MAX)
        voice_speed_value: float = self.config.get("voice", "speed") or 1.0
        self.voice_speed.setValue(int(voice_speed_value * 100))
        self.voice_speed.setCursor(Qt.CursorShape.PointingHandCursor)

        self.speed_value = label("", "value")
        self.speed_value.setMinimumWidth(44)
        self.speed_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        reset = QPushButton()
        reset.setProperty("variant", "ghost")
        reset.setIcon(icon("reset", COLORS["text_secondary"], 14))
        reset.setToolTip("Reset to normal speed")
        reset.setCursor(Qt.CursorShape.PointingHandCursor)
        reset.clicked.connect(lambda: self.voice_speed.setValue(VOICE_SPEED_DEFAULT))

        slider_row = QWidget()
        slider_layout = QHBoxLayout(slider_row)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(10)
        slider_layout.addWidget(label("Slow", "muted"))
        slider_layout.addWidget(self.voice_speed, 1)
        slider_layout.addWidget(label("Fast", "muted"))
        slider_layout.addWidget(self.speed_value)
        slider_layout.addWidget(reset)

        self.voice_speed.valueChanged.connect(self._on_speed_changed)
        self._on_speed_changed(self.voice_speed.value())
        card.add_row(SettingRow("Speaking speed", "50% to 200% of normal", slider_row,
                                stacked=True))
        layout.addWidget(card)

        layout.addStretch(1)
        return body

    def _on_open_at_login(self, enabled: bool) -> None:
        if not app_support.set_login_item(enabled):
            self.open_at_login.setChecked(app_support.is_login_item_enabled())

    def _on_engine_changed(self, *_args, update: bool = True) -> None:
        """Whisper size only matters when Whisper is the engine."""
        self.speech_model_row.setEnabled(self.speech_engine.currentData() == "whisper")
        if update:
            self.settings_change()

    @staticmethod
    def _installed_voices() -> list:
        """Voices actually installed on this computer (falls back to a short list)."""
        try:
            from app.voice_handler import list_voices
            return list_voices() or FALLBACK_VOICES
        except Exception as e:
            logger.warning(f"Couldn't read installed voices: {e}")
            return FALLBACK_VOICES

    def _on_speed_changed(self, value: int) -> None:
        self.speed_value.setText(f"{value / 100:.2f}×")
        self.settings_change()

    # ----------------------------------------------------------------- behavior

    def settings_change(self) -> None:
        """Save all settings changes to the configuration file.

        Called whenever any setting widget changes (text field, slider, toggle,
        or dropdown). Reads all current widget values and saves them to the
        configuration through the ConfigManager, so settings survive restarts.
        """
        if self._loading:
            return
        try:
            # Save hotkey settings
            self.config.set("hotkeys", "start", self.start_hotkey.raw_text())
            self.config.set("hotkeys", "stop", self.stop_hotkey.raw_text())

            # Save API settings
            self.config.set("api", "provider", self._provider_value())
            self.config.set("api", "model", self._model_value())
            self.config.set("api", "api_key", self.api_key.text())

            # Save voice settings (convert slider 50-200 to 0.5-2.0 multiplier)
            self.config.set("voice", "speed", self.voice_speed.value() / 100)
            voice = "" if self.voice_name.currentIndex() == 0 else self.voice_name.currentText()
            self.config.set("voice", "voice_name", voice)

            # Save speech recognition settings
            self.config.set("speech", "engine", self.speech_engine.currentData())
            self.config.set("speech", "model", self.speech_model.currentData())

            # Save response mode settings
            self.config.set("response_mode", "voice", self.response_voice.isChecked())
            self.config.set("response_mode", "popup", self.response_popup.isChecked())

            logger.debug("Settings updated and saved to configuration")

        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)

    def hideEvent(self, event) -> None:
        """Stop any half-finished shortcut recording when the window closes."""
        self.start_hotkey.cancel()
        self.stop_hotkey.cancel()
        super().hideEvent(event)

    def clear_chat_history(self) -> None:
        """Clear the AI conversation history and reset context.

        Resets the conversation history in the AIHandler so the next response
        won't reference past interactions, and briefly confirms it in the UI.
        """
        try:
            self.ai_handler.clear_history()
            logger.info("User cleared chat history from settings panel")
            self.history_status.setProperty("role", "success")
            self.history_status.setText("✓ Cleared")
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}", exc_info=True)
            self.history_status.setProperty("role", "rowHint")
            self.history_status.setText("Couldn't clear")
        self.history_status.style().polish(self.history_status)
        QTimer.singleShot(2500, lambda: self.history_status.setText(""))
