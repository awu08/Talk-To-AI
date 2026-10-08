# Changelog

## v1.1.0 — 10/8/2026

### New
- **Mac app**: Talk-To-AI is now a real app (`Talk-To-AI.app`) with its own icon, delivered as a `.dmg`. Build it with `bash build_app.sh`, or `bash build_app.sh --install` to put it straight into Applications.
- **Redesigned interface**: a dark, macOS-style look across the menu bar, Settings, and response window.
- **Menu bar dropdown**: shows whether it's ready, listening, or speaking, with quick toggles, Clear conversation, Settings, and Quit.
- **Settings window**: sidebar with General, AI Model, and Voice sections.
- **Model picker**: choose a model from a list for each provider, with what each is good at (free, fastest, deeper thinking…). **Other…** lets you enter any model ID. If none is chosen, the provider's recommended model is used.
- **Record shortcuts**: click a shortcut in Settings and press the new combo.
- **On-device speech recognition**: Whisper transcribes your speech on your Mac (free, private, offline). Choose Fast, Balanced, or Most accurate. Google remains as a backup.
- **Right-sized answers**: quick questions get short answers; complex ones get only as much as they need.
- **Stop the voice anytime**: press Esc, click Stop speaking or Done, or ask a new question.
- **Response window**: shows your question, "Thinking…", then the formatted answer with Copy.
- **Open at login**, plus a log file at `~/Library/Logs/Talk-To-AI/`.

### Improved
- Voice list shows the voices actually installed on your Mac.
- Gemini now remembers earlier questions in the conversation.
- Works with OpenAI's newest models, which need a different answer-length setting.
- Clear messages when something's wrong: missing API key, blocked microphone, recording too short, or speech not understood.
- Hotkeys keep working while an answer is being spoken.

### Fixed
- The response popup never appeared (it was disabled because of a threading issue).
- "Speak responses" and "Show response window" turned themselves back on after restarting.
- Recording dropped audio between half-second chunks, which hurt recognition.
- Failed transcriptions were sent to the AI as if you'd asked "Could not understand audio".
- Closing the Settings window could quit the app.
- Speech failed with "Not a directory: 'say'" when the shell's PATH was missing `/usr/bin`.
- Running the app twice created two menu bar icons fighting over the hotkeys.

## v1.0.0 — 9/26/2026

- First version: global hotkey, voice questions, Claude / ChatGPT / Gemini, spoken answers, menu bar icon, and Settings.
