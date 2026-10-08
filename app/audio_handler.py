"""Audio Handler: Records the microphone and turns speech into text.

Recording runs on one continuous input stream in a background thread, so the
UI and hotkeys stay responsive. When recording stops, the audio is checked
(too short? silent because the mic is blocked?), quiet speech is boosted, and
the result is transcribed by app.transcriber: Whisper running on this computer
by default, with Google's web API as a backup.

Author: Allen Wu
Version: 1.1.0
"""

import logging
import threading
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd

from app.transcriber import Transcriber, TranscriptionError

logger = logging.getLogger(__name__)

# Audio recording configuration constants
SAMPLE_RATE: int = 16000  # Hz - what speech models expect
AUDIO_CHANNELS: int = 1  # mono
MAX_AUDIO_VALUE: float = 32767.0  # Maximum value for 16-bit audio
MIN_DURATION_SECONDS: float = 0.4  # shorter clips can't hold a question
SILENCE_PEAK: int = 60  # peak below this = mic blocked or muted
TARGET_PEAK: int = 16000  # quiet recordings are boosted up to this level

MIC_PERMISSION_HINT: str = ("Allow microphone access for your terminal in System Settings → "
                            "Privacy & Security → Microphone, then restart the app.")


class AudioHandler:
    """Records audio from the microphone and transcribes it.

    Attributes:
        transcriber (Transcriber): Speech-to-text engine (Whisper or Google)
        is_recording (bool): Whether the microphone is currently recording
        last_error (str): User-facing reason the most recent recording failed

    Example:
        >>> handler = AudioHandler(config)
        >>> handler.start_recording()
        >>> time.sleep(3)
        >>> text, error = handler.stop_and_transcribe()
    """

    def __init__(self, config=None) -> None:
        """Set up the recorder.

        Args:
            config: ConfigManager, used for the speech engine and Whisper model
                settings. Optional; without it Whisper "small.en" is used.
        """
        self.transcriber: Transcriber = Transcriber(config, SAMPLE_RATE)
        self.is_recording: bool = False
        self.recording_thread: Optional[threading.Thread] = None
        self.last_error: str = ""
        # Each recording gets its own buffer so a new recording can never mix
        # with one that's still being transcribed.
        self._chunks: list = []
        self._stream_error: Optional[str] = None
        logger.debug("AudioHandler initialized")

    def preload(self) -> None:
        """Load the speech model in the background so the first question is quick."""
        self.transcriber.preload()

    # ------------------------------------------------------------- recording

    def start_recording(self) -> None:
        """Start recording in a background thread. Returns immediately."""
        if self.is_recording:
            return
        self.is_recording = True
        self._chunks = []
        self._stream_error = None
        self.recording_thread = threading.Thread(
            target=self._record_audio, args=(self._chunks,), daemon=True)
        self.recording_thread.start()
        logger.info("Audio recording started")

    def _record_audio(self, chunks: list) -> None:
        """Fill `chunks` from one continuous input stream until recording stops."""
        def on_audio(indata, frames, time_info, status) -> None:
            if status:
                logger.debug(f"Audio input status: {status}")
            chunks.append(indata.copy())

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=AUDIO_CHANNELS,
                                dtype="int16", callback=on_audio):
                while self.is_recording:
                    sd.sleep(30)
        except Exception as e:
            logger.error(f"Error in recording thread: {e}", exc_info=True)
            self._stream_error = ("Couldn't open the microphone. Check that one is connected. "
                                  + MIC_PERMISSION_HINT)

    def _finish_recording(self) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """Stop the stream and return (audio, error) for this recording only."""
        self.is_recording = False
        thread, chunks = self.recording_thread, self._chunks
        if thread:
            thread.join()
        if self._stream_error:
            return None, self._stream_error
        if not chunks:
            return None, "No audio was recorded."
        return np.concatenate(chunks).reshape(-1), None

    # --------------------------------------------------------- transcription

    def stop_and_transcribe(self) -> Tuple[str, str]:
        """Stop recording and transcribe it.

        Returns:
            (text, error): text is what was said ("" if nothing usable was
            heard); error is a short, user-facing reason when text is "".
        """
        audio, error = self._finish_recording()
        if audio is None:
            return self._fail(error)

        samples = audio.astype(np.int32)
        duration: float = len(samples) / SAMPLE_RATE
        peak: int = int(np.abs(samples).max()) if len(samples) else 0
        logger.debug(f"Captured {duration:.1f}s of audio, peak level {peak}")

        if duration < MIN_DURATION_SECONDS:
            return self._fail("That was too short. Hold on a moment after you start talking.")
        if peak < SILENCE_PEAK:
            logger.warning(f"Recording was silent (peak {peak})")
            return self._fail("The microphone recorded silence. " + MIC_PERMISSION_HINT)

        # Boost quiet recordings so the recognizer has something to work with
        if peak < TARGET_PEAK:
            samples = samples * (TARGET_PEAK / peak)
        audio_int16 = np.clip(samples, -MAX_AUDIO_VALUE, MAX_AUDIO_VALUE).astype(np.int16)

        try:
            text, engine = self.transcriber.transcribe(audio_int16)
        except TranscriptionError as e:
            return self._fail(str(e))
        except Exception as e:
            logger.error(f"Unexpected transcription error: {e}", exc_info=True)
            return self._fail("Something went wrong while transcribing.")

        if not text:
            logger.warning("Speech recognition failed: audio unclear")
            return self._fail("Sorry, I didn't catch that. Try again a little closer to the mic.")
        logger.info(f"Transcribed with {engine}: {text[:50]}...")
        self.last_error = ""
        return text, ""

    def stop_recording(self) -> str:
        """Stop recording and return the text ("" on failure; see `last_error`)."""
        text, _error = self.stop_and_transcribe()
        return text

    def _fail(self, message: str) -> Tuple[str, str]:
        self.last_error = message
        logger.warning(message)
        return "", message
