"""Talk-To-AI: Main application entry point.

This module initializes and orchestrates all components of the Talk-To-AI application,
including configuration management, audio handling, AI integration, and UI management.
It serves as the central controller that coordinates between the hotkey listener,
audio handler, AI provider, and user interface.

Author: Allen Wu
Version: 1.0.0
"""

import sys
import logging
import threading
from typing import Optional
from PyQt6.QtWidgets import QApplication

from app.config import ConfigManager
from app.menu_bar import MenuBar
from app.hotkey_listener import HotkeyListener
from app.audio_handler import AudioHandler
from app.ai_handler import AIHandler
from app.voice_handler import VoiceHandler
from app.response_display import ResponseDisplay
from app.settings_panel import SettingsPanel
from app.theme import apply_theme

logger = logging.getLogger(__name__)


class VoiceAssistant:
    """Main application controller for the Talk-To-AI voice assistant.
    
    This class manages the lifecycle of all application components and coordinates
    their interactions. It handles the flow from hotkey detection through audio
    recording, transcription, AI processing, and voice response.
    
    Attributes:
        config (ConfigManager): Manages application configuration and settings
        audio_handler (AudioHandler): Handles audio recording and transcription
        ai_handler (AIHandler): Routes prompts to selected AI provider
        voice_handler (VoiceHandler): Handles text-to-speech synthesis
        response_display (ResponseDisplay): Displays AI responses in UI
        menu_bar (MenuBar): Menu bar icon and UI controller
        hotkey_listener (HotkeyListener): Detects global keyboard shortcuts
        settings_panel (SettingsPanel): Settings configuration interface
    """

    def __init__(self) -> None:
        """Initialize all application components and establish their relationships.
        
        Sets up configuration management, audio handling, AI routing, voice synthesis,
        UI components, and links them together for coordinated operation.
        
        Raises:
            Exception: If any component fails to initialize (logs and propagates)
        """
        try:
            # Initialize core managers
            self.config: ConfigManager = ConfigManager()
            self.audio_handler: AudioHandler = AudioHandler(self.config)
            self.ai_handler: AIHandler = AIHandler(self.config)
            self.voice_handler: VoiceHandler = VoiceHandler(self.config)
            self.response_display: ResponseDisplay = ResponseDisplay(self.config)
            
            # Initialize UI components with cross-references
            self.menu_bar: MenuBar = MenuBar(self.config, None, self.ai_handler)
            self.hotkey_listener: Optional[HotkeyListener] = None
            
            # Create settings panel and attach to menu bar
            self.settings_panel: SettingsPanel = SettingsPanel(
                self.config, 
                None, 
                self.ai_handler
            )
            self.menu_bar.settings_panel = self.settings_panel

            # State shared between the hotkey thread and answer workers
            self._state_lock = threading.Lock()
            self._recording: bool = False
            self._question_id: int = 0

            # Stopping speech from the UI, and showing when it's talking
            self.response_display.on_stop_speaking = self.stop_speaking
            self.menu_bar.on_stop_speaking = self.stop_speaking
            self.voice_handler.on_state_change = self._on_speaking_changed

            # Load the speech model now so the first question isn't slow
            self.audio_handler.preload()
            
            logger.debug("VoiceAssistant initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VoiceAssistant: {e}")
            raise

    # The hotkey callbacks below run on the hotkey listener's thread. They
    # return right away and hand slow work (transcribing, asking the AI,
    # speaking) to a worker thread, so hotkeys keep working while it talks.

    def on_recording_started(self) -> None:
        """Start hotkey: stop any answer in progress and start listening.

        Pressing it while the assistant is talking (or still thinking) cuts the
        old answer off; only the new question will be answered.
        """
        with self._state_lock:
            if self._recording:
                return
            self._recording = True
            self._question_id += 1  # anything still working on an older question is now stale
        self.voice_handler.stop()
        self.menu_bar.change_icon("unmuted_microphone.png")
        self.audio_handler.start_recording()
        logger.debug("Recording started via hotkey")

    def on_recording_stopped(self) -> None:
        """Stop hotkey: send the recording, or, if not recording, stop talking."""
        with self._state_lock:
            if not self._recording:
                stop_speaking = True
            else:
                stop_speaking = False
                self._recording = False
                question_id = self._question_id
        if stop_speaking:
            self.stop_speaking()
            return
        threading.Thread(target=self._answer, args=(question_id,), daemon=True).start()

    def _on_speaking_changed(self, speaking: bool) -> None:
        """Called from the speaking thread; both targets hop to the UI thread."""
        self.response_display.set_speaking_async(speaking)
        self.menu_bar.set_speaking(speaking)

    def stop_speaking(self) -> None:
        """Stop the spoken answer now (Stop button, stop hotkey, Done)."""
        self.voice_handler.stop()

    def _is_current(self, question_id: int) -> bool:
        return question_id == self._question_id

    def _answer(self, question_id: int) -> None:
        """Worker thread: transcribe → ask the AI → show and speak the answer.

        Pipeline:
            1. Stop recording and transcribe (Whisper on this computer by default)
            2. Show the question with "Thinking…" (if the popup is enabled)
            3. Send it to the selected AI provider
            4. Show the answer, then speak it (if enabled)
        Each step checks the question is still the latest one; if a new
        question was started meanwhile, this one quietly gives up.
        """
        try:
            text, error = self.audio_handler.stop_and_transcribe()
            self.menu_bar.change_icon("muted_microphone.png")
            if not self._is_current(question_id):
                return
            if not text:
                # Nothing usable was heard: tell the user instead of asking the AI
                self.response_display.request_response(error)
                return
            logger.info(f"Audio transcribed: {text[:50]}...")

            self.response_display.request_thinking(text)
            try:
                ai_response: str = self.ai_handler.send_prompt(text)
            except Exception as e:
                if self._is_current(question_id):
                    self.response_display.request_response(self._ai_error_message(e), text)
                return
            logger.info(f"AI response received: {ai_response[:50]}...")
            if not self._is_current(question_id):
                return

            # Show first, so the text is on screen while it's being spoken
            self.response_display.request_response(ai_response, text)
            self.voice_handler.speak(ai_response)
        except Exception as e:
            logger.error(f"Error processing recording: {e}", exc_info=True)
            self.menu_bar.change_icon("muted_microphone.png")

    def _ai_error_message(self, error: Exception) -> str:
        """Turn an AI failure into a short message the user can act on."""
        if isinstance(error, ValueError) and "API key" in str(error):
            return "Add your API key in **Settings → AI Model** to get answers."
        if isinstance(error, ValueError) and "Model" in str(error):
            return "Choose a model in **Settings → AI Model** to get answers."
        provider = self.config.get("api", "provider") or "the AI provider"
        return (f"Couldn't get an answer from {provider}. Check your internet "
                f"connection, API key and model name.\n\n`{str(error)[:200]}`")

    def run(self, app: QApplication) -> None:
        """Start the application and event loops.
        
        Initializes the global hotkey listener, attaches it to UI components,
        and starts the Qt event loop. This method blocks until the application
        is closed.
        
        Args:
            app (QApplication): The Qt application instance to run
            
        Raises:
            SystemExit: Exits with app.exec() return code
        """
        try:
            # Initialize hotkey listener with registered callbacks
            self.hotkey_listener = HotkeyListener(
                self.config,
                on_start=self.on_recording_started,
                on_stop=self.on_recording_stopped,
            )
            self.hotkey_listener.start()
            logger.debug("Hotkey listener started")

            # Attach hotkey listener to UI components for access
            self.menu_bar.hotkey_listener = self.hotkey_listener
            self.settings_panel.hotkey_listener = self.hotkey_listener

            logger.info("Talk-To-AI application started")
            
            # Start Qt event loop (blocks until app closes)
            sys.exit(app.exec())
            
        except Exception as e:
            logger.error(f"Error running application: {e}", exc_info=True)
            raise


def main() -> None:
    """Initialize and run the Talk-To-AI application.
    
    Entry point that creates the Qt application instance and VoiceAssistant
    controller, then starts the application event loop.
    
    Raises:
        Exception: Any uncaught exceptions during initialization or runtime
    """
    try:
        app: QApplication = QApplication(sys.argv)
        app.setApplicationName("Talk-To-AI")
        app.setQuitOnLastWindowClosed(False)  # menu bar app: keep running with no windows
        apply_theme(app)
        assistant: VoiceAssistant = VoiceAssistant()
        assistant.run(app)
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()