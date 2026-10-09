# Talk-To-AI

A macOS menu bar voice assistant that brings Claude, ChatGPT, or Gemini to your fingertips with a single keyboard shortcut. Ask a question out loud from any app, and get the answer spoken back and shown in a small window.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Platform](https://img.shields.io/badge/macOS-12%2B-black.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

## Features

- **Global Hotkey** — Press `⌘ ⌥ Space` from any app to start talking, `Esc` to send
- **Custom Shortcuts** — Click a shortcut in Settings and press the new combo to change it
- **On-Device Transcription** — Whisper turns your speech into text right on your Mac (free, private, works offline), with Google as a backup
- **Multi-AI Support** — Choose between Claude, ChatGPT, or Gemini
- **Saved Keys per Provider** — Each provider remembers its own API key, so switching provider swaps the key; add extra named keys (like "Work") and pick which one to use
- **Model Picker** — Pick a model from a list that says what each one is good at (free, fastest, deeper thinking…), or choose **Other…** to use any model ID
- **Fast, Streamed Answers** — The answer appears as it's written and the voice starts after the first sentence; a "quick thinking" setting makes models reply sooner
- **Right-Sized Answers** — Quick questions get a sentence or two; harder ones get only as much as they need
- **Voice Response** — Answers are read aloud with any voice installed on your Mac, at the speed you choose
- **Interruptible** — Ask a new question, or click **Stop speaking** or **Done**, to cut the voice off (it keeps talking while you use other apps)
- **Response Window** — A floating panel shows your question and the formatted answer, with Copy
- **Menu Bar App** — No Dock icon; a dropdown panel shows status, quick toggles, Settings and Quit
- **Open at Login** — Optionally starts automatically when you log in
- **Conversation History** — The AI remembers earlier questions until you clear them
- **Privacy-First** — API keys and settings stay on your Mac; speech is transcribed locally

## Install the App

1. **Download** the latest **Talk-To-AI-x.y.z.dmg** from the [Releases page](https://github.com/awu08/Talk-To-AI/releases/latest). It's built for Apple Silicon Macs (M1 or newer) on macOS 12 or newer; on an Intel Mac, [build it yourself](#build-the-app-yourself).
2. **Install**: open the .dmg and drag **Talk-To-AI** into **Applications**.
3. **First launch**: open Talk-To-AI from Applications. Because the app isn't notarized by Apple, macOS blocks it the first time: go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway**.
4. **Permissions**: macOS asks for three things, and the app tells you if any is still missing:
   - **Microphone**: click Allow when asked.
   - **Accessibility** and **Input Monitoring** (needed for the global shortcut): in **System Settings → Privacy & Security**, turn on **Talk-To-AI** in both lists.
   Then quit Talk-To-AI (menu bar mic → **Quit**) and open it again.
5. **Add an AI**: click the microphone in the menu bar → **Settings → AI Model**, pick a provider and model, and paste your API key (see below).

The app has no Dock icon; it lives in the menu bar. The first question downloads the Whisper speech model once (about 500 MB for the default size; you can pick a smaller or larger one in **Settings → Voice**). Turn on **Settings → General → Open at login** to start it automatically.

### Get an API key

Talk-To-AI uses your own API key, so you only pay the provider for what you use (or nothing, on Gemini's free tier). Pick one:

- **Gemini (free tier):** https://ai.google.dev → Get API key
- **Claude:** https://console.anthropic.com → API Keys → Create Key
- **ChatGPT (OpenAI):** https://platform.openai.com → API keys → Create new secret key

Each provider keeps its own key in Settings, so you can add more than one and switch providers anytime.

### Update to a new version

1. Quit Talk-To-AI (menu bar mic → **Quit**).
2. Download the new .dmg from the [Releases page](https://github.com/awu08/Talk-To-AI/releases/latest) and drag Talk-To-AI into **Applications**, choosing **Replace**.
3. Open it. Your settings and API keys are kept. If the shortcut stops working, macOS treats the new version as a new app: in **Privacy & Security → Accessibility** and **Input Monitoring**, turn Talk-To-AI off and back on, then reopen it.

### Uninstall

1. Quit Talk-To-AI (menu bar mic → **Quit**), and turn off **Open at login** in Settings if you turned it on.
2. Drag **Talk-To-AI** from Applications to the Trash.
3. Optional, to remove everything it saved:
   ```bash
   rm -rf ~/.talktoai                 # settings and API keys
   rm -rf ~/Library/Logs/Talk-To-AI   # logs
   rm -rf ~/.cache/huggingface/hub/models--Systran--faster-whisper-*   # Whisper model
   ```
4. Optional: remove Talk-To-AI from **Privacy & Security → Accessibility**, **Input Monitoring** and **Microphone** (select it and click **−**).

## Usage

1. **Press your start shortcut** (default: `⌘ ⌥ Space`) — the menu bar mic turns orange
2. **Ask your question**
3. **Press your stop shortcut** (default: `Esc`) — the response window shows "Thinking…"
4. **Get the answer** — it appears as it's written and is read aloud starting with the first sentence
5. **Stop it anytime** — press the start shortcut to ask something new, or click **Stop speaking** or **Done**. Clicking other apps or pressing `Esc` elsewhere won't cut it off (turn on **Settings → General → Stop shortcut also stops speaking** if you want `Esc` to stop it)

Click the menu bar mic for status, to turn spoken answers or the response window on and off, to clear the conversation, or to open Settings.

## Settings

| Section | What you can change |
|---------|---------------------|
| **General** | Start/stop shortcuts, spoken answers, response window, whether the stop shortcut also stops speaking, Open at login, clear chat history |
| **AI Model** | Provider (Claude, ChatGPT, Gemini), model (from a described list, or Other… for any model ID), Thinking (quick or the model's default), API key (one per provider, plus named extras via **Add another key…**) |
| **Voice** | Speech recognition (Whisper or Google), Whisper accuracy, voice, speaking speed |

Changes save automatically.

## Build the App Yourself

On a Mac, from the project folder:

```bash
bash build_app.sh            # builds dist/Talk-To-AI.app and dist/Talk-To-AI-<version>.dmg
bash build_app.sh --install  # same, then puts the app straight into Applications
```

It builds for the kind of Mac you're on and takes a few minutes. You need Python 3.10+ and about 3 GB of free disk space.

To have GitHub build the .dmg for you, push a version tag. The workflow in `.github/workflows/build-macos.yml` attaches the .dmg to a new Release:

```bash
git tag v1.2.0
git push origin v1.2.0
```

## Run From Source

### Prerequisites
- macOS 12+
- Python 3.10+ (3.13 recommended)
- API key from Claude, OpenAI, or Google Gemini (Gemini has a free tier)

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

1. **Get an API key** (see [Get an API key](#get-an-api-key) above).

2. **Run the application:**
   ```bash
   python3 main.py
   ```

3. **Configure in Settings:**
   - Click the menu bar microphone → Settings
   - Under **AI Model**, choose a provider, pick a model from the list (or **Other…** to type any model ID) and paste your API key
   - Each provider keeps its own key. To keep a second key for the same provider (say, a work account), choose **Key → Add another key…**, name it, and paste it
   - Optionally change shortcuts (click one under General and press your new combo) and voice settings

When running from source, macOS asks for Microphone, Accessibility and Input Monitoring permission for your terminal app rather than for Talk-To-AI.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| The shortcut does nothing | Turn on Talk-To-AI (or your terminal, if running from source) in **System Settings → Privacy & Security → Accessibility** and **Input Monitoring**, then reopen the app. After rebuilding the app, turn both switches off and on again |
| "The microphone recorded silence" | Allow it in **System Settings → Privacy & Security → Microphone**, then reopen the app |
| "Sorry, I didn't catch that" | Wait a moment after pressing the shortcut before speaking, speak closer to the mic, or choose a larger Whisper model in **Settings → Voice** |
| "Add your API key…" | Enter it in **Settings → AI Model** |
| The voice stopped unexpectedly | The log lists every stop and why (`Speech stopped (…)`) |
| Answers feel slow | Keep **Settings → AI Model → Thinking** on Quick, and try a model labeled **Fastest**. The log shows how long each answer took (`Timing …`) |
| The first answer takes a long time | Whisper is downloading its model; later questions are much faster |
| Can't find the app | It has no Dock icon; look for the microphone in the menu bar near the clock. On MacBooks with a notch, a crowded menu bar can hide it behind the notch |
| "Talk-To-AI can't be opened" | macOS blocks unsigned apps the first time: **Privacy & Security → Open Anyway** |

Logs are saved to `~/Library/Logs/Talk-To-AI/talk-to-ai.log`.

## Project Structure

- **main.py** — Entry point; coordinates hotkeys, recording, the AI and responses
- **requirements.txt** — Python dependencies
- **build_app.sh** — Builds `Talk-To-AI.app` and the `.dmg`
- **README.md**, **ROADMAP.md**, **CHANGELOG.md**, **LICENSE**

### App Module (`app/`)
- **config.py** — Settings management (stores in ~/.talktoai/settings.json)
- **menu_bar.py** — Menu bar icon and dropdown popover (status, quick toggles, Settings/Quit)
- **hotkey_listener.py** — Global keyboard hotkey detection
- **audio_handler.py** — Microphone recording and audio checks
- **transcriber.py** — Speech-to-text: local Whisper, with Google as backup
- **ai_handler.py** — AI API routing (Claude, ChatGPT, Gemini), streamed answers, quick thinking and the answer-length instructions
- **streaming.py** — Splits a streaming answer into sentences so speech can start early
- **api_keys.py** — Saved API keys per provider (Primary plus named extras)
- **models_catalog.py** — The models offered in Settings, with descriptions (edit this when providers release new models)
- **voice_handler.py** — Interruptible text-to-speech
- **settings_panel.py** — Settings window with sidebar sections (General, AI Model, Voice)
- **response_display.py** — Floating response window with Markdown, Copy, Stop and Done
- **theme.py** — Shared dark theme: colors, fonts, icons and stylesheet
- **widgets.py** — Reusable UI pieces (toggle switch, cards, setting rows, shortcut recorder)
- **app_support.py** — App plumbing: log file, single instance, permission checks, Open at login

### Packaging
- **packaging/Talk-To-AI.spec** — PyInstaller recipe (bundled libraries, menu-bar-only, microphone permission text)
- **packaging/make_icon.py** — Draws the app icon
- **.github/workflows/build-macos.yml** — Builds the `.dmg` on GitHub for tagged releases

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Desktop UI** | PyQt6 with a custom dark theme |
| **Hotkey Detection** | pynput |
| **Audio Capture** | sounddevice, numpy |
| **Speech Recognition** | Whisper via faster-whisper (local), Google Speech-to-Text (backup) |
| **AI Providers** | Anthropic SDK, OpenAI SDK, Google Gen AI SDK (all streamed) |
| **Text-to-Speech** | macOS `say` (interruptible), pyttsx3 on other systems |
| **Packaging** | PyInstaller, GitHub Actions |
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
    "thinking": "quick",
    "keys": {
      "Gemini": { "Primary": "your-gemini-key" },
      "Claude": { "Primary": "your-claude-key", "Work": "your-work-claude-key" }
    },
    "active_keys": { "Claude": "Work" },
    "api_key": "your-gemini-key"
  },
  "speech": {
    "engine": "whisper",
    "model": "small.en"
  },
  "voice": {
    "speed": 1.0,
    "voice_name": ""
  },
  "response_mode": {
    "voice": true,
    "popup": true,
    "stop_key_stops_speech": false
  }
}
```

`api.thinking` is `quick` (fastest) or `default` (the model's own thinking). `api.model` is any model ID; Settings fills it in from the list. `api.keys` holds each provider's keys by name, `api.active_keys` says which one each provider uses (Primary if not listed), and `api.api_key` mirrors the key in use. `voice_name` is empty for the system's default voice. `speech.model` can be `base.en` (fast), `small.en` (balanced) or `medium.en` (most accurate).

## API Recommendations

| Provider | Free Tier | Best For |
|----------|-----------|----------|
| **Gemini** | Yes (with daily limits) | Best free option |
| **Claude** | None (pay-as-you-go) | Best reasoning |
| **ChatGPT** | None (pay-as-you-go) | Popular choice |

**For testing:** Use the Gemini free tier (no payment required). Free-tier limits change, so check Google AI Studio for current numbers.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for what's done and what's planned, and [CHANGELOG.md](CHANGELOG.md) for what changed in each version.

## What I Learned

This project demonstrates:

- Full-stack desktop application development using PyQt6, including a custom design system
- Cross-platform keyboard event handling with pynput at OS level
- Async/threading patterns for responsive UI: worker threads, Qt signals, streaming, and cancelling stale work
- Multi-API integration with a unified interface for Claude, ChatGPT, and Gemini
- Prompt design to control answer length and style for spoken responses
- Audio processing and on-device machine learning (recording, level checks, local Whisper transcription)
- Packaging a Python app as a native macOS app, with CI builds on GitHub Actions
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
