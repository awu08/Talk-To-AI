"""Response Display: Floating panel for showing AI responses.

Shows the AI's answer in a dark, rounded panel near the top-right corner of
the screen, under the menu bar. The panel shows what you asked, renders the
answer (including Markdown such as lists and code), and offers Copy and Done.

The panel only appears when response_mode.popup is enabled in settings, so
users can still choose voice-only output.

`request_response()` is safe to call from any thread: it hands the text to
the Qt main thread through a signal before touching any widgets.

Author: Allen Wu
Version: 1.1.0
"""

import logging

from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout,
)

from app.theme import COLORS, MONO_FAMILIES, icon, icon_pixmap
from app.widgets import RoundedPanel, label

logger = logging.getLogger(__name__)

# Window sizing constants
DEFAULT_WINDOW_WIDTH: int = 420
MAX_BODY_HEIGHT: int = 420
MIN_BODY_HEIGHT: int = 40
SCREEN_MARGIN: int = 14

# Styles applied inside the rendered Markdown answer
ANSWER_CSS: str = f"""
    body {{ color: {COLORS['text']}; font-size: 14px; }}
    p, li {{ line-height: 150%; }}
    a {{ color: {COLORS['accent_hover']}; text-decoration: none; }}
    code {{ font-family: '{MONO_FAMILIES[0]}'; font-size: 12.5px; background-color: {COLORS['field']}; }}
    pre {{ font-family: '{MONO_FAMILIES[0]}'; font-size: 12.5px; background-color: {COLORS['card']}; }}
    h1, h2, h3 {{ font-weight: 600; }}
"""


class ResponseDisplay(RoundedPanel):
    """Floating panel that displays AI responses.

    Attributes:
        config (ConfigManager): Configuration manager for checking popup setting
        response_label (QTextBrowser): Read-only view showing the AI response
        question_label (QLabel): Shows the transcribed question, when provided

    Example:
        >>> display = ResponseDisplay(config)
        >>> display.show_response("The answer is 42.", question="What is the answer?")
        >>> # From a background thread, use:
        >>> display.request_response("The answer is 42.")
    """

    # (response text, question text) — emitted from any thread
    response_ready = pyqtSignal(str, str)
    # (question text) — show the question with "Thinking…" while the AI works
    thinking_ready = pyqtSignal(str)
    # True while the answer is being spoken — emitted from any thread
    speaking_changed = pyqtSignal(bool)
    # (answer so far, question text) — streaming updates, emitted from any thread
    partial_ready = pyqtSignal(str, str)

    def __init__(self, config) -> None:
        """Build the panel. It stays hidden until a response is shown.

        Args:
            config: ConfigManager instance providing response_mode settings
        """
        super().__init__(Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.config = config
        self._drag_offset = None
        self.setWindowTitle("Talk-To-AI Response")
        # macOS hides tool windows when you click another app; keep this one visible
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        self.setFixedWidth(DEFAULT_WINDOW_WIDTH)
        self.response_ready.connect(self.show_response)
        self.thinking_ready.connect(self.show_thinking)
        self.partial_ready.connect(self.show_partial)
        self.speaking_changed.connect(self._set_speaking)
        # Set by the app: called to stop the spoken answer
        self.on_stop_speaking = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 12, 14)
        layout.setSpacing(10)

        # ---- Header: badge, name, provider, close
        header = QHBoxLayout()
        header.setSpacing(9)
        badge = QLabel()
        badge.setPixmap(icon_pixmap("sparkles", "#ffffff", 14))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(24, 24)
        badge.setStyleSheet(f"background: {COLORS['accent']}; border-radius: 7px;")
        header.addWidget(badge)
        header.addWidget(label("Talk-To-AI", "rowTitle"))
        self.provider_chip = label("", "chip")
        header.addWidget(self.provider_chip)
        header.addStretch(1)
        close_button = QPushButton()
        close_button.setProperty("variant", "ghost")
        close_button.setIcon(icon("close", COLORS["text_secondary"], 14))
        close_button.setIconSize(QSize(14, 14))
        close_button.setFixedSize(26, 26)
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.setToolTip("Close (Esc)")
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.dismiss)
        header.addWidget(close_button)
        layout.addLayout(header)

        # ---- The question that was asked
        self.question_label = label("", "rowHint", wrap=True)
        self.question_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; background: {COLORS['card']};"
            f"border-radius: 10px; padding: 8px 12px; font-size: 12.5px;"
        )
        self.question_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.question_label)

        # ---- The answer
        self.response_label = QTextBrowser()
        self.response_label.setOpenExternalLinks(True)
        self.response_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.response_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.response_label.document().setDefaultStyleSheet(ANSWER_CSS)
        self.response_label.document().setDocumentMargin(0)
        self.response_label.setContentsMargins(0, 0, 6, 0)
        layout.addWidget(self.response_label)

        # ---- Footer: Copy | Done
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 2, 6, 0)
        self.copy_button = QPushButton("  Copy")
        self.copy_button.setIcon(icon("copy", COLORS["text_secondary"], 14))
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self._copy)
        footer.addWidget(self.copy_button)
        self.stop_button = QPushButton("  Stop speaking")
        self.stop_button.setIcon(icon("stop", COLORS["text"], 12))
        self.stop_button.setToolTip("Stop reading the answer aloud")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_button.clicked.connect(lambda: self._stop_speaking("Stop button"))
        self.stop_button.hide()
        footer.addWidget(self.stop_button)
        footer.addStretch(1)
        done = QPushButton("Done")
        done.setProperty("variant", "primary")
        done.setMinimumWidth(80)
        done.setCursor(Qt.CursorShape.PointingHandCursor)
        done.setToolTip("Close and stop speaking (Esc)")
        done.clicked.connect(self.dismiss)
        footer.addWidget(done)
        layout.addLayout(footer)

        self._plain_text: str = ""
        logger.debug("ResponseDisplay window initialized")

    # ---------------------------------------------------------------- public

    def request_thinking(self, question: str) -> None:
        """Thread-safe: show the question with "Thinking…" while the AI works."""
        self.thinking_ready.emit(question or "")

    def set_speaking_async(self, speaking: bool) -> None:
        """Thread-safe: show or hide the Stop button."""
        self.speaking_changed.emit(speaking)

    def dismiss(self) -> None:
        """Close the window and stop any spoken answer ("I've got it")."""
        self._stop_speaking("Done")
        self.hide()

    def show_thinking(self, question: str) -> None:
        """Show the question and a "Thinking…" placeholder. Main thread only."""
        if self.config.get("response_mode", "popup") is False:
            return
        self.show_response("*Thinking…*", question)
        self.copy_button.hide()

    def request_partial(self, text: str, question: str = "") -> None:
        """Thread-safe: show the answer written so far (it keeps growing)."""
        self.partial_ready.emit(text, question or "")

    def show_partial(self, text: str, question: str = "") -> None:
        """Update the answer in place while it streams in. Main thread only.

        Unlike show_response(), this doesn't re-focus the window on every
        update, so it won't keep stealing focus while you work elsewhere.
        """
        if self.config.get("response_mode", "popup") is False:
            return
        if not self.isVisible():
            self.show_response(text, question)
            return
        self._plain_text = text
        self.response_label.setMarkdown(text)
        self._fit_height()
        scroll = self.response_label.verticalScrollBar()
        scroll.setValue(scroll.maximum())  # follow the newest text

    def request_response(self, text: str, question: str = "") -> None:
        """Thread-safe way to show a response from a background thread."""
        self.response_ready.emit(text, question or "")

    def show_response(self, text: str, question: str = "") -> None:
        """Display the AI response, if popup responses are enabled.

        Must run on the Qt main thread; use `request_response()` elsewhere.

        Args:
            text: The AI response text. Markdown is rendered.
            question: Optional transcribed question shown above the answer.
        """
        try:
            if self.config.get("response_mode", "popup") is False:
                logger.debug("Popup response disabled in settings, skipping display")
                return

            self._plain_text = text
            provider = self.config.get("api", "provider") or ""
            self.provider_chip.setText(provider)
            self.provider_chip.setVisible(bool(provider))

            self.question_label.setText(f"“{question.strip()}”" if question.strip() else "")
            self.question_label.setVisible(bool(question.strip()))

            self.response_label.setMarkdown(text)
            self.copy_button.show()
            self._fit_height()
            self._place_top_right()
            if not self.isVisible():
                # Bring it up once; later updates don't steal focus from your work
                self.show()
                self.raise_()
                self.activateWindow()
            logger.debug(f"Response displayed: {text[:50]}...")

        except Exception as e:
            logger.error(f"Error displaying response: {e}", exc_info=True)

    # --------------------------------------------------------------- helpers

    def _fit_height(self) -> None:
        """Size the answer area to its content, scrolling past MAX_BODY_HEIGHT."""
        self.layout().activate()  # settle widths before measuring text
        document = self.response_label.document()
        document.setTextWidth(self.response_label.viewport().width())
        height = int(document.size().height()) + 6
        self.response_label.setFixedHeight(max(MIN_BODY_HEIGHT, min(height, MAX_BODY_HEIGHT)))
        self.adjustSize()

    def _place_top_right(self) -> None:
        if self.isVisible():
            return  # keep wherever the user dragged it
        screen = QGuiApplication.screenAt(self.mapToGlobal(QPoint(0, 0))) \
            or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - SCREEN_MARGIN, area.top() + SCREEN_MARGIN)

    def _set_speaking(self, speaking: bool) -> None:
        self.stop_button.setVisible(speaking)

    def _stop_speaking(self, reason: str) -> None:
        if callable(self.on_stop_speaking):
            self.on_stop_speaking(reason)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._plain_text)
        self.copy_button.setText("  Copied")
        self.copy_button.setIcon(icon("check", COLORS["green"], 14))
        QTimer.singleShot(1500, self._reset_copy)

    def _reset_copy(self) -> None:
        self.copy_button.setText("  Copy")
        self.copy_button.setIcon(icon("copy", COLORS["text_secondary"], 14))

    # ----------------------------------------------------- dragging & keys

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
        else:
            super().keyPressEvent(event)
