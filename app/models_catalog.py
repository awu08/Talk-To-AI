"""Models Catalog: The AI models offered in Settings, with plain-English descriptions.

Each provider has a short list of current models so users can pick one
instead of looking up model IDs. Anything not listed can still be used via
"Other…" in Settings.

Model lineups change every few months. To update, edit MODELS below; the
Settings dropdown, the default for each provider and the descriptions all
come from here. Sources (checked October 2026):
    Claude:  https://platform.claude.com/docs/en/models/overview
    ChatGPT: https://developers.openai.com/api/docs/models
    Gemini:  https://ai.google.dev/gemini-api/docs/models
             https://ai.google.dev/gemini-api/docs/pricing (free tier)

Author: Allen Wu
Version: 1.1.0
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ModelInfo:
    """One choice in the model dropdown."""

    id: str           # exact API model ID
    name: str         # display name
    tags: str         # short summary shown in the dropdown, e.g. "Free · Fastest"
    description: str  # one sentence shown under the dropdown
    default: bool = False  # the provider's pre-selected choice


MODELS: Dict[str, List[ModelInfo]] = {
    "Claude": [
        ModelInfo("claude-haiku-5-5", "Claude Haiku 5.5", "Fastest · Cheapest",
                  "Quickest replies at the lowest cost. Great for everyday quick questions."),
        ModelInfo("claude-sonnet-5-5", "Claude Sonnet 5.5", "Fast · Smart",
                  "The best balance of speed and intelligence. A good default for voice.",
                  default=True),
        ModelInfo("claude-opus-5-5", "Claude Opus 5.5", "Smarter · Slower",
                  "Stronger reasoning for harder questions, with a little more wait."),
        ModelInfo("claude-fable-5-1", "Claude Fable 5.1", "Deepest thinking · Slowest",
                  "Anthropic's most capable model, for the hardest problems. Slowest "
                  "and most expensive."),
    ],
    "ChatGPT": [
        ModelInfo("gpt-6-luna", "GPT-6 Luna", "Fastest · Cheapest",
                  "OpenAI's most efficient model. Quick, low-cost answers."),
        ModelInfo("gpt-6.1-sol", "GPT-6.1 Sol", "Fast · Smart",
                  "Close to OpenAI's best at a much lower price. A good default.",
                  default=True),
        ModelInfo("gpt-6-astra", "GPT-6 Astra", "Deepest thinking · Slowest",
                  "OpenAI's most capable model, for complex reasoning. Slower and "
                  "more expensive."),
    ],
    "Gemini": [
        ModelInfo("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite", "Free · Fastest",
                  "Google's fastest, lowest-cost model. Included in the free tier."),
        ModelInfo("gemini-3.6-flash", "Gemini 3.6 Flash", "Free · Balanced",
                  "A good balance of speed and smarts for everyday questions. "
                  "Included in the free tier.", default=True),
        ModelInfo("gemini-3.8-flash", "Gemini 3.8 Flash", "Free · Smartest Flash",
                  "Google's newest and most capable Flash model. Included in the free tier."),
        ModelInfo("gemini-3.1-pro-preview", "Gemini 3.1 Pro (preview)", "Paid · Deep thinking",
                  "Google's strongest reasoning model, for complex problems. Preview, "
                  "and not in the free tier."),
    ],
}

# Where to look up other model IDs (shown next to "Other…")
MODEL_DOCS: Dict[str, str] = {
    "Claude": "https://platform.claude.com/docs/en/models/overview",
    "ChatGPT": "https://developers.openai.com/api/docs/models",
    "Gemini": "https://ai.google.dev/gemini-api/docs/models",
}


def models_for(provider: str) -> List[ModelInfo]:
    """The listed models for a provider (empty for an unknown provider)."""
    return MODELS.get(provider, [])


def default_model(provider: str) -> Optional[ModelInfo]:
    """The pre-selected model for a provider, or None if the provider is unknown."""
    models = models_for(provider)
    for model in models:
        if model.default:
            return model
    return models[0] if models else None


def find_model(provider: str, model_id: str) -> Optional[ModelInfo]:
    """The catalog entry for a model ID, or None if it isn't listed (a custom model)."""
    for model in models_for(provider):
        if model.id == model_id:
            return model
    return None


def display_name(provider: str, model_id: str) -> str:
    """A friendly name for a model ID, falling back to the ID itself."""
    model = find_model(provider, model_id)
    return model.name if model else model_id
