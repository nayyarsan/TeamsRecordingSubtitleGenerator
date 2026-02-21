"""OpenAI client for LLM-assisted name extraction."""

import json
import os
from typing import List, Optional

from ..utils import get_logger, get_config

logger = get_logger(__name__)

# Import at call-site to keep the package importable without openai installed
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


class OpenAIClient:
    """Client for OpenAI-hosted models."""

    def __init__(self, model: Optional[str] = None):
        config = get_config()
        llm_config = config.get("naming", default={}).get("llm", {})
        self.model = model or llm_config.get("model", "gpt-4o-mini")
        self.temperature = llm_config.get("temperature", 0.0)

    def is_available(self) -> bool:
        """Return True if OPENAI_API_KEY is set."""
        return bool(os.environ.get("OPENAI_API_KEY"))

    def list_models(self) -> List[str]:
        """Return the configured model name."""
        return [self.model]

    def extract_names(self, text: str) -> List[dict]:
        """Use OpenAI to extract speaker names from transcript text."""
        if OpenAI is None:
            logger.error("openai package not installed")
            return []

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, skipping name extraction")
            return []

        prompt = (
            "Extract all person names mentioned in this meeting transcript excerpt. "
            "Return a JSON array where each element has 'name' (the person's full name) "
            "and 'context' (the sentence where the name appears). "
            "Only return the JSON array, nothing else.\n\n"
            f"Transcript:\n{text[:3000]}"
        )

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )
            response_text = response.choices[0].message.content or ""
            return self._parse_names_response(response_text)
        except Exception as e:
            logger.error(f"OpenAI name extraction failed: {e}")
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
            logger.warning("Failed to parse OpenAI response as JSON")
            return []
