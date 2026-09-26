"""Voice Handler: Text-to-speech synthesis and audio output.

This module provides text-to-speech functionality for the Talk-To-AI application,
allowing AI responses to be spoken aloud to the user. Uses the pyttsx3 library
which provides cross-platform TTS support (works on macOS, Windows, Linux).

Voice output respects user configuration settings (voice name, speed) and can
be disabled via the response_mode.voice setting. Handles voice synthesis errors
gracefully with informative logging.

Author: Allen Wu
Version: 1.0.0
"""

import logging
from typing import Optional, List
import pyttsx3

logger = logging.getLogger(__name__)

# Text-to-speech configuration constants
DEFAULT_SPEECH_RATE: int = 150  # Words per minute base rate
SPEECH_RATE_MIN: int = 75  # Minimum WPM (speed slider minimum 50% = 75 WPM)
SPEECH_RATE_MAX: int = 300  # Maximum WPM (speed slider maximum 200% = 300 WPM)

# Default voice configuration
DEFAULT_VOICE_NAME: str = "Alex"


class VoiceHandler:
    """Handles text-to-speech synthesis and audio playback.
    
    This class provides a simple interface for converting text to speech and
    playing it through the system audio output. It uses pyttsx3, a Python
    text-to-speech library that works on macOS, Windows, and Linux.
    
    Voice output is configurable through the ConfigManager:
    - voice.voice_name: Which voice to use (e.g., "Alex", "Victoria")
    - voice.speed: Speech speed multiplier (0.5 = 50%, 1.0 = 100%, 2.0 = 200%)
    - response_mode.voice: Enable/disable voice responses
    
    Voice Synthesis Process:
    1. Check if voice response is enabled in settings
    2. Load voice name and speed from configuration
    3. Find matching system voice by name
    4. Set voice and speech rate on pyttsx3 engine
    5. Synthesize and play audio through system speakers
    
    Available Voices (macOS):
        - Alex (default male voice)
        - Victoria (female voice)
        - Moira (female voice with Irish accent)
        - Fiona (female voice)
        Note: Available voices vary by OS. Windows has different voices.
    
    Attributes:
        config (ConfigManager): Configuration manager for voice settings
        engine (pyttsx3.Engine): pyttsx3 text-to-speech engine instance
        
    Features:
    - Cross-platform support (macOS, Windows, Linux)
    - Configurable voice selection
    - Configurable speech rate (50-200%)
    - Can be disabled via settings
    - Graceful error handling with logging
    
    Example:
        >>> from app.config import ConfigManager
        >>> config = ConfigManager()
        >>> voice = VoiceHandler(config)
        >>> voice.speak("Hello, world!")
        >>> # Audio plays at configured voice and speed
        
    Technical Details:
        Speech rate is converted from a multiplier (0.5-2.0) to words per minute:
        - 0.5x speed: 75 WPM (minimum)
        - 1.0x speed: 150 WPM (default)
        - 2.0x speed: 300 WPM (maximum)
        
    Note:
        - Blocks while speaking. Audio plays synchronously.
        - All errors are logged but not raised (graceful degradation)
        - Voice availability depends on OS and installed voices
    """

    def __init__(self, config) -> None:
        """Initialize the text-to-speech engine with configuration.
        
        Creates a pyttsx3 TTS engine instance and loads voice configuration
        from the ConfigManager. The engine is ready to use immediately after
        initialization.
        
        Args:
            config: ConfigManager instance providing voice settings
                (voice.voice_name, voice.speed, response_mode.voice)
            
        Side Effects:
            - Initializes pyttsx3 engine (may start background processes)
            - Loads system voices list
            - Logs initialization message
            
        Raises:
            RuntimeError: If pyttsx3 cannot initialize (rare, indicates
                system TTS subsystem issue)
                
        Note:
            Engine initialization is usually fast, but on some systems it may
            take a moment as it initializes the underlying TTS subsystem.
        """
        try:
            self.config = config
            self.engine: pyttsx3.Engine = pyttsx3.init()
            logger.info("Voice handler initialized with pyttsx3 TTS engine")
        except Exception as e:
            logger.error(f"Failed to initialize text-to-speech engine: {e}", exc_info=True)
            raise

    def speak(self, text: str) -> None:
        """Synthesize and play text as speech through system audio.
        
        Converts the provided text to speech using the configured voice and
        speech rate, then plays it through the system audio output. Respects
        the user's voice response setting - does nothing if voice output is
        disabled.
        
        This method blocks until the audio finishes playing (synchronous).
        Speech rate is applied as a multiplier of the base rate.
        
        Args:
            text (str): The text to synthesize and speak aloud. Can be any
                length, but longer text will take longer to synthesize and play.
                
        Side Effects:
            - Synthesizes audio (CPU usage spike)
            - Plays audio through system speakers
            - Blocks until audio finishes playing
            - Logs debug and error messages
            
        Raises:
            Does not raise exceptions. All errors are logged and the method
            returns gracefully.
            
        Configuration Used:
            - voice.voice_name: Name of voice to use (e.g., "Alex")
            - voice.speed: Speech rate multiplier (0.5-2.0)
            - response_mode.voice: Whether voice output is enabled
            
        Example:
            >>> voice_handler.speak("The weather today is sunny.")
            >>> # Audio plays at configured voice and speed
            >>> # Method blocks until audio finishes
            
        Note:
            - Blocks synchronously (audio plays before method returns)
            - Very long text may take significant time to synthesize
            - Voice availability depends on operating system
        """
        try:
            # Check if voice response is enabled in configuration
            if not self.config.get("response_mode", "voice"):
                logger.debug("Voice response disabled in settings, skipping synthesis")
                return

            # Load voice settings from configuration
            voice_name: Optional[str] = self.config.get("voice", "voice_name")
            speed: Optional[float] = self.config.get("voice", "speed")
            
            # Use defaults if not configured
            if not voice_name:
                voice_name = DEFAULT_VOICE_NAME
            if not speed:
                speed = 1.0

            logger.debug(f"Synthesizing speech: voice={voice_name}, speed={speed}x")

            # Find and set the requested voice
            voices: List = self.engine.getProperty("voices")
            voice_id: Optional[str] = self._find_voice_id(voice_name, voices)
            if voice_id:
                self.engine.setProperty("voice", voice_id)

            # Convert speed multiplier (0.5-2.0) to words per minute
            # Base rate is 150 WPM, so 1.0x speed = 150 WPM
            speech_rate: int = int(speed * DEFAULT_SPEECH_RATE)
            speech_rate = max(SPEECH_RATE_MIN, min(SPEECH_RATE_MAX, speech_rate))
            self.engine.setProperty("rate", speech_rate)
            
            logger.debug(f"Speech rate set to {speech_rate} WPM")

            # Synthesize and play audio (blocks until complete)
            self.engine.say(text)
            self.engine.runAndWait()

            logger.info(f"Spoke: {text[:50]}..." if len(text) > 50 else f"Spoke: {text}")

        except Exception as e:
            logger.error(f"Error during text-to-speech synthesis: {e}", exc_info=True)

    def _find_voice_id(self, voice_name: str, voices: List) -> Optional[str]:
        """Find the voice ID matching the requested voice name.
        
        Searches the available system voices for a voice matching the requested
        name. Uses case-insensitive substring matching to be flexible with
        voice names (e.g., "alex" matches "Alex", "Alex (Enhanced)", etc.).
        
        Args:
            voice_name (str): Requested voice name (e.g., "Alex", "Victoria")
            voices (List): List of available voice objects from pyttsx3
            
        Returns:
            Optional[str]: The voice ID if a match is found, None if no matching
                voice is available. Returns None gracefully rather than raising.
                
        Side Effects:
            - Logs debug message if voice found
            - Logs warning if voice not found
            
        Raises:
            Does not raise exceptions. Returns None if voice not found.
            
        Voice Matching:
            Uses case-insensitive substring matching. For example:
            - "alex" matches "Alex"
            - "victoria" matches "Victoria"
            - "moira" matches "Moira (Enhanced)"
            
        Example:
            >>> voices = engine.getProperty('voices')
            >>> voice_id = handler._find_voice_id("Alex", voices)
            >>> if voice_id:
            ...     engine.setProperty('voice', voice_id)
            
        Note:
            Available voices depend on the operating system:
            - macOS: Alex, Victoria, Moira, Fiona, etc.
            - Windows: David, Zira, Mark (and others from installed TTS engines)
            - Linux: Depends on installed espeak or other TTS backends
        """
        try:
            for voice in voices:
                # Case-insensitive substring matching for flexibility
                if voice_name.lower() in voice.name.lower():
                    logger.debug(f"Found matching voice: '{voice.name}'")
                    return voice.id
            
            # No matching voice found
            logger.warning(
                f"Requested voice '{voice_name}' not found. Available voices: "
                f"{[v.name for v in voices]}"
            )
            return None
            
        except Exception as e:
            logger.error(f"Error finding voice: {e}", exc_info=True)
            return None