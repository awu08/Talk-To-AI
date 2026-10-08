"""Menu Bar: System tray icon and popover panel.

This module provides the menu bar interface for the Talk-To-AI application.
Clicking the tray icon opens a dark, rounded popover (in the style of modern
macOS menu bar utilities) showing the assistant's status, the active AI model,
quick response toggles, and Settings / Quit buttons.

The tray icon also reflects recording state by switching between the muted and
unmuted microphone images.

Author: Allen Wu
Version: 1.1.0
"""

import sys
import logging
from typing import Optional

from PyQt6.QtCore import QObject, QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSystemTrayIcon, QVBoxLayout, QWidget,
)

from app import models_catalog
from app.theme import COLORS, icon, icon_pixmap, tray_icon
from app.widgets import Card, RoundedPanel, SettingRow, ToggleSwitch, format_hotkey, label

logger = logging.getLogger(__name__)

POPOVER_WIDTH: int = 300
POPOVER_GAP: int = 6  # space between the menu bar and the popover
RECORDING_ICON: str = "unmuted_microphone.png"


def _bool_setting(value, default: bool = True) -> bool:
    return default if value is None else bool(value)


class _UiBridge(QObject):
    """Moves calls from background threads onto the Qt main thread."""

    icon_requested = pyqtSignal(str)
    speaking_requested = pyqtSignal(bool)


class StatusDot(QLabel):
    """Small colored dot showing idle (green) or listening (orange) state."""

    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(8, 8)
        self.set_color(COLORS["green"])

    def set_color(self, color: str) -> None:
        self.setStyleSheet(f"background: {color}; border-radius: 4px;")


class TrayPopover(RoundedPanel):
    """The panel that drops down from the menu bar icon."""

    def __init__(self, menu_bar: "MenuBar") -> None:
        super().__init__(Qt.WindowType.Popup)
        self.menu_bar = menu_bar
        self.config = menu_bar.config
        self.setFixedWidth(POPOVER_WIDTH)
        self._syncing: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)

        # ---- Brand header
        header = QHBoxLayout()
        header.setSpacing(10)
        badge = QLabel()
        badge.setPixmap(icon_pixmap("mic", "#ffffff", 16))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(30, 30)
        badge.setStyleSheet(f"background: {COLORS['accent']}; border-radius: 9px;")
        header.addWidget(badge)
        header.addWidget(label("Talk-To-AI", "rowTitle"), 1)
        self.provider_chip = label("", "chip")
        header.addWidget(self.provider_chip)
        layout.addLayout(header)

        # ---- Status card
        status_card = Card()
        status = QWidget()
        status_layout = QHBoxLayout(status)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(10)
        self.status_dot = StatusDot()
        status_layout.addWidget(self.status_dot)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.status_title = label("Ready", "rowTitle")
        self.status_hint = label("", "rowHint")
        text.addWidget(self.status_title)
        text.addWidget(self.status_hint)
        status_layout.addLayout(text, 1)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setIcon(icon("stop", COLORS["text"], 11))
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.clicked.connect(self._stop_speaking)
        self.stop_button.hide()
        status_layout.addWidget(self.stop_button)
        status_card.add_row(status)
        layout.addWidget(status_card)

        # ---- Response toggles
        layout.addSpacing(2)
        layout.addWidget(label("RESPONSES", "section"))
        toggles = Card()
        self.voice_toggle = ToggleSwitch()
        self.popup_toggle = ToggleSwitch()
        self.voice_toggle.toggled.connect(lambda on: self._save_toggle("voice", on))
        self.popup_toggle.toggled.connect(lambda on: self._save_toggle("popup", on))
        toggles.add_row(SettingRow("Speak answers", control=self.voice_toggle, icon_name="wave"))
        toggles.add_row(SettingRow("Show answer window", control=self.popup_toggle,
                                   icon_name="bubble"))
        layout.addWidget(toggles)

        # ---- Clear history
        clear = QPushButton("  Clear conversation")
        clear.setIcon(icon("trash", COLORS["text_secondary"], 14))
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(self._clear_history)
        self.clear_button = clear
        layout.addWidget(clear)

        # ---- Footer: Settings | Quit
        layout.addSpacing(4)
        footer = QHBoxLayout()
        footer.setSpacing(10)
        for text_, icon_name, slot in (
            ("  Settings", "gear", self._open_settings),
            ("  Quit", "power", menu_bar.quit_app),
        ):
            button = QPushButton(text_)
            button.setProperty("variant", "outline")
            button.setIcon(icon(icon_name, COLORS["text_secondary"], 15))
            button.setIconSize(QSize(15, 15))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot)
            footer.addWidget(button)
        layout.addLayout(footer)

    # ---------------------------------------------------------------- state

    def refresh(self) -> None:
        """Pull the latest settings into the popover before it opens."""
        self._syncing = True
        provider = self.config.get("api", "provider") or ""
        model = self.config.get("api", "model") or ""
        self.provider_chip.setText(provider or "No AI set")
        self.provider_chip.setToolTip(models_catalog.display_name(provider, model))
        self.voice_toggle.setChecked(_bool_setting(self.config.get("response_mode", "voice")))
        self.popup_toggle.setChecked(_bool_setting(self.config.get("response_mode", "popup")))
        self._syncing = False
        self.set_recording(self.menu_bar.is_recording)

    def set_recording(self, recording: bool) -> None:
        start = format_hotkey(self.config.get("hotkeys", "start") or "")
        stop = format_hotkey(self.config.get("hotkeys", "stop") or "")
        speaking = self.menu_bar.is_speaking and not recording
        self.stop_button.setVisible(speaking)
        if speaking:
            self.status_dot.set_color(COLORS["accent"])
            self.status_title.setText("Speaking…")
            self.status_hint.setText(f"Press {stop} to stop")
        elif recording:
            self.status_dot.set_color(COLORS["orange"])
            self.status_title.setText("Listening…")
            self.status_hint.setText(f"Press {stop} to send")
        elif not self.config.get("api", "api_key"):
            self.status_dot.set_color(COLORS["text_tertiary"])
            self.status_title.setText("Add an API key to start")
            self.status_hint.setText("Open Settings → AI Model")
        else:
            self.status_dot.set_color(COLORS["green"])
            self.status_title.setText("Ready")
            self.status_hint.setText(f"Press {start} to ask anything")

    def _stop_speaking(self) -> None:
        if callable(self.menu_bar.on_stop_speaking):
            self.menu_bar.on_stop_speaking()

    def _save_toggle(self, key: str, on: bool) -> None:
        if self._syncing:
            return
        self.config.set("response_mode", key, on)
        # Keep an open settings window in sync with the popover.
        panel = self.menu_bar.settings_panel
        if panel is not None:
            widget = panel.response_voice if key == "voice" else panel.response_popup
            if widget.isChecked() != on:
                widget.setChecked(on)

    def _clear_history(self) -> None:
        try:
            self.menu_bar.ai_handler.clear_history()
            self.clear_button.setText("  Conversation cleared")
            self.clear_button.setIcon(icon("check", COLORS["green"], 14))
        except Exception as e:
            logger.error(f"Error clearing chat history: {e}", exc_info=True)
            self.clear_button.setText("  Couldn't clear")
        QTimer.singleShot(1800, self._reset_clear_button)

    def _reset_clear_button(self) -> None:
        self.clear_button.setText("  Clear conversation")
        self.clear_button.setIcon(icon("trash", COLORS["text_secondary"], 14))

    def _open_settings(self) -> None:
        self.hide()
        self.menu_bar.show_settings()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


class MenuBar:
    """Manages the system tray icon, popover panel, and settings window.

    Attributes:
        config (ConfigManager): Configuration manager for application settings
        hotkey_listener (HotkeyListener): Hotkey listener for settings updates
        ai_handler (AIHandler): AI handler for clearing conversation history
        tray_icon (QSystemTrayIcon): System tray icon instance
        popover (TrayPopover): Panel shown when the tray icon is clicked
        settings_window (Optional[QMainWindow]): Settings window (created on demand)
        settings_panel (Optional[SettingsPanel]): Settings window instance
        is_recording (bool): Whether the microphone is currently recording

    Example:
        >>> menu_bar = MenuBar(config, hotkey_listener, ai_handler)
        >>> menu_bar.change_icon("unmuted_microphone.png")  # Show recording state
    """

    def __init__(self, config, hotkey_listener, ai_handler) -> None:
        """Initialize the tray icon and its popover."""
        self.config = config
        self.hotkey_listener = hotkey_listener
        self.ai_handler = ai_handler
        self.settings_window = None
        self.settings_panel = None
        self.is_recording: bool = False
        self.is_speaking: bool = False
        self.on_stop_speaking = None  # set by the app

        # Icon changes can come from the hotkey thread; route them to the UI thread.
        self._bridge = _UiBridge()
        self._bridge.icon_requested.connect(self._apply_icon)
        self._bridge.speaking_requested.connect(self._apply_speaking)

        self.tray_icon: QSystemTrayIcon = QSystemTrayIcon(tray_icon(recording=False))
        self.tray_icon.setToolTip("Talk-To-AI")

        self.popover = TrayPopover(self)

        self.tray_icon.activated.connect(self.on_tray_icon_clicked)
        self.tray_icon.show()
        logger.info("System tray popover initialized")

    def on_tray_icon_clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Toggle the popover when the tray icon is clicked."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.Context):
            if self.popover.isVisible():
                self.popover.hide()
            else:
                self.show_popover()

    def show_popover(self) -> None:
        """Open the popover just below the tray icon, kept on screen."""
        self.popover.refresh()
        self.popover.adjustSize()

        anchor = self.tray_icon.geometry()
        if anchor.isValid() and not anchor.isEmpty():
            point = QPoint(anchor.center().x() - self.popover.width() // 2,
                           anchor.bottom() + POPOVER_GAP)
            screen = QGuiApplication.screenAt(anchor.center())
        else:
            cursor = QCursor.pos()
            point = QPoint(cursor.x() - self.popover.width() // 2, cursor.y() + POPOVER_GAP)
            screen = QGuiApplication.screenAt(cursor)

        screen = screen or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = min(max(point.x(), area.left() + 8), area.right() - self.popover.width() - 8)
        y = min(max(point.y(), area.top() + POPOVER_GAP), area.bottom() - self.popover.height() - 8)
        self.popover.move(x, y)
        self.popover.show()
        self.popover.activateWindow()
        logger.debug("Tray popover displayed")

    def show_settings(self) -> None:
        """Open or bring to front the settings window (created once, then reused)."""
        try:
            if self.settings_panel is None:
                from app.settings_panel import SettingsPanel
                self.settings_panel = SettingsPanel(self.config, self.hotkey_listener,
                                                    self.ai_handler)
            self.settings_window = self.settings_panel
            self.settings_panel.show()
            self.settings_panel.raise_()
            self.settings_panel.activateWindow()
            logger.debug("Settings window brought to foreground")
        except Exception as e:
            logger.error(f"Error opening settings window: {e}", exc_info=True)

    def change_icon(self, icon_name: str) -> None:
        """Change the tray icon to show recording state. Safe from any thread.

        Args:
            icon_name: "unmuted_microphone.png" for recording, anything else
                (e.g. "muted_microphone.png") for idle. The names are kept for
                compatibility; the icons themselves are drawn by app.theme.
        """
        self._bridge.icon_requested.emit(icon_name)

    def _apply_icon(self, icon_name: str) -> None:
        try:
            self.is_recording = icon_name == RECORDING_ICON
            self.tray_icon.setIcon(tray_icon(self.is_recording))
            self.tray_icon.setToolTip("Talk-To-AI — listening" if self.is_recording else "Talk-To-AI")
            if self.popover.isVisible():
                self.popover.set_recording(self.is_recording)
            logger.debug(f"Tray icon changed to: {icon_name}")
        except Exception as e:
            logger.error(f"Error changing icon: {e}", exc_info=True)

    def set_speaking(self, speaking: bool) -> None:
        """Show whether an answer is being spoken. Safe from any thread."""
        self._bridge.speaking_requested.emit(speaking)

    def _apply_speaking(self, speaking: bool) -> None:
        self.is_speaking = speaking
        if self.popover.isVisible():
            self.popover.set_recording(self.is_recording)

    def quit_app(self) -> None:
        """Quit the application."""
        logger.info("Application quit initiated by user")
        sys.exit(0)
