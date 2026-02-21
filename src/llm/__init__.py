"""LLM integration module."""

from .ollama import OllamaClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from ..utils import get_config, get_logger

logger = get_logger(__name__)

__all__ = ["OllamaClient", "OpenAIClient", "AnthropicClient", "get_llm_client"]


def get_llm_client(provider: str = None):
    """Return the appropriate LLM client based on provider name.

    Falls back to OllamaClient if the provider requires an external API
    and ``privacy.allow_external_api`` is False.

    Args:
        provider: One of ``"ollama"``, ``"openai"``, or ``"anthropic"``.
                  If None, reads naming.llm.provider from config.yaml.

    Returns:
        An LLM client instance.
    """
    config = get_config()
    llm_config = config.get("naming", default={}).get("llm", {})
    provider = provider or llm_config.get("provider", "ollama")

    if provider in ("openai", "anthropic"):
        allow_external = config.get("privacy", default={}).get(
            "allow_external_api", False
        )
        if not allow_external:
            logger.warning(
                f"Provider '{provider}' requires external API calls but "
                "privacy.allow_external_api is false. Falling back to ollama."
            )
            return OllamaClient()

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    else:
        return OllamaClient()
