"""Transcriber: Turns recorded speech into text.

Two engines are available:
    - Whisper, running locally with faster-whisper. Free, works offline and is
      much more accurate than the Google web API, especially with accents or
      background noise. The model is downloaded once on first use.
    - Google's free web speech API (the original engine), used as a backup if
      Whisper isn't installed or fails to load.

Settings used (all optional):
    speech.engine: "whisper" (default) or "google"
    speech.model:  "base.en", "small.en" (default) or "medium.en"

Author: Allen Wu
Version: 1.1.0
"""

import logging
import threading
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_ENGINE: str = "whisper"
DEFAULT_MODEL: str = "small.en"

# Shown in Settings: (label, model name, approximate download size)
WHISPER_MODELS = [
    ("Fast", "base.en", "about 150 MB"),
    ("Balanced", "small.en", "about 500 MB"),
    ("Most accurate", "medium.en", "about 1.5 GB"),
]


class TranscriptionError(Exception):
    """Raised with a short, user-facing message when speech can't be turned into text."""


class Transcriber:
    """Chooses an engine from settings and transcribes 16 kHz mono audio."""

    def __init__(self, config=None, sample_rate: int = 16000) -> None:
        self.config = config
        self.sample_rate = sample_rate
        self._model = None
        self._model_name: Optional[str] = None
        self._load_lock = threading.Lock()
        self._whisper_failed: bool = False

    # ------------------------------------------------------------ settings

    def _setting(self, key: str, default: str) -> str:
        if self.config is None:
            return default
        return self.config.get("speech", key) or default

    @property
    def engine(self) -> str:
        return self._setting("engine", DEFAULT_ENGINE)

    @property
    def model_name(self) -> str:
        return self._setting("model", DEFAULT_MODEL)

    # -------------------------------------------------------------- whisper

    def preload(self) -> None:
        """Load the Whisper model in the background so the first question is fast."""
        if self.engine == "whisper":
            threading.Thread(target=self._load_whisper, daemon=True).start()

    def _load_whisper(self):
        """Load (or reload after a settings change) the Whisper model. Thread-safe."""
        wanted = self.model_name
        with self._load_lock:
            if self._model is not None and self._model_name == wanted:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                logger.warning("faster-whisper isn't installed; using Google speech recognition. "
                               "Run: pip install -r requirements.txt")
                self._whisper_failed = True
                return None
            try:
                logger.info(f"Loading Whisper model '{wanted}' "
                            "(the first time downloads it, which can take a minute)…")
                self._model = WhisperModel(wanted, device="cpu", compute_type="int8")
                self._model_name = wanted
                self._whisper_failed = False
                logger.info(f"Whisper model '{wanted}' ready")
                return self._model
            except Exception as e:
                logger.error(f"Couldn't load Whisper model '{wanted}': {e}")
                self._whisper_failed = True
                return None

    def _transcribe_whisper(self, audio: np.ndarray) -> Optional[str]:
        """Return text, "" if nothing was said, or None if Whisper is unavailable."""
        model = self._load_whisper()
        if model is None:
            return None
        samples = audio.astype(np.float32) / 32768.0
        segments, _info = model.transcribe(
            samples,
            language="en",
            beam_size=5,
            vad_filter=True,                  # skip silence; avoids made-up words
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()

    # --------------------------------------------------------------- google

    def _transcribe_google(self, audio: np.ndarray) -> str:
        import speech_recognition as sr
        data = sr.AudioData(audio.astype(np.int16).tobytes(), self.sample_rate, 2)
        try:
            return sr.Recognizer().recognize_google(data)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.error(f"Google Speech Recognition API error: {e}")
            raise TranscriptionError(
                "Couldn't reach Google speech recognition. Check your internet connection.")

    # ---------------------------------------------------------------- public

    def transcribe(self, audio: np.ndarray) -> Tuple[str, str]:
        """Transcribe int16 mono audio.

        Returns:
            (text, engine_used). Text is "" when no words were recognized.

        Raises:
            TranscriptionError: with a message suitable for showing the user.
        """
        if self.engine == "whisper":
            try:
                text = self._transcribe_whisper(audio)
                if text is not None:
                    return text, "whisper"
            except Exception as e:
                logger.error(f"Whisper transcription failed, trying Google: {e}", exc_info=True)
        return self._transcribe_google(audio), "google"
