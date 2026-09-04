"""
Routes prompts to Claude, ChatGPT, or Gemini APIs and maintains conversation history.
"""

import logging
from anthropic import Anthropic
from openai import OpenAI
import google.generativeai as genai

logger = logging.getLogger(__name__)

# API configuration defaults
DEFAULT_MAX_TOKENS = 1024


class AIHandler:
    """Handles communication with multiple AI API providers."""

    # Supported providers
    PROVIDERS = {"Claude", "ChatGPT", "Gemini"}

    def __init__(self, config):
        """Initialize AI handler with configuration."""

        self.config = config
        self.conversation_history = []
        self._validate_config()

    def _validate_config(self):
        """Validate that required API configuration is present."""
        provider = self.config.get("api", "provider")
        if provider not in self.PROVIDERS:
            logger.warning(f"Unknown provider: {provider}. Supported: {self.PROVIDERS}")

    def send_prompt(self, user_text, use_history=True):
        provider = self.config.get("api", "provider")
        model = self.config.get("api", "model")
        api_key = self.config.get("api", "api_key")

        # Validate configuration
        if not api_key:
            logger.error("No API key configured")
            raise ValueError("API key is required but not configured")

        if not model:
            logger.error("No model configured")
            raise ValueError("Model is required but not configured")

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_text})

        try:
            # Route to correct provider
            if provider == "Claude":
                response = self._send_to_claude(model, api_key, use_history)
            elif provider == "ChatGPT":
                response = self._send_to_chatgpt(model, api_key, use_history)
            elif provider == "Gemini":
                response = self._send_to_gemini(model, api_key, use_history)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Add response to history
            self.conversation_history.append(
                {"role": "assistant", "content": response}
            )

            logger.debug(f"Got response from {provider}: {response[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Error communicating with {provider}: {e}")
            raise

    def _send_to_claude(self, model, api_key, use_history):
        """Send request to Claude (Anthropic) API."""
        client = Anthropic(api_key=api_key)

        # Use full history if requested, otherwise just last message
        messages = (
            self.conversation_history
            if use_history
            else [self.conversation_history[-1]]
        )

        response = client.messages.create(
            model=model, max_tokens=DEFAULT_MAX_TOKENS, messages=messages
        )

        return response.content[0].text

    def _send_to_chatgpt(self, model, api_key, use_history):
        """Send request to ChatGPT (OpenAI) API."""
        client = OpenAI(api_key=api_key)

        # Use full history if requested, otherwise just last message
        messages = (
            self.conversation_history
            if use_history
            else [self.conversation_history[-1]]
        )

        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=DEFAULT_MAX_TOKENS
        )

        return response.choices[0].message.content

    def _send_to_gemini(self, model, api_key, use_history):
        """Send request to Gemini (Google) API."""
        genai.configure(api_key=api_key)
        gemini_model = genai.GenerativeModel(model)

        # Get the latest user message
        user_message = self.conversation_history[-1]["content"]

        if use_history:
            logger.debug(
                "Note: Gemini request uses only the latest message, not full history"
            )

        response = gemini_model.generate_content(user_message)

        return response.text

    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.debug("Conversation history cleared")