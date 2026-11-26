"""Ollama chat client, grounded prompt builder and extractive fallback."""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import requests

import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are a Rust Book assistant. You answer questions about the Rust programming language using ONLY the numbered context passages from "The Rust Programming Language" book that are given to you.

Rules:
1. Use only facts stated in the context. Do not use outside knowledge.
2. Cite the passages you use with their numbers in square brackets, for example [1] or [2].
3. When you show Rust code, copy it exactly from the context.
4. Keep the answer concise: a short explanation, then code only if it helps.
5. If the context does not contain the answer, reply exactly: {config.REFUSAL_TEXT}"""

USER_TEMPLATE = """Context:
{context}

Question: {question}

Answer using only the context above and cite passages like [1]."""


class LLMUnavailable(RuntimeError):
    """Raised when the Ollama server cannot be reached."""


def format_context(passages: list[dict]) -> str:
    """Number passages as [1], [2], ... with their heading path as a source line."""
    parts = []
    for i, p in enumerate(passages, start=1):
        parts.append(f"[{i}] (source: {p['metadata'].get('heading_path', '')})\n{p['text']}")
    return "\n\n".join(parts)


def build_messages(question: str, passages: list[dict]) -> list[dict]:
    """Build the chat messages for Ollama."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(context=format_context(passages), question=question)},
    ]


def prompt_template_text() -> str:
    """Human-readable prompt template (saved to results/prompt_template.txt)."""
    return (f"=== SYSTEM ===\n{SYSTEM_PROMPT}\n\n=== USER ===\n{USER_TEMPLATE}\n\n"
            f"=== OPTIONS ===\ntemperature={config.LLM_TEMPERATURE}, num_ctx={config.LLM_NUM_CTX}, "
            f"num_predict={config.LLM_MAX_TOKENS}\n"
            "Each context passage is formatted as: [n] (source: <chapter > heading path>)\\n<chunk text>\n")


class OllamaClient:
    """Minimal Ollama /api/chat client over HTTP (no SDK)."""

    def __init__(self, base_url: str = config.OLLAMA_URL, model: str = config.LLM_MODEL) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=2).ok
        except requests.RequestException:
            return False

    def has_model(self, model: str | None = None) -> bool:
        try:
            tags = requests.get(f"{self.base_url}/api/tags", timeout=2).json()
        except (requests.RequestException, ValueError):
            return False
        names = {m.get("name") for m in tags.get("models", [])}
        return (model or self.model) in names

    def _payload(self, messages: list[dict], stream: bool, model: str | None) -> dict:
        return {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": config.LLM_TEMPERATURE,
                "num_ctx": config.LLM_NUM_CTX,
                "num_predict": config.LLM_MAX_TOKENS,
            },
        }

    def chat(self, messages: list[dict], model: str | None = None) -> str:
        """Non-streaming chat call; returns the full reply."""
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=self._payload(messages, False, model),
                              timeout=config.LLM_TIMEOUT_S)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise LLMUnavailable(str(exc)) from exc
        return r.json()["message"]["content"].strip()

    def chat_stream(self, messages: list[dict], model: str | None = None) -> Iterator[str]:
        """Streaming chat call; yields text pieces as they arrive."""
        try:
            with requests.post(f"{self.base_url}/api/chat", json=self._payload(messages, True, model),
                               stream=True, timeout=config.LLM_TIMEOUT_S) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    piece = data.get("message", {}).get("content", "")
                    if piece:
                        yield piece
                    if data.get("done"):
                        break
        except requests.RequestException as exc:
            raise LLMUnavailable(str(exc)) from exc


def extractive_fallback(passages: list[dict], max_words: int = config.FALLBACK_MAX_WORDS) -> str:
    """Return the best passage, trimmed, clearly labelled as not LLM-generated."""
    if not passages:
        return config.REFUSAL_TEXT
    best = passages[0]
    words = best["text"].split(" ")
    snippet = " ".join(words[:max_words]) + (" ..." if len(words) > max_words else "")
    return ("**[Extractive fallback: LLM unavailable, showing the most relevant passage verbatim]**\n\n"
            f"{snippet}\n\n[1]")
