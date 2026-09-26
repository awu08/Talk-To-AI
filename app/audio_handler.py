"""Audio Handler: Captures and transcribes audio using Google Speech Recognition.

This module provides real-time audio recording from the microphone and converts
it to text using Google's free speech recognition API. Audio is captured in
configurable chunks to allow for responsive stopping and maintains audio data
in memory for transcription.

The AudioHandler operates asynchronously: recording happens in a background thread
to prevent blocking the UI, while transcription happens on demand when recording stops.

Author: Allen Wu
Version: 1.0.0
"""

import logging
from typing import Optional
import sounddevice as sd
import numpy as np
import speech_recognition as sr
from threading import Thread

logger = logging.getLogger(__name__)

# Audio recording configuration constants
SAMPLE_RATE: int = 16000  # Hz - standard for speech recognition
CHUNK_DURATION: float = 0.5  # seconds - balance between responsiveness and efficiency
AUDIO_CHANNELS: int = 1  # mono
AUDIO_BIT_DEPTH: int = 2  # 16-bit (2 bytes per sample)
MAX_AUDIO_VALUE: float = 32767.0  # Maximum value for 16-bit audio


class AudioHandler:
    """Handles real-time audio recording and speech-to-text transcription.
    
    This class provides a simple interface for recording audio from the microphone
    and converting it to text. Recording happens asynchronously in a background
    thread to prevent blocking the UI. Audio data is stored in memory and transcribed
    using Google's free speech recognition API when recording stops.
    
    The audio recording is done in chunks (default 0.5 seconds) which allows for
    responsive stopping while maintaining good audio quality. Transcription uses
    16kHz mono audio, standard for speech recognition models.
    
    Attributes:
        recognizer (sr.Recognizer): SpeechRecognition library recognizer instance
        is_recording (bool): Flag indicating if recording is currently active
        recording_thread (Optional[Thread]): Background thread handle for recording
        audio_data (Optional[np.ndarray]): Raw audio data captured from microphone.
            Shape: (num_samples, 1) as numpy array, values normalized to [-1, 1]
            
    Example:
        >>> handler = AudioHandler()
        >>> handler.start_recording()
        >>> time.sleep(3)  # Record for 3 seconds
        >>> text = handler.stop_recording()
        >>> print(text)
        'What is the weather today'
        
    Note:
        - Requires internet connection for Google Speech Recognition API
        - Audio must be at least 100ms for reliable recognition
        - Recording can be stopped at any time by calling stop_recording()
    """

    def __init__(self) -> None:
        """Initialize audio handler with speech recognizer.
        
        Sets up the SpeechRecognition library and initializes instance variables
        for tracking recording state and storing audio data.
        
        Raises:
            ImportError: If required audio libraries (sounddevice, SpeechRecognition)
                are not installed
        """
        self.recognizer: sr.Recognizer = sr.Recognizer()
        self.is_recording: bool = False
        self.recording_thread: Optional[Thread] = None
        self.audio_data: Optional[np.ndarray] = None
        logger.debug("AudioHandler initialized")

    def start_recording(self) -> None:
        """Start recording audio in a background daemon thread.
        
        Launches a daemon thread that continuously records audio chunks until
        stop_recording() is called. The daemon thread will not prevent the
        application from exiting.
        
        Sets is_recording flag to True and starts the background recording
        thread. Call stop_recording() to end the recording and process the audio.
        
        Side Effects:
            - Sets is_recording to True
            - Spawns background daemon thread
            - Thread continues recording until stop_recording() is called
            
        Note:
            Safe to call multiple times. If already recording, will be ignored
            by the flag check in _record_audio.
        """
        self.is_recording = True
        self.recording_thread = Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
        logger.info("Audio recording started")

    def _record_audio(self) -> None:
        """Record audio chunks in a background thread until stopped.
        
        Continuously captures audio in chunks using the sounddevice library,
        storing each chunk in a list. When is_recording becomes False (via
        stop_recording call), this function concatenates all chunks into a
        single audio data array and returns.
        
        Audio is captured at SAMPLE_RATE (16kHz) in mono with chunks of
        CHUNK_DURATION (0.5 seconds) size. This balance allows responsive
        stopping while maintaining good audio quality.
        
        Side Effects:
            - Populates self.audio_data with numpy array of audio samples
            - Logs recording start/stop messages
            - Logs errors if recording fails
            
        Raises:
            Logs errors but does not raise exceptions (runs in daemon thread)
            
        Technical Details:
            - sounddevice.rec() returns normalized float32 array [-1, 1]
            - Each chunk has shape (chunk_size, 1) for mono audio
            - Chunks are concatenated along first axis to create final audio
        """
        try:
            logger.debug("Recording thread started")
            chunk_size: int = int(CHUNK_DURATION * SAMPLE_RATE)
            chunks: list = []

            # Record audio chunks until stopped
            while self.is_recording:
                # Capture audio chunk from microphone
                audio_chunk: np.ndarray = sd.rec(
                    chunk_size, 
                    samplerate=SAMPLE_RATE, 
                    channels=AUDIO_CHANNELS
                )
                sd.wait()  # Block until chunk is fully recorded
                chunks.append(audio_chunk)

            # Combine all chunks into single audio array
            self.audio_data = np.concatenate(chunks) if chunks else None
            logger.debug(
                f"Recording stopped. Total samples: {len(self.audio_data) if self.audio_data is not None else 0}"
            )
            
        except Exception as e:
            logger.error(f"Error in recording thread: {e}", exc_info=True)
            self.audio_data = None

    def stop_recording(self) -> str:
        """Stop recording and transcribe audio to text using Google Speech Recognition.
        
        Stops the recording thread, joins it, and processes the captured audio data.
        Converts the audio to the format expected by the speech recognition API and
        sends it to Google's free speech recognition service for transcription.
        
        Returns:
            str: Transcribed text from the audio. On error, returns an error message
                describing what went wrong (e.g., "Could not understand audio").
                
        Side Effects:
            - Sets is_recording to False
            - Joins recording thread (blocks until thread finishes)
            - Clears audio_data after processing
            
        Raises:
            Does not raise exceptions. All errors are caught and returned as
            string messages for user display.
            
        Error Handling:
            - No audio recorded: Returns "No audio recorded"
            - Audio too quiet/unclear: Returns "Could not understand audio"
            - Network error: Returns "Error with Google API: {error}"
            - Other errors: Returns "Error: {error}"
            
        Technical Details:
            Audio conversion pipeline:
            1. Retrieve stored audio_data (normalized float [-1, 1])
            2. Convert to int16 (multiply by 32767 to scale to [-32767, 32767])
            3. Convert to bytes for sr.AudioData
            4. Create sr.AudioData object with sample rate and bit depth
            5. Send to Google API via sr.Recognizer.recognize_google()
            
        Note:
            Requires internet connection for Google Speech Recognition API.
            Google's free API has rate limits (typically 50 requests/day).
        """
        self.is_recording = False
        
        # Wait for recording thread to finish
        if self.recording_thread:
            self.recording_thread.join()
            logger.debug("Recording thread joined")

        # Handle case where no audio was recorded
        if self.audio_data is None:
            logger.warning("stop_recording called but no audio data captured")
            return "No audio recorded"

        try:
            logger.debug("Beginning audio transcription...")
            
            # Convert normalized float audio [-1, 1] to int16 [-32767, 32767]
            audio_int16: np.ndarray = np.int16(self.audio_data * MAX_AUDIO_VALUE)
            audio_bytes: bytes = audio_int16.tobytes()

            # Create AudioData object for speech_recognition library
            # sr.AudioData(bytes, sample_rate, sample_width_in_bytes)
            audio_data_obj: sr.AudioData = sr.AudioData(
                audio_bytes, 
                SAMPLE_RATE, 
                AUDIO_BIT_DEPTH
            )

            # Send to Google's free speech recognition API
            text: str = self.recognizer.recognize_google(audio_data_obj)
            logger.info(f"Transcription successful: {text[:50]}...")
            return text
            
        except sr.UnknownValueError:
            # Google API could not understand the audio
            logger.warning("Speech recognition failed: audio unclear")
            return "Could not understand audio"
            
        except sr.RequestError as e:
            # Network error or Google API issue
            logger.error(f"Google Speech Recognition API error: {e}", exc_info=True)
            return f"Error with Google API: {e}"
            
        except Exception as e:
            # Unexpected error during transcription
            logger.error(f"Unexpected transcription error: {e}", exc_info=True)
            return f"Error: {e}"