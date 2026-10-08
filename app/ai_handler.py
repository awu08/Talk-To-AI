"""AI Handler: Routes prompts to multiple LLM providers.

This module provides a unified interface for communicating with multiple AI providers
(Claude, ChatGPT, Gemini). It handles API routing, maintains conversation history,
and abstracts away provider-specific implementation details.

The AIHandler class implements a consistent API regardless of the underlying provider,
allowing users to switch between Claude, ChatGPT, and Gemini seamlessly through
configuration settings.

Author: Allen Wu
Version: 1.0.0
"""

import logging
from typing import List, Dict, Optional, Literal
from anthropic import Anthropic
from openai import OpenAI
import google.generativeai as genai

logger = logging.getLogger(__name__)

# API configuration defaults
DEFAULT_MAX_TOKENS: int = 1024

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
    """Unified interface for communicating with multiple AI API providers.
    
    This class abstracts the differences between Claude, ChatGPT, and Gemini APIs,
    providing a consistent interface for sending prompts and maintaining conversation
    history. It handles provider routing, error handling, and API key management.
    
    Attributes:
        config (ConfigManager): Configuration manager for API keys and settings
        conversation_history (List[Dict]): Maintains conversation context across requests
            Each entry is {"role": "user"|"assistant", "content": str}
        PROVIDERS (set): Set of supported AI providers for validation
        
    Example:
        >>> from app.config import ConfigManager
        >>> config = ConfigManager()
        >>> handler = AIHandler(config)
        >>> response = handler.send_prompt("What is 2+2?")
        >>> print(response)
        'The answer is 4.'
    """

    # Supported providers for validation
    PROVIDERS: set = {"Claude", "ChatGPT", "Gemini"}

    def __init__(self, config) -> None:
        """Initialize AI handler with configuration manager.
        
        Args:
            config (ConfigManager): Configuration manager instance that provides
                API keys, model names, and provider selection
                
        Raises:
            AttributeError: If config doesn't have required get() method
        """
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self._validate_config()
        logger.debug("AIHandler initialized")

    def _validate_config(self) -> None:
        """Validate that required API configuration is present.
        
        Checks if the configured provider is supported. Logs a warning if an
        unknown provider is selected, but does not raise an exception (validation
        happens at send_prompt time when the provider is actually used).
        
        Side Effects:
            - Logs warning if provider is not in SUPPORTED_PROVIDERS
        """
        provider: str = self.config.get("api", "provider")
        if provider and provider not in self.PROVIDERS:
            logger.warning(
                f"Unknown provider '{provider}'. Supported: {self.PROVIDERS}"
            )

    def send_prompt(
        self, 
        user_text: str, 
        use_history: bool = True
    ) -> str:
        """Send a prompt to the configured AI provider and get a response.
        
        Orchestrates the full request pipeline: validation → history management →
        provider routing → response handling. Automatically maintains conversation
        history for multi-turn interactions.
        
        Args:
            user_text (str): The user's prompt/question to send to the AI
            use_history (bool): Whether to include conversation history in the request.
                Defaults to True. Set to False for stateless requests.
                
        Returns:
            str: The AI provider's response text
            
        Raises:
            ValueError: If API key or model is not configured
            ValueError: If provider is unknown or unsupported
            
        Side Effects:
            - Appends user message and AI response to conversation_history
            - Logs debug and error information
            
        Example:
            >>> response = handler.send_prompt("Explain quantum computing")
            >>> # response contains the AI's explanation
        """
        provider: str = self.config.get("api", "provider")
        model: str = self.config.get("api", "model")
        api_key: str = self.config.get("api", "api_key")

        # Validate configuration before making API calls
        if not api_key:
            logger.error("API key not configured")
            raise ValueError("API key is required but not configured")

        if not model:
            logger.error("Model not configured")
            raise ValueError("Model is required but not configured")

        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        logger.debug(f"User prompt added to history. Total messages: {len(self.conversation_history)}")

        try:
            # Route request to appropriate provider based on configuration
            if provider == "Claude":
                response = self._send_to_claude(model, api_key, use_history)
            elif provider == "ChatGPT":
                response = self._send_to_chatgpt(model, api_key, use_history)
            elif provider == "Gemini":
                response = self._send_to_gemini(model, api_key, use_history)
            else:
                raise ValueError(f"Unknown provider: {provider}")

            # Add AI response to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})
            logger.debug(
                f"Response from {provider}: {response[:50]}..." 
                if len(response) > 50 
                else f"Response from {provider}: {response}"
            )
            
            return response

        except Exception as e:
            # Drop the unanswered question so the history stays user/assistant pairs
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            logger.error(f"Error communicating with {provider}: {e}", exc_info=True)
            raise

    def _send_to_claude(
        self, 
        model: str, 
        api_key: str, 
        use_history: bool
    ) -> str:
        """Send request to Claude (Anthropic) API.
        
        Uses the Anthropic SDK to communicate with Claude models. Supports
        multi-turn conversations through message history.
        
        Args:
            model (str): The Claude model identifier (e.g., "claude-3-5-sonnet-20241022")
            api_key (str): Anthropic API key for authentication
            use_history (bool): Whether to include conversation history in the request
            
        Returns:
            str: The Claude response text
            
        Raises:
            Exception: If Anthropic API request fails (authentication, rate limit, etc.)
        """
        try:
            client = Anthropic(api_key=api_key)

            # Select message history based on use_history flag
            messages: List[Dict[str, str]] = (
                self.conversation_history
                if use_history
                else [self.conversation_history[-1]]
            )

            response = client.messages.create(
                model=model,
                max_tokens=DEFAULT_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages
            )

            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise

    def _send_to_chatgpt(
        self, 
        model: str, 
        api_key: str, 
        use_history: bool
    ) -> str:
        """Send request to ChatGPT (OpenAI) API.
        
        Uses the OpenAI SDK to communicate with ChatGPT models. Supports
        multi-turn conversations through message history.
        
        Args:
            model (str): The ChatGPT model identifier (e.g., "gpt-4", "gpt-3.5-turbo")
            api_key (str): OpenAI API key for authentication
            use_history (bool): Whether to include conversation history in the request
            
        Returns:
            str: The ChatGPT response text
            
        Raises:
            Exception: If OpenAI API request fails (authentication, rate limit, etc.)
        """
        try:
            client = OpenAI(api_key=api_key)

            # Select message history based on use_history flag
            messages: List[Dict[str, str]] = (
                self.conversation_history
                if use_history
                else [self.conversation_history[-1]]
            )

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                max_tokens=DEFAULT_MAX_TOKENS
            )

            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}", exc_info=True)
            raise

    def _send_to_gemini(
        self, 
        model: str, 
        api_key: str, 
        use_history: bool
    ) -> str:
        """Send request to Gemini (Google) API.
        
        Uses the Google Generative AI SDK to communicate with Gemini models,
        sending the conversation history (roles mapped to Gemini's "user" /
        "model") and the shared system prompt.

        Args:
            model (str): The Gemini model identifier (e.g., "gemini-2.0-flash")
            api_key (str): Google Generative AI API key for authentication
            use_history (bool): If True, include previous messages for context

        Returns:
            str: The Gemini response text

        Raises:
            Exception: If Google API request fails (authentication, rate limit, etc.)
        """
        try:
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel(model, system_instruction=SYSTEM_PROMPT)

            # Gemini calls the assistant role "model"
            messages: List[Dict[str, str]] = (
                self.conversation_history
                if use_history
                else [self.conversation_history[-1]]
            )
            contents = [
                {"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [m["content"]]}
                for m in messages
            ]
            response = gemini_model.generate_content(contents)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            raise

    def clear_history(self) -> None:
        """Clear the conversation history.
        
        Resets conversation_history to empty list, effectively starting a fresh
        conversation with the AI. Useful when the user wants to change topics or
        reset context.
        
        Side Effects:
            - Clears conversation_history list
            - Logs debug message indicating history was cleared
            
        Example:
            >>> handler.clear_history()
            >>> handler.send_prompt("New topic: Python")
            >>> # This request won't reference any previous messages
        """
        self.conversation_history = []
        logger.info("Conversation history cleared by user")