"""Provider-agnostic AI layer.

Supports: mock (default, no keys), ollama (local), openai, anthropic, gemini.
Every call is wrapped so an AI failure never breaks a core flow — callers get
a graceful fallback and `degraded=True`. Mock mode reports degraded=True so
callers prefer their deterministic, data-backed answer.
"""

from __future__ import annotations

import logging

import httpx
from django.conf import settings

logger = logging.getLogger("ai")


class AIResult:
    def __init__(self, text: str, degraded: bool = False):
        self.text = text
        self.degraded = degraded


def _chat_mock(system: str, prompt: str) -> str:
    return "[AI mock] " + prompt.strip().splitlines()[0][:200]


def _chat_ollama(system: str, prompt: str) -> str:
    url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
    resp = httpx.post(
        url,
        json={
            "model": settings.AI_MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _chat_openai(system: str, prompt: str) -> str:
    # AI_MODEL may hold an Ollama default (llama3.1); use a sensible OpenAI
    # model unless the operator set an explicit gpt-* model.
    model = settings.AI_MODEL if settings.AI_MODEL.startswith("gpt") else "gpt-4o-mini"
    resp = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        json={
            "model": model,
            "temperature": 0.7,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _chat_anthropic(system: str, prompt: str) -> str:
    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": settings.AI_MODEL,
            "max_tokens": 512,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"].strip()


def _chat_gemini(system: str, prompt: str) -> str:
    # AI_MODEL may hold another provider's default; use a Gemini model unless
    # an explicit gemini-* model was configured.
    default_model = "gemini-flash-lite-latest"
    model = settings.AI_MODEL if settings.AI_MODEL.startswith("gemini") else default_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    # New Gemini "auth keys" (AQ.* prefix) authenticate via the x-goog-api-key
    # header. The header also works for older AIza* keys, so use it uniformly.
    resp = httpx.post(
        url,
        headers={
            "x-goog-api-key": settings.GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": prompt}]}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


_PROVIDERS = {
    "mock": _chat_mock,
    "ollama": _chat_ollama,
    "openai": _chat_openai,
    "anthropic": _chat_anthropic,
    "gemini": _chat_gemini,
}


def chat(system: str, prompt: str) -> AIResult:
    """Call the configured provider. Falls back to mock on any failure.

    Mock mode is reported as degraded=True so callers prefer their
    deterministic, data-backed answer over the echo stub.
    """
    provider = settings.AI_PROVIDER.lower()
    fn = _PROVIDERS.get(provider)
    if fn is None or provider == "mock":
        return AIResult(_chat_mock(system, prompt), degraded=True)
    try:
        return AIResult(fn(system, prompt), degraded=False)
    except Exception:
        logger.exception("AI provider '%s' failed; falling back", provider)
        return AIResult(_chat_mock(system, prompt), degraded=True)
