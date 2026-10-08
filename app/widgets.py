"""Widgets: Reusable building blocks for the Talk-To-AI interface.

Small, styled components shared by the settings window, tray popover and
response popup: an animated toggle switch, rounded cards, labeled setting
rows, a keycap shortcut display and a frameless rounded panel.

Author: Allen Wu
Version: 1.1.0
"""

import sys
from typing import Optional

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from app.theme import COLORS, RADIUS_WINDOW, icon_pixmap


def label(text: str, role: Optional[str] = None, wrap: bool = False) -> QLabel:
    """Create a QLabel with a stylesheet role (title, section, rowHint...)."""
    widget = QLabel(text)
    if role:
        widget.setProperty("role", role)
    widget.setWordWrap(wrap)
    return widget


def icon_label(name: str, color: str = COLORS["text_secondary"], size: int = 18) -> QLabel:
    """Create a QLabel showing one of the theme's line icons."""
    widget = QLabel()
    widget.setPixmap(icon_pixmap(name, color, size))
    widget.setFixedSize(size, size)
    return widget


class ToggleSwitch(QCheckBox):
    """iOS/macOS-style on/off switch.

    Subclasses QCheckBox so the familiar `isChecked()`, `setChecked()` and
    `stateChanged` / `toggled` APIs keep working; only the painting changes.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(38, 22)
        self._offset: float = 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(140)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self) -> QSize:
        return QSize(38, 22)

    def hitButton(self, pos) -> bool:  # whole widget is clickable
        return self.contentsRect().contains(pos)

    def setChecked(self, checked: bool) -> None:  # jump without animating
        super().setChecked(checked)
        self._animation.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = pyqtProperty(float, get_offset, set_offset)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)

        off = QColor(COLORS["field_hover"])
        on = QColor(COLORS["accent"])
        t = self._offset
        track = QColor(
            int(off.red() + (on.red() - off.red()) * t),
            int(off.green() + (on.green() - off.green()) * t),
            int(off.blue() + (on.blue() - off.blue()) * t),
        )
        if not self.isEnabled():
            track.setAlpha(110)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        knob = rect.height() - 4
        x = rect.left() + 2 + (rect.width() - knob - 4) * t
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(x, rect.top() + 2, knob, knob))
        painter.end()


class Card(QFrame):
    """Rounded, bordered container that stacks rows with hairline dividers."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._rows: int = 0

    def add_row(self, widget: QWidget) -> QWidget:
        if self._rows:
            divider = QFrame()
            divider.setProperty("role", "divider")
            wrapper = QWidget()
            wrap_layout = QHBoxLayout(wrapper)
            wrap_layout.setContentsMargins(14, 0, 14, 0)
            wrap_layout.addWidget(divider)
            self._layout.addWidget(wrapper)
        self._layout.addWidget(widget)
        self._rows += 1
        return widget


class SettingRow(QWidget):
    """One line inside a card: optional icon, title + hint, control on the right."""

    def __init__(
        self,
        title: str,
        hint: str = "",
        control: Optional[QWidget] = None,
        icon_name: Optional[str] = None,
        stacked: bool = False,
    ) -> None:
        """Build the row.

        Args:
            title: Main row label.
            hint: Smaller secondary description under the title.
            control: Widget shown on the right (or below when `stacked`).
            icon_name: Optional theme icon shown to the left of the title.
            stacked: Put the control under the text, full width (for wide inputs).
        """
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 11, 14, 11)
        outer.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(12)
        if icon_name:
            top.addWidget(icon_label(icon_name), 0, Qt.AlignmentFlag.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(title, "rowTitle"))
        self._hint_text = hint
        self.hint_label = label(hint, "rowHint", wrap=True)
        self.hint_label.setVisible(bool(hint))
        text.addWidget(self.hint_label)
        top.addLayout(text, 1)

        if control is not None and not stacked:
            top.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(top)

        if control is not None and stacked:
            outer.addWidget(control)

    def set_hint(self, text: str, role: str = "rowHint") -> None:
        """Temporarily replace the hint, e.g. with an instruction or an error."""
        self.hint_label.setProperty("role", role)
        self.hint_label.setText(text)
        self.hint_label.setVisible(bool(text))
        self.hint_label.style().unpolish(self.hint_label)
        self.hint_label.style().polish(self.hint_label)

    def reset_hint(self) -> None:
        """Restore the original hint text."""
        self.set_hint(self._hint_text)


_KEY_SYMBOLS = {
    "cmd": "⌘", "command": "⌘", "option": "⌥", "alt": "⌥", "ctrl": "⌃",
    "control": "⌃", "shift": "⇧", "esc": "Esc", "escape": "Esc",
    "space": "Space", "enter": "Return", "return": "Return", "tab": "Tab",
    "up": "↑", "down": "↓", "left": "←", "right": "→", "backspace": "⌫",
    "delete": "⌦", "page_up": "Page Up", "page_down": "Page Down",
    "home": "Home", "end": "End",
}


def format_hotkey(raw: str) -> str:
    """Turn a stored shortcut like "cmd+option+space" into "⌘ ⌥ Space"."""
    if not raw:
        return "—"
    parts = [p.strip().lower() for p in raw.split("+") if p.strip()]
    return " ".join(_KEY_SYMBOLS.get(p, p.upper() if len(p) == 1 else p.title()) for p in parts)


# Qt key code -> name understood by HotkeyListener._parse_hotkey()
_QT_KEY_NAMES = {
    Qt.Key.Key_Space: "space", Qt.Key.Key_Escape: "esc", Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
    Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right", Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "page_up", Qt.Key.Key_PageDown: "page_down",
}
for _i in range(26):
    _QT_KEY_NAMES[Qt.Key(Qt.Key.Key_A.value + _i)] = chr(ord("a") + _i)
for _i in range(10):
    _QT_KEY_NAMES[Qt.Key(Qt.Key.Key_0.value + _i)] = str(_i)
for _i in range(12):
    _QT_KEY_NAMES[Qt.Key(Qt.Key.Key_F1.value + _i)] = f"f{_i + 1}"

_MODIFIER_KEYS = {Qt.Key.Key_Control, Qt.Key.Key_Meta, Qt.Key.Key_Alt,
                  Qt.Key.Key_Shift, Qt.Key.Key_AltGr}


def modifier_names(mods: Qt.KeyboardModifier) -> list:
    """Modifier names in a stable order, in the listener's vocabulary.

    On macOS Qt reports ⌘ as ControlModifier and ⌃ as MetaModifier.
    """
    mac = sys.platform == "darwin"
    names = []
    if mods & (Qt.KeyboardModifier.MetaModifier if mac else Qt.KeyboardModifier.ControlModifier):
        names.append("ctrl")
    if mods & Qt.KeyboardModifier.AltModifier:
        names.append("option")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        names.append("shift")
    if mods & (Qt.KeyboardModifier.ControlModifier if mac else Qt.KeyboardModifier.MetaModifier):
        names.append("cmd")
    return names


class KeycapField(QPushButton):
    """A shortcut shown like a physical key; click it to record a new one.

    Click → it turns blue and waits. Hold any modifiers and press a key to
    set the shortcut. Click it again (or click elsewhere) to cancel.
    `raw_text()` returns the stored form, e.g. "cmd+option+space".

    Signals:
        recording_started(): recording began (pause global hotkeys now)
        recording_finished(): recording ended, saved or not
        hotkey_recorded(str): a new shortcut was captured (raw form)
        rejected(str): a key was pressed that can't be used, with the reason
    """

    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()
    hotkey_recorded = pyqtSignal(str)
    rejected = pyqtSignal(str)

    def __init__(self, text: str = "") -> None:
        super().__init__(format_hotkey(text))
        self._raw = text
        self._recording = False
        self.setProperty("role", "keycap")
        self.setProperty("recording", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setToolTip("Click to change")
        self.clicked.connect(self._toggle)
        self._fit()

    # ---- public API
    def raw_text(self) -> str:
        """The shortcut in its stored, machine-readable form."""
        return self._raw

    def set_raw_text(self, text: str) -> None:
        self._raw = text
        self._show(format_hotkey(text))

    def is_recording(self) -> bool:
        return self._recording

    def cancel(self) -> None:
        if self._recording:
            self._stop()

    # ---- recording
    def _toggle(self) -> None:
        if self._recording:
            self._stop()
        else:
            self._recording = True
            self._set_state(True)
            self._show("Type shortcut…")
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.grabKeyboard()
            self.recording_started.emit()

    def _stop(self) -> None:
        self._recording = False
        self.releaseKeyboard()
        self._set_state(False)
        self._show(format_hotkey(self._raw))
        self.recording_finished.emit()

    def keyPressEvent(self, event) -> None:
        if not self._recording:
            super().keyPressEvent(event)
            return
        event.accept()
        mods = modifier_names(event.modifiers())
        key = Qt.Key(event.key())
        if key in _MODIFIER_KEYS:  # live preview while modifiers are held
            self._show(format_hotkey("+".join(mods)) + " …" if mods else "Type shortcut…")
            return
        name = _QT_KEY_NAMES.get(key)
        if name is None:
            self.rejected.emit("That key can't be used. Try a letter, number, F-key or Space.")
            return
        raw = "+".join(mods + [name])
        self._raw = raw
        self._stop()
        self.hotkey_recorded.emit(raw)

    def keyReleaseEvent(self, event) -> None:
        if self._recording:
            event.accept()
            mods = modifier_names(event.modifiers())
            self._show(format_hotkey("+".join(mods)) + " …" if mods else "Type shortcut…")
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event) -> None:
        self.cancel()
        super().focusOutEvent(event)

    # ---- display
    def _show(self, text: str) -> None:
        self.setText(text)
        self._fit()

    def _set_state(self, recording: bool) -> None:
        self.setProperty("recording", recording)
        self.style().unpolish(self)
        self.style().polish(self)

    def _fit(self) -> None:
        width = self.fontMetrics().horizontalAdvance(self.text() or "—") + 36
        self.setFixedWidth(max(64, width))


class RoundedPanel(QWidget):
    """Frameless, translucent top-level window painted as a rounded dark panel.

    Used by the tray popover and the response popup. Subclasses add their own
    layout; this class only paints the background, border and shadow-free edge.
    """

    def __init__(self, flags: Qt.WindowType, radius: int = RADIUS_WINDOW) -> None:
        super().__init__(None, flags | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.radius = radius

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.fillPath(path, QColor(COLORS["window"]))
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawPath(path)
        painter.end()
