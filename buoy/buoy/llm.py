"""
Generic LLM provider for honeypot response generation.

LLM_ENABLED=true activates generation. Without it the module returns ""
immediately and cache threads exit at startup — zero CPU overhead.

Supported providers (LLM_PROVIDER):
  ollama            — local Ollama server (default)
  openai            — OpenAI API (gpt-4o-mini, gpt-4o, o1, …)
  anthropic         — Anthropic API (claude-haiku-4-5, claude-sonnet-4-6, …)
  openai_compatible — any OpenAI-spec endpoint (Groq, Together, Mistral, Fireworks, …)

Required env vars per provider:
  ollama:            LLM_BASE_URL (default http://ollama:11434)
  openai:            LLM_API_KEY
  anthropic:         LLM_API_KEY
  openai_compatible: LLM_BASE_URL, LLM_API_KEY (if the endpoint requires one)

Common:
  LLM_MODEL   — model name (provider-specific default used if unset)
  LLM_ENABLED — must be "true" to enable
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get("LLM_ENABLED", "").lower() == "true"
_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama").lower()
_API_KEY = os.environ.get("LLM_API_KEY", "")
_MODEL = os.environ.get("LLM_MODEL", "")
_BASE_URL = os.environ.get("LLM_BASE_URL", "")

_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "ollama": {
        "base_url": "http://ollama:11434",
        "model": "gemma3:1b",
    },
    "openai": {
        "base_url": "https://api.openai.com",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "model": "claude-haiku-4-5-20251001",
    },
    "openai_compatible": {
        "base_url": "",
        "model": "",
    },
}


def _resolve(key: str) -> str:
    if key == "base_url":
        return _BASE_URL or _PROVIDER_DEFAULTS.get(_PROVIDER, {}).get("base_url", "")
    if key == "model":
        return _MODEL or _PROVIDER_DEFAULTS.get(_PROVIDER, {}).get("model", "")
    return ""


def _post(url: str, payload: bytes, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())  # type: ignore[no-any-return]


def _generate_ollama(prompt: str, max_tokens: int) -> str:
    base = _resolve("base_url").rstrip("/")
    url = f"{base}/api/generate"
    payload = json.dumps(
        {
            "model": _resolve("model"),
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.9,
                "top_p": 0.95,
            },
        }
    ).encode()
    body = _post(url, payload, {"Content-Type": "application/json"})
    return str(body.get("response", "")).strip()


def _generate_openai_compat(prompt: str, max_tokens: int) -> str:
    base = _resolve("base_url").rstrip("/")
    url = f"{base}/v1/chat/completions"
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["Authorization"] = f"Bearer {_API_KEY}"
    payload = json.dumps(
        {
            "model": _resolve("model"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.9,
            "top_p": 0.95,
        }
    ).encode()
    body = _post(url, payload, headers)
    choices = body.get("choices", [])
    if not choices:
        return ""
    return str(choices[0].get("message", {}).get("content", "")).strip()


def _generate_anthropic(prompt: str, max_tokens: int) -> str:
    base = _resolve("base_url").rstrip("/")
    url = f"{base}/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": _API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = json.dumps(
        {
            "model": _resolve("model"),
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    body = _post(url, payload, headers)
    content = body.get("content", [])
    if not content:
        return ""
    return str(content[0].get("text", "")).strip()


def generate(prompt: str, max_tokens: int = 256) -> str:
    if not _ENABLED:
        return ""

    try:
        if _PROVIDER == "ollama":
            return _generate_ollama(prompt, max_tokens)
        if _PROVIDER == "anthropic":
            return _generate_anthropic(prompt, max_tokens)
        if _PROVIDER in ("openai", "openai_compatible"):
            return _generate_openai_compat(prompt, max_tokens)
        logger.warning("unknown LLM_PROVIDER %r, using fallback", _PROVIDER)
        return ""
    except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as e:
        logger.warning("llm provider %r error (%s), using fallback", _PROVIDER, e)
        return ""
