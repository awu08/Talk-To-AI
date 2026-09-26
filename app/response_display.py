"""Response Display: Popup window for showing AI responses.

This module provides a simple popup window that displays AI responses to the user.
The window is shown on-demand when response_mode.popup is enabled in settings,
displaying the AI's text response in a readable format with word wrapping.

The response display respects user configuration settings, only showing when
explicitly enabled, allowing users to disable popup responses if they prefer
voice-only output.

Author: Allen Wu
Version: 1.0.0
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)

# Window styling constants
RESPONSE_LABEL_STYLESHEET: str = "font-size: 14px; padding: 20px; line-height: 1.5;"
DEFAULT_WINDOW_WIDTH: int = 500
DEFAULT_WINDOW_HEIGHT: int = 200
DEFAULT_WINDOW_X: int = 100
DEFAULT_WINDOW_Y: int = 100


class ResponseDisplay(QMainWindow):
    """Popup window for displaying AI responses.
    
    This class provides a simple, clean popup window that shows the text response
    from the AI provider. The window includes the response text with word wrapping
    for readability and a close button for dismissal.
    
    The display respects user configuration settings - it only shows when the
    user has enabled "Popup Response" in the settings panel. This allows users
    to choose between voice-only, popup-only, or both modes of receiving responses.
    
    Threading Considerations:
        The show_response() method may be called from the background hotkey listener
        thread. PyQt widgets must be updated from the main thread. Currently this
        is a limitation - see TODO in on_recording_stopped() in main.py.
        
    Attributes:
        config (ConfigManager): Configuration manager for checking popup response setting
        response_label (QLabel): Label widget displaying the AI response text
        
    Features:
    - Word-wrapped text for readability
    - Clean, minimal UI with close button
    - Respects user configuration settings
    - Readable default window size
    
    Example:
        >>> display = ResponseDisplay(config)
        >>> display.show_response("The answer is 42.")
        >>> # Window appears if popup mode is enabled
        
    Note:
        The window is created once and reused for multiple responses. Each call
        to show_response() updates the text and brings the window to front.
    """

    def __init__(self, config) -> None:
        """Initialize the response display window with UI elements.
        
        Creates a QMainWindow with a label for the response text and a close button.
        The window is not shown until show_response() is called. Applies styling
        for readability including font size, padding, and word wrapping.
        
        Args:
            config: ConfigManager instance providing response_mode settings
            
        Side Effects:
            - Creates QMainWindow with response label and close button
            - Sets window title and default geometry
            - Applies stylesheet for responsive label
            - Logs initialization message
            
        Raises:
            AttributeError: If config doesn't have required get() method
        """
        super().__init__()
        self.config = config

        # Set window properties
        self.setWindowTitle("Talk-To-AI Response")
        self.setGeometry(
            DEFAULT_WINDOW_X,
            DEFAULT_WINDOW_Y,
            DEFAULT_WINDOW_WIDTH,
            DEFAULT_WINDOW_HEIGHT
        )

        # Create central widget and main layout
        central_widget: QWidget = QWidget()
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create response text label with word wrapping
        self.response_label: QLabel = QLabel()
        self.response_label.setWordWrap(True)
        self.response_label.setStyleSheet(RESPONSE_LABEL_STYLESHEET)
        self.response_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.response_label)

        # Create close button
        close_button: QPushButton = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        logger.debug("ResponseDisplay window initialized")

    def show_response(self, text: str) -> None:
        """Display the AI response in the popup window.
        
        Shows the response text in the popup window if the user has enabled
        popup responses in settings (response_mode.popup = true). The response
        text is displayed with word wrapping for readability.
        
        If popup responses are disabled, this method returns silently without
        displaying anything.
        
        Args:
            text (str): The AI response text to display. Can be multi-line.
            
        Side Effects:
            - Updates response_label text
            - Shows window if popup mode is enabled
            - Logs debug message
            
        Raises:
            Does not raise exceptions. Returns silently if popup mode disabled.
            
        Example:
            >>> display.show_response("Here's the weather forecast...")
            >>> # Window appears with the response
            
        Threading Note:
            This method may be called from the background hotkey listener thread.
            PyQt widgets should only be updated from the main thread. This is a
            known limitation that should be addressed with QThread signals/slots
            or similar thread-safe mechanisms.
        """
        try:
            # Check if popup response is enabled in configuration
            if not self.config.get("response_mode", "popup"):
                logger.debug("Popup response disabled in settings, skipping display")
                return

            # Update label text with the response
            self.response_label.setText(text)
            
            # Show the window
            self.show()
            
            logger.info(f"Response displayed: {text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error displaying response: {e}", exc_info=True)