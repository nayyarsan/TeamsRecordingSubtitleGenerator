# OpenAI and Anthropic LLM Providers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `OpenAIClient` and `AnthropicClient` with the same interface as `OllamaClient`, wire them through a `get_llm_client()` factory, and update `extractor.py` and `api.py` to use it.

**Architecture:** Each new client lives in its own file under `src/llm/` and implements `is_available()`, `extract_names()`, and `list_models()`. A factory function in `src/llm/__init__.py` reads the configured provider and returns the right client. Privacy guard: cloud providers fall back to Ollama if `privacy.allow_external_api` is `false`.

**Tech Stack:** `openai` SDK, `anthropic` SDK (both already in `requirements.txt`), `unittest.mock` for tests, `pytest`.

---

### Task 1: Create test directory and write failing tests for the factory and OpenAIClient

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/llm/__init__.py`
- Create: `tests/llm/test_clients.py`

**Step 1: Create the test directories**

```bash
mkdir -p tests/llm
touch tests/__init__.py tests/llm/__init__.py
```

**Step 2: Write the failing tests**

Create `tests/llm/test_clients.py`:

```python
"""Tests for LLM client implementations and factory."""

import os
from unittest.mock import patch, MagicMock

import pytest


# ── Factory ──────────────────────────────────────────────────────────────────

def test_factory_returns_ollama_for_unknown_provider():
    from src.llm import get_llm_client
    from src.llm.ollama import OllamaClient
    client = get_llm_client("unknown")
    assert isinstance(client, OllamaClient)


def test_factory_returns_openai_client():
    from src.llm import get_llm_client
    from src.llm.openai_client import OpenAIClient
    client = get_llm_client("openai")
    assert isinstance(client, OpenAIClient)


def test_factory_returns_anthropic_client():
    from src.llm import get_llm_client
    from src.llm.anthropic_client import AnthropicClient
    client = get_llm_client("anthropic")
    assert isinstance(client, AnthropicClient)


# ── OpenAIClient.is_available ────────────────────────────────────────────────

def test_openai_is_available_when_key_set():
    from src.llm.openai_client import OpenAIClient
    client = OpenAIClient(model="gpt-4o-mini")
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        assert client.is_available() is True


def test_openai_not_available_when_key_missing():
    from src.llm.openai_client import OpenAIClient
    client = OpenAIClient(model="gpt-4o-mini")
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        assert client.is_available() is False


# ── OpenAIClient.extract_names ───────────────────────────────────────────────

def test_openai_extract_names_returns_parsed_list():
    from src.llm.openai_client import OpenAIClient
    client = OpenAIClient(model="gpt-4o-mini")

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        '[{"name": "John Smith", "context": "Hi I am John Smith"}]'
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
        with patch("src.llm.openai_client.OpenAI") as mock_cls:
            mock_cls.return_value.chat.completions.create.return_value = mock_response
            result = client.extract_names("Hi I am John Smith from engineering")

    assert len(result) == 1
    assert result[0]["name"] == "John Smith"
    assert "confidence" in result[0]
    assert "context" in result[0]


def test_openai_extract_names_returns_empty_when_no_key():
    from src.llm.openai_client import OpenAIClient
    client = OpenAIClient(model="gpt-4o-mini")
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        result = client.extract_names("Hi I am John Smith")
    assert result == []


# ── AnthropicClient.is_available ─────────────────────────────────────────────

def test_anthropic_is_available_when_key_set():
    from src.llm.anthropic_client import AnthropicClient
    client = AnthropicClient(model="claude-haiku-4-5-20251001")
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        assert client.is_available() is True


def test_anthropic_not_available_when_key_missing():
    from src.llm.anthropic_client import AnthropicClient
    client = AnthropicClient(model="claude-haiku-4-5-20251001")
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        assert client.is_available() is False


# ── AnthropicClient.extract_names ────────────────────────────────────────────

def test_anthropic_extract_names_returns_parsed_list():
    from src.llm.anthropic_client import AnthropicClient
    client = AnthropicClient(model="claude-haiku-4-5-20251001")

    mock_content = MagicMock()
    mock_content.text = '[{"name": "Jane Doe", "context": "This is Jane Doe speaking"}]'
    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
        with patch("src.llm.anthropic_client.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            result = client.extract_names("This is Jane Doe speaking")

    assert len(result) == 1
    assert result[0]["name"] == "Jane Doe"
    assert "confidence" in result[0]


def test_anthropic_extract_names_returns_empty_when_no_key():
    from src.llm.anthropic_client import AnthropicClient
    client = AnthropicClient(model="claude-haiku-4-5-20251001")
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        result = client.extract_names("This is Jane Doe speaking")
    assert result == []
```

**Step 3: Run tests to confirm they fail**

```bash
pytest tests/llm/test_clients.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `get_llm_client`, `OpenAIClient`, `AnthropicClient` don't exist yet.

---

### Task 2: Implement `OpenAIClient`

**Files:**
- Create: `src/llm/openai_client.py`

**Step 1: Create the file**

```python
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
            names = json.loads(text[start:end + 1])
            result = []
            for item in names:
                if isinstance(item, dict) and "name" in item:
                    result.append({
                        "name": item["name"],
                        "confidence": 0.9,
                        "context": item.get("context", ""),
                    })
                elif isinstance(item, str):
                    result.append({"name": item, "confidence": 0.9, "context": ""})
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI response as JSON")
            return []
```

**Step 2: Run the OpenAI tests**

```bash
pytest tests/llm/test_clients.py -k "openai" -v
```

Expected: all `test_openai_*` tests pass.

**Step 3: Commit**

```bash
git add src/llm/openai_client.py tests/llm/test_clients.py tests/llm/__init__.py tests/__init__.py
git commit -m "feat: add OpenAIClient for LLM name extraction"
```

---

### Task 3: Implement `AnthropicClient`

**Files:**
- Create: `src/llm/anthropic_client.py`

**Step 1: Create the file**

```python
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
            names = json.loads(text[start:end + 1])
            result = []
            for item in names:
                if isinstance(item, dict) and "name" in item:
                    result.append({
                        "name": item["name"],
                        "confidence": 0.9,
                        "context": item.get("context", ""),
                    })
                elif isinstance(item, str):
                    result.append({"name": item, "confidence": 0.9, "context": ""})
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse Anthropic response as JSON")
            return []
```

**Step 2: Run the Anthropic tests**

```bash
pytest tests/llm/test_clients.py -k "anthropic" -v
```

Expected: all `test_anthropic_*` tests pass.

**Step 3: Commit**

```bash
git add src/llm/anthropic_client.py
git commit -m "feat: add AnthropicClient for LLM name extraction"
```

---

### Task 4: Add `get_llm_client` factory to `src/llm/__init__.py`

**Files:**
- Modify: `src/llm/__init__.py`

**Step 1: Replace the file contents**

```python
"""LLM integration module."""

from .ollama import OllamaClient
from .openai_client import OpenAIClient
from .anthropic_client import AnthropicClient
from ..utils import get_logger, get_config

logger = get_logger(__name__)

__all__ = ["OllamaClient", "OpenAIClient", "AnthropicClient", "get_llm_client"]


def get_llm_client(provider: str = None):
    """Return the configured LLM client instance.

    Args:
        provider: Override the config provider. One of "ollama", "openai", "anthropic".
                  If None, reads naming.llm.provider from config.yaml.

    Returns:
        An LLM client with is_available(), extract_names(), and list_models() methods.
    """
    config = get_config()
    llm_config = config.get("naming", default={}).get("llm", {})
    provider = provider or llm_config.get("provider", "ollama")

    if provider in ("openai", "anthropic"):
        allow_external = config.get("privacy", default={}).get("allow_external_api", False)
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
```

**Step 2: Run all factory tests**

```bash
pytest tests/llm/test_clients.py -v
```

Expected: all tests pass.

**Step 3: Commit**

```bash
git add src/llm/__init__.py
git commit -m "feat: add get_llm_client factory with privacy guard"
```

---

### Task 5: Update `src/naming/extractor.py` to use the factory

**Files:**
- Modify: `src/naming/extractor.py`

The only change is in `_extract_names_with_llm()`. Currently:

```python
# Line 80 in extractor.py — BEFORE
if self.llm_enabled and self.llm_provider == "ollama":
    llm_candidates = self._extract_names_with_llm(intro_segments)
```

and inside `_extract_names_with_llm()`:

```python
# Lines 327-328 — BEFORE
from ..llm import OllamaClient
client = OllamaClient(model=self.llm_model)
```

**Step 1: Update the provider guard in `extract_names()`**

In `src/naming/extractor.py`, find the line:

```python
        if self.llm_enabled and self.llm_provider == "ollama":
```

Replace it with:

```python
        if self.llm_enabled:
```

**Step 2: Update `_extract_names_with_llm()` to use the factory**

Find these two lines inside `_extract_names_with_llm()`:

```python
            from ..llm import OllamaClient
            client = OllamaClient(model=self.llm_model)
```

Replace with:

```python
            from ..llm import get_llm_client
            client = get_llm_client(self.llm_provider)
```

Also remove the `if not client.is_available():` block's provider-specific wording — it's already provider-agnostic. The block stays as-is.

**Step 3: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. No regressions.

**Step 4: Commit**

```bash
git add src/naming/extractor.py
git commit -m "feat: use get_llm_client factory in SpeakerNamer"
```

---

### Task 6: Update `src/api.py` to use the factory

**Files:**
- Modify: `src/api.py`

Three places to update:

**Step 1: Update `/api/suggest-names` endpoint (lines ~272-278)**

Find:

```python
        try:
            from .llm import OllamaClient
            client = OllamaClient()
            if not client.is_available():
                return {"suggestions": [], "error": "Ollama is not available"}
```

Replace with:

```python
        try:
            from .llm import get_llm_client
            client = get_llm_client()
            if not client.is_available():
                return {"suggestions": [], "error": "LLM provider is not available"}
```

**Step 2: Update `/api/ollama/status` endpoint (lines ~327-332)**

Find:

```python
        try:
            from .llm import OllamaClient
            client = OllamaClient()
            available = client.is_available()
            return {"available": available}
```

Replace with:

```python
        try:
            from .llm import get_llm_client
            client = get_llm_client()
            available = client.is_available()
            return {"available": available}
```

**Step 3: Update `/api/ollama/models` endpoint (lines ~338-345)**

Find:

```python
        try:
            from .llm import OllamaClient
            client = OllamaClient()
            if not client.is_available():
                return {"models": [], "available": False}
            models = client.list_models()
            return {"models": models, "available": True}
```

Replace with:

```python
        try:
            from .llm import get_llm_client
            client = get_llm_client()
            if not client.is_available():
                return {"models": [], "available": False}
            models = client.list_models()
            return {"models": models, "available": True}
```

**Step 4: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass.

**Step 5: Run linting**

```bash
black --check src/
flake8 src/ --max-line-length=100 --extend-ignore=E203,W503,W293,E501
```

Fix any issues with `black src/` if needed.

**Step 6: Commit**

```bash
git add src/api.py
git commit -m "feat: update api.py to use get_llm_client factory"
```

---

### Task 7: Final verification

**Step 1: Run the full test suite with coverage**

```bash
pytest tests/ --cov=src --cov-report=term-missing -v
```

Expected: all tests pass.

**Step 2: Verify the config round-trip manually**

```bash
python -c "
from src.llm import get_llm_client
c = get_llm_client('openai')
print(type(c).__name__, c.is_available())
c2 = get_llm_client('anthropic')
print(type(c2).__name__, c2.is_available())
c3 = get_llm_client('ollama')
print(type(c3).__name__)
"
```

Expected output (no API keys set):
```
OpenAIClient False
AnthropicClient False
OllamaClient
```

**Step 3: Final commit**

```bash
git add -A
git commit -m "chore: implement OpenAI and Anthropic LLM providers"
```
