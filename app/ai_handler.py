"""AI Handler: Routes prompts to multiple LLM providers, streaming the answer.

This module provides a unified interface for Claude, ChatGPT and Gemini. It
keeps the conversation history, sends the shared system prompt (which sizes
answers to the question), and streams the answer back piece by piece so the
app can show and speak it while the rest is still being written.

Speed: by default each request asks the model for "quick" thinking (low
effort), since spoken questions rarely need deep reasoning. Settings → AI
Model → Thinking switches back to the model's own default. If a model doesn't
accept the quick setting (e.g. an older model entered under "Other…"), the
request is retried without it.

Author: Allen Wu
Version: 1.2.0
"""

import logging
from typing import Callable, Dict, Iterator, List, Optional

from anthropic import Anthropic
from openai import BadRequestError, OpenAI

from app import api_keys, models_catalog

logger = logging.getLogger(__name__)

# Upper limit on answer length. On models that think, this also covers thinking.
DEFAULT_MAX_TOKENS: int = 2048

# Settings → AI Model → Thinking
THINKING_QUICK: str = "quick"      # low effort: fastest replies (default)
THINKING_DEFAULT: str = "default"  # whatever the model does by default

# Gemini models whose lowest thinking level is "minimal" (others start at "low").
# From https://ai.google.dev/gemini-api/docs/thinking (October 2026)
GEMINI_MINIMAL_THINKING = {
    "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3-flash-preview",
}

# Words that show up in an API error when a model rejects a speed setting
_SPEED_SETTING_WORDS = ("effort", "output_config", "reasoning", "thinking")

# Sent with every request. Answers are spoken aloud, so length matters a lot:
# quick questions get quick answers, hard ones get only as much as they need.
SYSTEM_PROMPT: str = """You are a voice assistant. Your reply is read aloud and also shown in a small window, so keep it as short as the question allows.

First judge what kind of question it is, then size the answer to fit:
- Quick questions (facts, yes/no, definitions, conversions, times, spelling, small talk): answer in one or two short sentences. Give the answer first. No preamble, no restating the question, no extra background, and no offer to say more.
- Questions that need explaining, reasoning, comparing options, or steps: give a fuller answer, usually one to three short paragraphs or a short numbered list. Cover what the person needs to understand or act, then stop.
- If the person asks for detail ("explain", "walk me through", "in depth"), you can go longer. If they ask for it short, keep it short.

Because the reply is spoken: write in plain, natural sentences. Avoid tables, headings, code blocks, links and emoji unless asked. Don't add caveats, disclaimers or a summary at the end unless they really matter."""
SUPPORTED_PROVIDERS: set = {"Claude", "ChatGPT", "Gemini"}


class AIHandler:
    """Unified, streaming interface to Claude, ChatGPT and Gemini.

    Attributes:
        config (ConfigManager): Provider, model, keys and the Thinking setting
        conversation_history (List[Dict]): {"role": "user"|"assistant", "content": str}
        PROVIDERS (set): Supported provider names

    Example:
        >>> handler = AIHandler(config)
        >>> for piece in handler.stream_prompt("What is 2+2?"):
        ...     print(piece, end="")
        Four.
        >>> handler.send_prompt("And 3+3?")   # same, but waits for the whole answer
        'Six.'
    """

    PROVIDERS: set = {"Claude", "ChatGPT", "Gemini"}

    def __init__(self, config) -> None:
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self._clients: Dict[tuple, object] = {}  # reused so connections stay warm
        self._validate_config()
        logger.debug("AIHandler initialized")

    def _validate_config(self) -> None:
        provider: str = self.config.get("api", "provider")
        if provider and provider not in self.PROVIDERS:
            logger.warning(f"Unknown provider '{provider}'. Supported: {self.PROVIDERS}")

    # ------------------------------------------------------------------ public

    def current_model(self) -> str:
        """The model a request would use right now (the provider default if none is set)."""
        provider = self.config.get("api", "provider") or ""
        model = self.config.get("api", "model") or ""
        if not model:
            default = models_catalog.default_model(provider)
            model = default.id if default else ""
        return model

    def stream_prompt(self, user_text: str, use_history: bool = True) -> Iterator[str]:
        """Send a question and yield the answer in pieces as it's written.

        The question and the answer (even a partial one, if the caller stops
        early) are added to the conversation history.

        Raises:
            ValueError: If the API key or model isn't configured, or the
                provider is unknown
            Exception: Errors from the provider's API
        """
        provider: str = self.config.get("api", "provider") or ""
        api_key: str = api_keys.active_key(self.config, provider) if provider else ""
        if not api_key:
            logger.error("API key not configured")
            raise ValueError("API key is required but not configured")
        model = self.current_model()
        if not model:
            logger.error("Model not configured")
            raise ValueError("Model is required but not configured")
        if provider not in self.PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}")

        question = {"role": "user", "content": user_text}
        self.conversation_history.append(question)
        messages = list(self.conversation_history) if use_history else [question]
        quick = (self.config.get("api", "thinking") or THINKING_QUICK) == THINKING_QUICK
        streamer = {"Claude": self._stream_claude, "ChatGPT": self._stream_chatgpt,
                    "Gemini": self._stream_gemini}[provider]

        pieces: List[str] = []
        try:
            for piece in self._with_speed_fallback(
                    lambda q: streamer(model, api_key, messages, q), quick, model):
                if piece:
                    pieces.append(piece)
                    yield piece
        except Exception as e:
            logger.error(f"Error communicating with {provider}: {e}", exc_info=True)
            raise
        finally:
            answer = "".join(pieces)
            if answer:
                self.conversation_history.append({"role": "assistant", "content": answer})
            elif self.conversation_history and self.conversation_history[-1] is question:
                self.conversation_history.pop()  # keep user/assistant pairs
            logger.debug(f"History now has {len(self.conversation_history)} messages")

    def send_prompt(self, user_text: str, use_history: bool = True) -> str:
        """Send a question and return the whole answer (non-streaming convenience)."""
        return "".join(self.stream_prompt(user_text, use_history))

    def clear_history(self) -> None:
        """Forget the conversation so the next question starts fresh."""
        self.conversation_history = []
        logger.info("Conversation history cleared by user")

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _with_speed_fallback(make_stream: Callable[[bool], Iterator[str]], quick: bool,
                             model: str) -> Iterator[str]:
        """Stream with quick thinking; if the model rejects that setting, retry without it."""
        started = False
        try:
            for piece in make_stream(quick):
                started = True
                yield piece
        except Exception as e:
            if quick and not started and any(w in str(e).lower() for w in _SPEED_SETTING_WORDS):
                logger.info(f"{model} doesn't accept the quick-thinking setting; "
                            "retrying with its default")
                yield from make_stream(False)
            else:
                raise

    def _client(self, kind: str, api_key: str, factory: Callable[[], object]) -> object:
        key = (kind, api_key)
        if key not in self._clients:
            self._clients = {key: factory()}  # one client at a time is plenty
        return self._clients[key]

    # -------------------------------------------------------------- providers

    def _stream_claude(self, model: str, api_key: str, messages: List[Dict[str, str]],
                       quick: bool) -> Iterator[str]:
        """Stream from Claude. Quick = output_config.effort "low"."""
        client = self._client("claude", api_key, lambda: Anthropic(api_key=api_key))
        request = dict(model=model, max_tokens=DEFAULT_MAX_TOKENS, system=SYSTEM_PROMPT,
                       messages=messages)
        if quick:
            request["extra_body"] = {"output_config": {"effort": "low"}}
        with client.messages.stream(**request) as stream:
            for text in stream.text_stream:
                yield text

    def _stream_chatgpt(self, model: str, api_key: str, messages: List[Dict[str, str]],
                        quick: bool) -> Iterator[str]:
        """Stream from ChatGPT. Quick = reasoning_effort "low"."""
        client = self._client("openai", api_key, lambda: OpenAI(api_key=api_key))
        request = dict(model=model, stream=True,
                       messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages)
        if quick:
            request["reasoning_effort"] = "low"
        try:
            # Current models take max_completion_tokens...
            stream = client.chat.completions.create(
                **request, max_completion_tokens=DEFAULT_MAX_TOKENS)
        except BadRequestError as e:
            if "max_completion_tokens" not in str(e):
                raise
            # ...some older ones only know max_tokens
            stream = client.chat.completions.create(**request, max_tokens=DEFAULT_MAX_TOKENS)
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _stream_gemini(self, model: str, api_key: str, messages: List[Dict[str, str]],
                       quick: bool) -> Iterator[str]:
        """Stream from Gemini (google-genai SDK). Quick = thinking level minimal/low."""
        from google import genai
        from google.genai import types

        client = self._client("gemini", api_key, lambda: genai.Client(api_key=api_key))
        contents = [
            types.Content(role="model" if m["role"] == "assistant" else "user",
                          parts=[types.Part(text=m["content"])])
            for m in messages
        ]
        thinking = None
        if quick:
            level = "MINIMAL" if model in GEMINI_MINIMAL_THINKING else "LOW"
            thinking = types.ThinkingConfig(thinking_level=level)
        config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                             thinking_config=thinking)
        for chunk in client.models.generate_content_stream(model=model, contents=contents,
                                                           config=config):
            text = getattr(chunk, "text", None)
            if text:
                yield text
