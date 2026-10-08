"""Voice Handler: Speaks AI responses aloud, and can be interrupted.

On macOS speech uses the built-in `say` command, which can be stopped the
instant you want: from the Stop button, by pressing the stop hotkey, or by
starting a new question. Other systems use pyttsx3.

Settings used:
    voice.voice_name: voice to use ("" = system default)
    voice.speed: 0.5–2.0 multiplier
    response_mode.voice: speak at all?

Author: Allen Wu
Version: 1.1.0
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

IS_MAC: bool = sys.platform == "darwin"


def _say_path() -> str:
    """Full path to macOS's `say`, so it works even if PATH is missing /usr/bin."""
    return "/usr/bin/say" if os.path.exists("/usr/bin/say") else (shutil.which("say") or "say")

# Speaking rates in words per minute at speed 1.0
MAC_SPEECH_RATE: int = 185      # macOS `say`
DEFAULT_SPEECH_RATE: int = 150  # pyttsx3
SPEECH_RATE_MIN: int = 75
SPEECH_RATE_MAX: int = 400

DEFAULT_VOICE_NAME: str = ""  # "" means the system's default voice

# macOS novelty/effect voices that make poor assistant voices
NOVELTY_VOICES = {
    "albert", "bad news", "bahh", "bells", "boing", "bubbles", "cellos",
    "good news", "jester", "organ", "superstar", "trinoids", "whisper",
    "wobble", "zarvox", "deranged", "hysterical", "pipe organ",
}


class _Voice:
    """Minimal voice record (name, languages, id) shared by both engines."""

    def __init__(self, name: str, languages: list, voice_id: str) -> None:
        self.name, self.languages, self.id = name, languages, voice_id


def _is_english(voice) -> bool:
    return any(str(lang).lower().replace("-", "_").startswith("en")
               for lang in (voice.languages or []) if lang)


def _installed_voices() -> List[_Voice]:
    """All voices on this computer."""
    if IS_MAC:
        try:
            out = subprocess.run([_say_path(), "-v", "?"], capture_output=True, text=True,
                                 timeout=10).stdout
        except Exception as e:
            logger.error(f"Couldn't list macOS voices: {e}")
            return []
        voices = []
        for line in out.splitlines():
            # e.g. "Eddy (English (US))   en_US    # Hello! My name is Eddy."
            match = re.match(r"^(.+?)\s+([a-z]{2,3}[_-][A-Za-z0-9]{2,4})\s+#", line)
            if match:
                voices.append(_Voice(match.group(1).strip(), [match.group(2)],
                                     match.group(1).strip()))
        return voices
    try:
        import pyttsx3
        return [_Voice(v.name or "", list(v.languages or []), v.id)
                for v in pyttsx3.init().getProperty("voices")]
    except Exception as e:
        logger.error(f"Couldn't list voices: {e}")
        return []


def list_voices() -> List[str]:
    """Names of installed English voices worth offering (novelty voices left out)."""
    names, seen = [], set()
    for voice in sorted(_installed_voices(), key=lambda v: v.name.lower()):
        if not voice.name or voice.name.lower() in NOVELTY_VOICES or voice.name in seen:
            continue
        if voice.languages and not _is_english(voice):
            continue
        seen.add(voice.name)
        names.append(voice.name)
    return names


def find_voice(voice_name: str, voices: List) -> Optional[str]:
    """Return the id of the best match for `voice_name`, or None for system default.

    Tries an exact name, then an English "Name (…)" variant (e.g. "Eddy" →
    "Eddy (English (US))"), then any name containing it.
    """
    wanted = (voice_name or "").strip().lower()
    if not wanted:
        return None
    for voice in voices:
        if (voice.name or "").lower() == wanted:
            return voice.id
    variants = [v for v in voices if (v.name or "").lower().startswith(wanted + " (")]
    variants.sort(key=lambda v: not _is_english(v))
    if variants:
        return variants[0].id
    for voice in voices:
        if wanted in (voice.name or "").lower():
            return voice.id
    logger.warning(f"Voice '{voice_name}' isn't installed; using the system default. "
                   "Pick another voice in Settings → Voice.")
    return None


def clean_for_speech(text: str) -> str:
    """Strip Markdown symbols so they aren't read aloud."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)          # code blocks
    text = re.sub(r"`([^`]*)`", r"\1", text)                    # inline code
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)      # links → their text
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)   # headings
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)        # bullets
    text = re.sub(r"(\*\*|__|\*|_)(\S.*?\S|\S)\1", r"\2", text)  # bold / italics
    return re.sub(r"[ \t]+", " ", text).strip()


class VoiceHandler:
    """Speaks text aloud; `stop()` cuts it off immediately.

    Attributes:
        config (ConfigManager): Provides voice settings
        on_state_change (Optional[Callable[[bool], None]]): Called with True when
            speech starts and False when it ends or is stopped. May be called
            from a background thread.

    Example:
        >>> handler = VoiceHandler(config)
        >>> threading.Thread(target=handler.speak, args=("Hello there",)).start()
        >>> handler.stop()  # from anywhere, e.g. a Stop button
    """

    def __init__(self, config) -> None:
        self.config = config
        self.on_state_change: Optional[Callable[[bool], None]] = None
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen] = None
        self._engine = None
        self._speaking: bool = False
        self._stop_count: int = 0  # bumps on every stop(); lets speech notice it was cancelled
        self._say_broken: bool = False
        self._default_voice_id: Optional[str] = None
        if not IS_MAC:
            self._init_pyttsx3()
        logger.info("Voice handler initialized (%s)", "macOS say" if IS_MAC else "pyttsx3")

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def speak(self, text: str) -> None:
        """Speak `text`, blocking until finished or stopped. Run it off the UI thread.

        Any speech already playing is stopped first.
        """
        if self.config.get("response_mode", "voice") is False:
            logger.debug("Voice response disabled in settings, skipping synthesis")
            return
        text = clean_for_speech(text)
        if not text:
            return
        self.stop()
        with self._lock:
            ticket = self._stop_count

        voice_name: str = self.config.get("voice", "voice_name") or DEFAULT_VOICE_NAME
        speed: float = self.config.get("voice", "speed") or 1.0
        try:
            self._set_speaking(True)
            if IS_MAC and not self._say_broken:
                try:
                    self._speak_mac(text, voice_name, speed, ticket)
                    return
                except OSError as e:
                    # `say` couldn't start; use pyttsx3 from now on (not interruptible)
                    logger.error(f"Couldn't run macOS 'say' ({e}); falling back to pyttsx3")
                    self._say_broken = True
            self._speak_pyttsx3(text, voice_name, speed)
        except Exception as e:
            logger.error(f"Error during text-to-speech synthesis: {e}", exc_info=True)
        finally:
            self._set_speaking(False)

    def stop(self) -> None:
        """Stop speaking right away. Safe to call from any thread, any time."""
        with self._lock:
            self._stop_count += 1
            process, self._process = self._process, None
        if process and process.poll() is None:
            process.terminate()
            logger.info("Speech stopped")
        if self._engine is not None and self._speaking:
            try:
                self._engine.stop()
            except Exception:
                pass

    # -------------------------------------------------------------- engines

    def _speak_mac(self, text: str, voice_name: str, speed: float, ticket: int) -> None:
        rate = max(SPEECH_RATE_MIN, min(SPEECH_RATE_MAX, int(MAC_SPEECH_RATE * speed)))
        command = [_say_path(), "-r", str(rate)]
        voice_id = find_voice(voice_name, _installed_voices()) if voice_name else None
        if voice_id:
            command += ["-v", voice_id]
        logger.info(f"Speaking with: {' '.join(command)}")
        # Errors go to a temp file (not a pipe) so stop() never waits on them
        errors = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=errors,
                                       text=True, encoding="utf-8")
        except OSError:
            errors.close()
            raise
        with self._lock:
            if self._stop_count != ticket:  # stop() arrived while we were starting
                process.kill()
                errors.close()
                return
            self._process = process
        try:
            try:
                process.communicate(text)  # text via stdin: no length or quoting limits
                stopped = self._stop_count != ticket
                if process.returncode not in (0, None) and not stopped:
                    errors.seek(0)
                    logger.error(f"'say' failed (exit {process.returncode}): "
                                 f"{errors.read().strip()[:300]}")
            except (BrokenPipeError, OSError):
                pass  # stopped while the text was still being sent
        finally:
            errors.close()
            with self._lock:
                if self._process is process:
                    self._process = None
        logger.info(f"Spoke: {text[:50]}...")

    def _init_pyttsx3(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._default_voice_id = self._engine.getProperty("voice")
        return self._engine

    def _speak_pyttsx3(self, text: str, voice_name: str, speed: float) -> None:
        engine = self._init_pyttsx3()
        voice_id = find_voice(voice_name, engine.getProperty("voices")) or self._default_voice_id
        if voice_id:
            engine.setProperty("voice", voice_id)
        rate = max(SPEECH_RATE_MIN, min(SPEECH_RATE_MAX, int(DEFAULT_SPEECH_RATE * speed)))
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
        logger.info(f"Spoke: {text[:50]}...")

    def _set_speaking(self, speaking: bool) -> None:
        if self._speaking == speaking:
            return
        self._speaking = speaking
        if self.on_state_change:
            try:
                self.on_state_change(speaking)
            except Exception as e:
                logger.error(f"Error in speech state callback: {e}", exc_info=True)