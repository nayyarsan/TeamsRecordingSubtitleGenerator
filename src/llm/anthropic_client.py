"""Anthropic client for LLM-assisted name extraction."""

import json
import os
from typing import List, Optional

from ..utils import get_logger, get_config

logger = get_logger(__name__)

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore


class AnthropicClient:
    """Client for Anthropic Claude models."""

    def __init__(self, model: Optional[str] = None):
        config = get_config()
        llm_config = config.get("naming", default={}).get("llm", {})
        self.model = model or llm_config.get("model", "claude-haiku-4-5-20251001")
        self.temperature = llm_config.get("temperature", 0.0)

    def is_available(self) -> bool:
        """Return True if ANTHROPIC_API_KEY is set."""
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def list_models(self) -> List[str]:
        """Return the configured model name."""
        return [self.model]

    def extract_names(self, text: str) -> List[dict]:
        """Use Anthropic Claude to extract speaker names from transcript text."""
        if Anthropic is None:
            logger.error("anthropic package not installed")
            return []

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping name extraction")
            return []

        prompt = (
            "Extract all person names mentioned in this meeting transcript excerpt. "
            "Return a JSON array where each element has 'name' (the person's full name) "
            "and 'context' (the sentence where the name appears). "
            "Only return the JSON array, nothing else.\n\n"
            f"Transcript:\n{text[:3000]}"
        )

        try:
            client = Anthropic(api_key=api_key)
            message = client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text if message.content else ""
            return self._parse_names_response(response_text)
        except Exception as e:
            logger.error(f"Anthropic name extraction failed: {e}")
            return []

    def _parse_names_response(self, response_text: str) -> List[dict]:
        """Parse JSON array of names from LLM response."""
        text = response_text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return []
        try:
            names = json.loads(text[start : end + 1])
            result = []
            for item in names:
                if isinstance(item, dict) and "name" in item:
                    result.append(
                        {
                            "name": item["name"],
                            "confidence": 0.9,
                            "context": item.get("context", ""),
                        }
                    )
                elif isinstance(item, str):
                    result.append({"name": item, "confidence": 0.9, "context": ""})
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse Anthropic response as JSON")
            return []
