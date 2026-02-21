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

    # Must mock allow_external_api=True because config.yaml defaults it to false
    with patch("src.llm.get_config") as mock_cfg:
        cfg = MagicMock()
        cfg.get.side_effect = lambda key, default=None: (
            {"llm": {"provider": "openai"}}
            if key == "naming"
            else {"allow_external_api": True}
            if key == "privacy"
            else default
        )
        mock_cfg.return_value = cfg
        client = get_llm_client("openai")
    assert isinstance(client, OpenAIClient)


def test_factory_returns_anthropic_client():
    from src.llm import get_llm_client
    from src.llm.anthropic_client import AnthropicClient

    with patch("src.llm.get_config") as mock_cfg:
        cfg = MagicMock()
        cfg.get.side_effect = lambda key, default=None: (
            {"llm": {"provider": "anthropic"}}
            if key == "naming"
            else {"allow_external_api": True}
            if key == "privacy"
            else default
        )
        mock_cfg.return_value = cfg
        client = get_llm_client("anthropic")
    assert isinstance(client, AnthropicClient)


def test_factory_falls_back_to_ollama_when_external_api_disabled():
    from src.llm import get_llm_client
    from src.llm.ollama import OllamaClient

    with patch("src.llm.get_config") as mock_cfg:
        cfg = MagicMock()
        cfg.get.side_effect = lambda key, default=None: (
            {"llm": {"provider": "openai"}}
            if key == "naming"
            else {"allow_external_api": False}
            if key == "privacy"
            else default
        )
        mock_cfg.return_value = cfg
        client = get_llm_client("openai")
    assert isinstance(client, OllamaClient)


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
