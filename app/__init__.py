"""Talk-To-AI Application Package.

This package contains all the core components of the Talk-To-AI voice assistant
application, including configuration management, audio handling, AI integration,
and UI components.

Modules:
    config: Configuration management and settings persistence
    menu_bar: Menu bar icon and dropdown popover
    hotkey_listener: Global keyboard hotkey detection
    audio_handler: Microphone recording and audio checks
    transcriber: Speech-to-text (local Whisper, Google as backup)
    ai_handler: AI API routing (Claude, ChatGPT, Gemini), streamed answers
    streaming: Splits a streaming answer into speakable sentences
    voice_handler: Interruptible text-to-speech
    settings_panel: Settings window
    response_display: Floating response window
    theme: Shared colors, fonts, icons and stylesheet
    widgets: Reusable UI components
    app_support: Logging, single instance, permissions, Open at login

Usage:
    from app.config import ConfigManager
    from app.audio_handler import AudioHandler
    from app.ai_handler import AIHandler
    
    config = ConfigManager()
    audio = AudioHandler(config)
    ai = AIHandler(config)
"""

__version__ = "1.2.0"
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
