"""Captures audio from the microphone and transcribes it to text using the Google Speech Recognition API."""

import logging
import sounddevice as sd
import numpy as np
import speech_recognition as sr
from threading import Thread

logger = logging.getLogger(__name__)


class AudioHandler:
    """Handles audio recording and speech-to-text conversion."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.is_recording = False
        self.recording_thread = None
        self.audio_data = None

    def start_recording(self):
        """Start recording audio in a background thread."""
        self.is_recording = True
        self.recording_thread = Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()

    def _record_audio(self):
        """Record audio chunks until stopped."""
        try:
            logger.debug("Recording started")
            sample_rate = 16000
            chunk_duration = 0.5  # Record in 0.5 second chunks
            chunk_size = int(chunk_duration * sample_rate)

            chunks = []

            while self.is_recording:
                audio_chunk = sd.rec(chunk_size, samplerate=sample_rate, channels=1)
                sd.wait()
                chunks.append(audio_chunk)

            self.audio_data = np.concatenate(chunks) if chunks else None
            logger.debug("Recording finished")
        except Exception as e:
            logger.error(f"Error recording audio: {e}")

    def stop_recording(self):
        """Stop recording and transcribe audio to text."""
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join()

        if self.audio_data is None:
            logger.warning("No audio data recorded")
            return "No audio recorded"

        try:
            logger.debug("Converting audio to text...")
            # Convert numpy array to int16
            audio_int16 = np.int16(self.audio_data * 32767)
            audio_bytes = audio_int16.tobytes()

            # Create AudioData for speech_recognition
            audio_data = sr.AudioData(audio_bytes, 16000, 2)

            # Use Google's free speech recognition
            text = self.recognizer.recognize_google(audio_data)
            logger.debug(f"Transcribed: {text}")
            return text
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return "Could not understand audio"
        except sr.RequestError as e:
            logger.error(f"Google API error: {e}")
            return f"Error with Google API: {e}"
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error: {e}"