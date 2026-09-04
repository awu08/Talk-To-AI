"""Displays the AI response in a popup window when response_mode.popup is enabled."""

import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


class ResponseDisplay(QMainWindow):
    """Window for displaying AI responses."""

    def __init__(self, config):
        """
        Initialize the response display window.

        Args:
            config: ConfigManager instance
        """
        super().__init__()
        self.config = config

        self.setWindowTitle("ShortcutAI Response")
        self.setGeometry(100, 100, 500, 200)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Response text label
        self.response_label = QLabel()
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet("font-size: 14px; padding: 20px;")
        layout.addWidget(self.response_label)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        logger.debug("Response display window initialized")

    def show_response(self, text):
        """Display the AI response in the window."""
        # Check if popup response is enabled in config
        if not self.config.get("response_mode", "popup"):
            logger.debug("Popup response disabled, skipping display")
            return

        self.response_label.setText(text)
        self.show()
        logger.debug("Response displayed")