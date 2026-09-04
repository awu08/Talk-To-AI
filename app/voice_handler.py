"""Synthesizes and plays voice responses using pyttsx3 with configurable voice and speed settings."""

import logging
import pyttsx3

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles text-to-speech audio output."""

    def __init__(self, config):
        """Initialize the voice handler."""
        self.config = config
        self.engine = pyttsx3.init()
        logger.debug("Voice handler initialized")

    def speak(self, text):
        """Synthesize and speak the given text."""
        # Check if voice response is enabled
        if not self.config.get("response_mode", "voice"):
            logger.debug("Voice response disabled, skipping")
            return

        try:
            # Get voice settings from config
            voice_name = self.config.get("voice", "voice_name")
            speed = self.config.get("voice", "speed")

            # Set voice
            voices = self.engine.getProperty("voices")
            voice_id = self._find_voice_id(voice_name, voices)
            if voice_id:
                self.engine.setProperty("voice", voice_id)

            # Set speed (convert to words per minute)
            self.engine.setProperty("rate", int(speed * 150))

            # Speak
            self.engine.say(text)
            self.engine.runAndWait()

            logger.debug(f"Speaking: {text[:50]}...")

        except Exception as e:
            logger.error(f"Voice synthesis error: {e}")

    def _find_voice_id(self, voice_name, voices):
        """Find voice ID by name."""
        for voice in voices:
            if voice_name.lower() in voice.name.lower():
                logger.debug(f"Found voice: {voice.name}")
                return voice.id
        
        logger.warning(f"Voice '{voice_name}' not found, using default")
        return None