# Talk-To-AI

A macOS desktop voice assistant that brings Claude, ChatGPT, or Gemini to your fingertips with a single keyboard shortcut. Record voice questions from any application and get instant AI responses with text-to-speech.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

## Features

- **Global Hotkey** — Press `cmd+option+space` (customizable) from anywhere to activate
- **Voice Input** — Speak naturally; Google Whisper transcribes automatically
- **Multi-AI Support** — Choose between Claude, ChatGPT, or Gemini APIs
- **Voice Response** — AI answers spoken aloud with customizable voice and speed
- **Conversation History** — Maintain context across multiple queries
- **Menu Bar Integration** — Minimal UI; lives in your system tray
- **Real-Time Settings** — Configure hotkeys, API keys, voice settings on-the-fly
- **Privacy-First** — API keys stored locally on your machine

## Quick Start

### Prerequisites
- macOS 10.13+
- Python 3.13+
- API key from Claude, OpenAI, or Google Gemini (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/awu08/Talk-To-AI.git
cd Talk-To-AI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Setup

1. **Get an API Key** (choose one):
   - **Claude:** https://console.anthropic.com → Create API Key
   - **Gemini (Free):** https://ai.google.dev → Create API Key (1M tokens/day)
   - **OpenAI:** https://platform.openai.com

2. **Run the application:**
```bash
   python3 main.py
```

3. **Configure in Settings:**
   - Click system tray icon → Settings
   - Enter your API key
   - Select AI provider and model
   - Customize hotkeys and voice settings

## Usage

1. **Press your hotkey** (default: `cmd+option+space`)
2. **Speak your question** — Microphone activates
3. **Press stop hotkey** (default: `esc`)
4. **AI responds** — Voice plays + optional popup

## Project Structure

- **main.py** — Entry point, orchestrates all components
- **requirements.txt** — Python dependencies
- **LICENSE** — MIT License
- **README.md** — Documentation

### App Module (`app/`)
- **config.py** — Settings management (stores in ~/.talktoai/settings.json)
- **menu_bar.py** — System tray icon and UI menu
- **hotkey_listener.py** — Global keyboard hotkey detection
- **audio_handler.py** — Audio recording and Google speech-to-text transcription
- **ai_handler.py** — AI API routing (Claude, ChatGPT, Gemini)
- **voice_handler.py** — Text-to-speech synthesis with pyttsx3
- **settings_panel.py** — Settings configuration window
- **response_display.py** — AI response popup window

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Desktop UI** | PyQt6 |
| **Hotkey Detection** | pynput |
| **Audio Capture** | sounddevice, numpy |
| **Speech Recognition** | Google Speech-to-Text |
| **AI Providers** | Anthropic SDK, OpenAI SDK, Google Generative AI |
| **Text-to-Speech** | pyttsx3 |
| **Configuration** | JSON (local file storage) |

## Configuration

Settings are stored in `~/.talktoai/settings.json`:

```json
{
  "hotkeys": {
    "start": "cmd+option+space",
    "stop": "esc"
  },
  "api": {
    "provider": "Gemini",
    "model": "gemini-3.6-flash",
    "api_key": "your-api-key-here"
  },
  "voice": {
    "speed": 1.0,
    "voice_name": "Alex"
  },
  "response_mode": {
    "voice": true,
    "popup": true
  }
}
```

## API Recommendations

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| **Gemini** | 1M tokens/day | Best free option |
| **Claude** | None (pay-as-you-go) | Best reasoning |
| **ChatGPT** | None (pay-as-you-go) | Popular choice |

**For testing:** Use Gemini free tier (no payment required)

## Features in Development

- [ ] Context awareness (clipboard, browser content)
- [ ] Persistent conversation history
- [ ] Custom hotkey recording UI
- [ ] Windows/Linux support
- [ ] Packaged .app distribution
- [ ] Streaming AI responses

## What I Learned

This project demonstrates:

- Full-stack desktop application development using PyQt6
- Cross-platform keyboard event handling with pynput at OS level
- Async/threading patterns for responsive UI during long operations
- Multi-API integration with unified interface for Claude, ChatGPT, and Gemini
- Audio processing (recording, format conversion, transcription)
- Configuration management with JSON persistence
- Professional Python practices (type hints, logging, error handling, docstrings)
- Git workflow and open-source project structure

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Author

**Allen Wu** — CS & Math @ UPenn (Class of 2030)

- GitHub: [@awu08](https://github.com/awu08)
- LinkedIn: [allen-wu-857541295](https://www.linkedin.com/in/allen-wu-857541295/)
- Email: wuallen@sas.upenn.edu

---