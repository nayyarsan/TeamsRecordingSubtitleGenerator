"""LLM integration module."""

from .ollama import OllamaClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from ..utils import get_config

__all__ = ["OllamaClient", "OpenAIClient", "AnthropicClient", "get_llm_client"]


def get_llm_client(provider: str = "ollama"):
    """Return the appropriate LLM client based on provider name.

    Falls back to OllamaClient if the provider requires an external API
    and ``privacy.allow_external_api`` is False.

    Args:
        provider: One of ``"ollama"``, ``"openai"``, or ``"anthropic"``.

    Returns:
        An LLM client instance.
    """
    config = get_config()
    privacy = config.get("privacy", default={})
    allow_external = privacy.get("allow_external_api", False)

    if provider == "openai":
        if not allow_external:
            return OllamaClient()
        return OpenAIClient()

    if provider == "anthropic":
        if not allow_external:
            return OllamaClient()
        return AnthropicClient()

    # Default / unknown → local Ollama
    return OllamaClient()
