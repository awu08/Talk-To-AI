"""Passes arguments to create the app."""

import sys
import logging
from PyQt6.QtWidgets import QApplication

from app.config import ConfigManager
from app.menu_bar import MenuBar
from app.hotkey_listener import HotkeyListener
from app.audio_handler import AudioHandler
from app.ai_handler import AIHandler
from app.voice_handler import VoiceHandler
from app.response_display import ResponseDisplay

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """Main application controller for the voice assistant."""

    def __init__(self):
        """Initialize all components and establish their relationships."""
        self.config = ConfigManager()
        self.audio_handler = AudioHandler()
        self.ai_handler = AIHandler(self.config)
        self.voice_handler = VoiceHandler(self.config)
        self.response_display = ResponseDisplay(self.config)
        self.menu_bar = MenuBar(self.config, None)
        self.hotkey_listener = None

    def on_recording_started(self):
        """Handle hotkey press to start recording."""
        logger.debug("Recording started")
        self.menu_bar.change_icon("unmuted_microphone.png")
        self.audio_handler.start_recording()

    def on_recording_stopped(self):
        """Handle hotkey release to process the recording."""
        try:
            # Capture and transcribe audio
            transcribed_text = self.audio_handler.stop_recording()
            logger.info(f"Transcribed: {transcribed_text}")

            # Get AI response
            ai_response = self.ai_handler.send_prompt(transcribed_text)
            logger.info(f"AI Response: {ai_response}")

            # Play voice response
            self.voice_handler.speak(ai_response)

            # TODO: Display response in UI on main thread
            # self.response_display.show_response(ai_response)

        except Exception as e:
            logger.error(f"Error processing recording: {e}")
        finally:
            self.menu_bar.change_icon("muted_microphone.png")

    def run(self, app):
        """Start the application and event loops."""
        # Initialize hotkey listener with callbacks
        self.hotkey_listener = HotkeyListener(
            self.config,
            on_start=self.on_recording_started,
            on_stop=self.on_recording_stopped,
        )
        self.hotkey_listener.start()

        # Attach hotkey listener to menu bar for access
        self.menu_bar.hotkey_listener = self.hotkey_listener

        logger.info("Voice Assistant started")
        sys.exit(app.exec())


def main():
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    assistant = VoiceAssistant()
    assistant.run(app)


if __name__ == "__main__":
    main()