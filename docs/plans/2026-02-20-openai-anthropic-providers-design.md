# Design: OpenAI and Anthropic LLM Providers

**Date:** 2026-02-20
**Status:** Approved

## Problem

`config.yaml` already exposes `naming.llm.provider` with values `"ollama"`, `"openai"`, and `"anthropic"`, and `requirements.txt` already lists both `openai` and `anthropic` packages. However, `src/naming/extractor.py` hardcodes a check for `provider == "ollama"`, so any other provider silently does nothing. `src/api.py` also directly instantiates `OllamaClient`, ignoring the configured provider entirely.

## Goal

Implement `OpenAIClient` and `AnthropicClient` with the same interface as `OllamaClient`, and wire everything together through a factory function so the configured provider is actually used.

## Interface Contract

All LLM clients implement the same three methods:

```python
def is_available() -> bool:
    """Return True if the provider is reachable and credentials are present."""

def extract_names(text: str) -> List[dict]:
    """Extract speaker names from transcript text.
    Returns: [{"name": str, "confidence": float, "context": str}]
    """

def list_models() -> List[str]:
    """Return available model names (empty list if not applicable)."""
```

## Files Changed

### New files

- **`src/llm/openai.py`** — `OpenAIClient`
  Uses the `openai` SDK. Reads `OPENAI_API_KEY` from env. `is_available()` checks the key is set and the API responds. `list_models()` returns the model from config. Prompt is identical in structure to `OllamaClient.extract_names()`.

- **`src/llm/anthropic.py`** — `AnthropicClient`
  Uses the `anthropic` SDK. Reads `ANTHROPIC_API_KEY` from env. Same interface. Uses `messages.create()` with the configured model (default: `claude-haiku-4-5-20251001`).

### Modified files

- **`src/llm/__init__.py`**
  Export `OpenAIClient`, `AnthropicClient`, and a new `get_llm_client(provider=None)` factory. The factory reads `naming.llm.provider` from config if `provider` is not passed, and returns the appropriate client instance.

- **`src/naming/extractor.py`**
  Replace the `if self.llm_provider == "ollama":` branch in `_extract_names_with_llm()` with a call to `get_llm_client(self.llm_provider)`. Remove the direct `OllamaClient` import.

- **`src/api.py`**
  - `/api/suggest-names`: replace `OllamaClient()` with `get_llm_client()`
  - `/api/ollama/status` → generalize to check configured provider; keep route path for frontend compatibility
  - `/api/ollama/models` → same; return empty list for non-Ollama providers

## Factory Design

```python
def get_llm_client(provider: str = None):
    config = get_config()
    llm_config = config.get("naming", default={}).get("llm", {})
    provider = provider or llm_config.get("provider", "ollama")

    if provider == "openai":
        return OpenAIClient()
    elif provider == "anthropic":
        return AnthropicClient()
    else:
        return OllamaClient()
```

Future providers require only: (1) a new file, (2) one `elif` line here.

## Privacy / Credentials

- API keys come from environment variables only (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Never from `config.yaml`.
- Cloud providers are only invoked when explicitly configured. Default remains `"ollama"` (fully local).
- The `privacy.allow_external_api` config flag should be checked before calling cloud providers; log a warning and fall back to Ollama if it is `false`.

## Out of Scope

- No changes to the pipeline stages (audio, video, fusion, output, visualization).
- No new API routes or frontend changes beyond making the existing suggest-names flow work with all providers.
- No streaming responses — all providers use request/response for the name extraction use case.
