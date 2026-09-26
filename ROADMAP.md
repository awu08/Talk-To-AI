# Talk-To-AI Roadmap

## Project Vision

Keyboard shortcuts on your device activate the app and a chosen LLM, which then produces either a voice response or an interface response on your device that answers your question.

## Completed Features

- [x] Global hotkey detection (cmd+option+space, customizable)
- [x] Multi-AI support (Claude, ChatGPT, Gemini)
- [x] Voice input (Google Speech-to-Text transcription)
- [x] Voice output (pyttsx3 TTS with customizable speed and voice)
- [x] Settings panel with full customization
- [x] Menu bar integration (system tray icon)
- [x] Configuration persistence (~/.talktoai/settings.json)
- [x] Conversation history management (clear history button)
- [x] Professional code documentation (type hints, docstrings)
- [x] README.md with comprehensive documentation
- [x] GitHub repository with MIT License
- [x] .gitignore and .env.example templates
- [x] Package initialization (app/__init__.py)
- [x] Hotkey listener with pause/resume functionality
- [x] Audio recording and transcription pipeline
- [x] Response display modes (voice, popup, or both)
- [x] Settings window with close button fix

## In Progress

- [ ] Custom hotkey recording UI (currently read-only in settings)
- [ ] Save settings as default with reset option (partially implemented)
- [ ] UI polishing and visual improvements

## Planned Features

- [ ] Offline mode with local LLMs fallback
- [ ] Context awareness (clipboard, browser content)
- [ ] Persistent conversation history across sessions
- [ ] Windows/Linux support
- [ ] Packaged .app distribution (PyInstaller)
- [ ] Streaming AI responses
- [ ] Custom hotkey UI recording
- [ ] Multi-app session management

## Technical Architecture

- **Desktop Framework**: PyQt6 (macOS native)
- **Hotkey Detection**: pynput (global keyboard monitoring)
- **Audio**: sounddevice + Google Speech-to-Text
- **AI Providers**: Anthropic SDK, OpenAI SDK, Google Generative AI
- **Text-to-Speech**: pyttsx3 (cross-platform)
- **Configuration**: JSON (local file storage at ~/.talktoai/)
- **Background Execution**: Menu bar application
- **Code Quality**: Type hints, comprehensive docstrings, error handling

## Dates

- **Project Start**: 8/24/2026 (Vision)
- **Detailed Planning**: 8/25/2026
- **To-Do List**: 8/30/2026
- **MVP Completion**: 9/26/2026
