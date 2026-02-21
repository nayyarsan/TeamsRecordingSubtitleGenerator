"""Ollama REST client for local LLM inference."""

import json
import urllib.request
import urllib.error
from typing import List, Optional

from ..utils import get_logger, get_config

logger = get_logger(__name__)


class OllamaClient:
    """Client for interacting with a local Ollama instance."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
    ):
        config = get_config()
        llm_config = config.get("naming", default={}).get("llm", {})

        self.endpoint = (
            endpoint or llm_config.get("endpoint", "http://localhost:11434")
        ).rstrip("/")
        self.model = model or llm_config.get("model", "llama3")
        self.temperature = llm_config.get("temperature", 0.0)

    def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Return list of available model names."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    def extract_names(self, text: str) -> List[dict]:
        """
        Use the LLM to extract speaker names from transcript text.

        Returns list of dicts: [{"name": "...", "confidence": 0.9, "context": "..."}]
        """
        prompt = (
            "Extract all person names mentioned in this meeting transcript excerpt. "
            "Return a JSON array where each element has 'name' (the person's full name) "
            "and 'context' (the sentence where the name appears). "
            "Only return the JSON array, nothing else.\n\n"
            f"Transcript:\n{text[:3000]}"
        )

        try:
            payload = json.dumps(
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": self.temperature},
                }
            ).encode()

            req = urllib.request.Request(
                f"{self.endpoint}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                response_text = result.get("response", "")

            # Parse JSON from response
            return self._parse_names_response(response_text)

        except Exception as e:
            logger.error(f"Ollama name extraction failed: {e}")
            return []

    def _parse_names_response(self, response_text: str) -> List[dict]:
        """Parse the LLM response to extract name suggestions."""
        # Try to find JSON array in response
        text = response_text.strip()

        # Find the JSON array boundaries
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
            logger.warning("Failed to parse Ollama response as JSON")
            return []
