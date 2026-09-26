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
            self.audio_handler: AudioHandler = AudioHandler()
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
            
            logger.debug("VoiceAssistant initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize VoiceAssistant: {e}")
            raise

    def on_recording_started(self) -> None:
        """Handle hotkey press to start recording.
        
        Called when the user presses the start hotkey. Changes the menu bar icon
        to indicate recording is active and begins capturing audio.
        
        Side Effects:
            - Changes menu bar icon to unmuted state
            - Starts audio recording in background thread
        """
        logger.debug("Recording started via hotkey")
        self.menu_bar.change_icon("unmuted_microphone.png")
        self.audio_handler.start_recording()

    def on_recording_stopped(self) -> None:
        """Handle hotkey release to process the recording.
        
        Called when the user presses the stop hotkey. Orchestrates the complete
        pipeline: transcription → AI processing → voice response. Handles errors
        gracefully and always resets the menu bar icon.
        
        Pipeline:
            1. Stop recording and transcribe audio
            2. Send transcribed text to selected AI provider
            3. Speak the AI response (if enabled)
            4. Display response popup (if enabled)
            5. Reset menu bar icon
            
        Side Effects:
            - Stops audio recording
            - Sends request to AI API
            - Plays audio response
            - Resets menu bar icon (always in finally block)
        """
        try:
            # Step 1: Capture and transcribe audio
            transcribed_text: str = self.audio_handler.stop_recording()
            logger.info(f"Audio transcribed: {transcribed_text[:50]}...")

            # Step 2: Send to AI provider and get response
            ai_response: str = self.ai_handler.send_prompt(transcribed_text)
            logger.info(f"AI response received: {ai_response[:50]}...")

            # Step 3: Speak the response (respects voice settings)
            self.voice_handler.speak(ai_response)

            # Step 4: Display response (respects popup settings)
            # TODO: Implement on main thread to avoid threading issues
            # self.response_display.show_response(ai_response)

        except Exception as e:
            logger.error(f"Error processing recording: {e}", exc_info=True)
        finally:
            # Always reset menu bar icon regardless of success/failure
            self.menu_bar.change_icon("muted_microphone.png")

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
        assistant: VoiceAssistant = VoiceAssistant()
        assistant.run(app)
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()