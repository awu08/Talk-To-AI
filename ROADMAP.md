# Talk-To-AI Roadmap

## Project Vision

Keyboard shortcuts on your device activate the app and a chosen LLM, which then produces either a voice response or an interface response on your device that answers your question.

## Completed Features

### MVP (9/26/2026)
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

### v1.1 (10/8/2026)
- [x] UI polishing and visual improvements (dark, macOS-style redesign across every window)
- [x] Menu bar dropdown with status, quick toggles, and Settings / Quit
- [x] Settings window with sidebar sections (General, AI Model, Voice)
- [x] Model picker with descriptions (free, fast, deep thinking), plus Other… for any model
- [x] Custom hotkey recording + UI
- [x] Floating response window with the question, formatted answer, Copy, Stop, and Done
- [x] On-device Whisper transcription (free, offline, more accurate), Google as backup
- [x] Answer length matched to the question (quick vs. complex)
- [x] Interruptible speech (Esc, Stop, Done, or asking a new question)
- [x] Voice picker using the voices installed on the Mac
- [x] Conversation history for Gemini
- [x] Clear error messages (missing API key, blocked microphone, unclear audio)
- [x] Create a proper app version (Talk-To-AI.app and .dmg, built with PyInstaller)
- [x] Open at login, single running copy, log file, permission checks
- [x] Automatic .dmg builds on GitHub for tagged releases

## In Progress

- [ ] Context awareness (clipboard, browser content)

## Planned Features

- [ ] Microphone picker and live input level in Settings
- [ ] Streaming AI responses (start speaking before the full answer arrives)
- [ ] Switch Gemini to the newer `google-genai` SDK (the current library is deprecated)
- [ ] Apple code signing and notarization (no security warning on first launch)
- [ ] Homebrew install (`brew install --cask talk-to-ai`)
- [ ] Offline mode with local LLMs fallback
- [ ] Persistent conversation history across sessions
- [ ] Windows/Linux support
- [ ] Multi-app session management

## Technical Architecture

- **Desktop Framework**: PyQt6 with a shared dark theme (macOS native look)
- **Hotkey Detection**: pynput (global keyboard monitoring)
- **Audio**: sounddevice (continuous microphone stream)
- **Speech Recognition**: Whisper via faster-whisper (on-device), Google Speech-to-Text (backup)
- **AI Providers**: Anthropic SDK, OpenAI SDK, Google Generative AI
- **Text-to-Speech**: macOS `say` (interruptible), pyttsx3 on other systems
- **Concurrency**: Worker threads for slow work; Qt signals for UI updates
- **Configuration**: JSON (local file storage at ~/.talktoai/)
- **Background Execution**: Menu bar application
- **Packaging**: PyInstaller (.app + .dmg), GitHub Actions for release builds
- **Code Quality**: Type hints, comprehensive docstrings, error handling

## Dates

- **Project Start**: 8/24/2026 (Vision)
- **Detailed Planning**: 8/25/2026
- **To-Do List**: 8/30/2026
- **MVP Completion**: 9/26/2026
- **v1.1 (Redesign, Whisper, Mac App)**: 10/8/2026
