"""Talk-To-AI Application Package.

This package contains all the core components of the Talk-To-AI voice assistant
application, including configuration management, audio handling, AI integration,
and UI components.

Modules:
    config: Configuration management and settings persistence
    menu_bar: System tray icon and application menu
    hotkey_listener: Global keyboard hotkey detection
    audio_handler: Audio recording and speech-to-text transcription
    ai_handler: AI API routing (Claude, ChatGPT, Gemini)
    voice_handler: Text-to-speech synthesis and audio playback
    settings_panel: Settings configuration UI
    response_display: AI response popup display window

Usage:
    from app.config import ConfigManager
    from app.audio_handler import AudioHandler
    from app.ai_handler import AIHandler
    
    config = ConfigManager()
    audio = AudioHandler()
    ai = AIHandler(config)
"""

__version__ = "1.1.0"
__author__ = "Allen Wu"
__all__ = [
    "ConfigManager",
    "MenuBar",
    "HotkeyListener",
    "AudioHandler",
    "AIHandler",
    "VoiceHandler",
    "SettingsPanel",
    "ResponseDisplay",
]
