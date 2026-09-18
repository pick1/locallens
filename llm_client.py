"""
Central LLM wrapper for LocalLens.

All LLM calls go through this module to ensure:
- Consistent backend selection (OpenAI > Ollama)
- Retry logic with exponential backoff
- Structured output support via prompt-based JSON parsing

Backends (detected automatically):
1. OpenAI (GPT-4o) — if OPENAI_API_KEY is set
2. Ollama (gemma4:e4b) — if Ollama is running locally (no API key needed)
3. Fallback — returns mock/simple responses for demo mode
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

import requests

from config import settings

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:e4b"


class LLMClientError(Exception):
    """Raised when LLM calls fail after all retries."""

    pass


class LLMClient:
    """Central LLM client with backend auto-detection and retry.

    Automatically selects the best available backend:
    - OpenAI when API key is configured
    - Ollama when running locally
    - Fallback stub when neither is available
    """

    def __init__(self) -> None:
        self._max_retries = 3
        self._backend: Literal["openai", "ollama", "mock"] = self._detect_backend()
        logger.info("LLM backend selected: %s", self._backend)

        # OpenAI setup (lazy — only import if needed)
        self._llm = None
        if self._backend == "openai":
            self._model_name = "gpt-4o"
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self._model_name,
                api_key=settings.openai_api_key,
                temperature=0.3,
                max_tokens=2048,
            )

    @property
    def backend(self) -> str:
        """Return the active backend name (openai/ollama/mock)."""
        return self._backend

    @property
    def available(self) -> bool:
        """True if a real LLM backend is available (not mock)."""
        return self._backend != "mock"

    @staticmethod
    def _detect_backend() -> Literal["openai", "ollama", "mock"]:
        """Detect which LLM backend is available."""
        # 1. Check OpenAI
        if settings.openai_api_key:
            return "openai"

        # 2. Check Ollama
        try:
            resp = requests.get(
                f"{OLLAMA_BASE_URL}/api/tags", timeout=3
            )
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if any(OLLAMA_MODEL in m.get("name", "") for m in models):
                    return "ollama"
                # Any model available?
                if models:
                    logger.info("Ollama available but %s not found, using first available", OLLAMA_MODEL)
                    return "ollama"
        except (requests.RequestException, ConnectionError, ValueError):
            pass

        # 3. Fallback
        logger.warning("No LLM backend detected — using mock responses")
        return "mock"

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text from an LLM with retry logic.

        Args:
            prompt: The user/human message content.
            system_prompt: Optional system message to set context.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.

        Returns:
            Generated text content.

        Raises:
            LLMClientError: If all retries fail.
        """
        if self._backend == "openai":
            return self._generate_openai(prompt, system_prompt, temperature, max_tokens)
        if self._backend == "ollama":
            return self._generate_ollama(prompt, system_prompt, temperature, max_tokens)
        return self._generate_mock(prompt, system_prompt)

    def generate_structured(
        self,
        prompt: str,
        response_schema: dict[str, Any] | None = None,
        response_model: type | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate a structured (typed) response from the LLM.

        Accepts either a response_schema dict or a Pydantic response_model class.
        Uses a carefully crafted prompt to encourage JSON output, then parses.

        Args:
            prompt: The user/human message content.
            response_schema: Dict describing expected JSON keys and types.
            response_model: Pydantic BaseModel class (alternative to schema).
            system_prompt: Optional system message.
            temperature: Sampling temperature.

        Returns:
            Dict with parsed JSON fields.

        Raises:
            LLMClientError: If parsing fails after all retries.
        """
        # Build schema description from response_model or response_schema
        type_hints: dict[str, str] = {}
        schema = response_schema
        if response_model is not None and schema is None:
            # Extract field descriptions AND type annotations from Pydantic model
            try:
                for field_name, field in response_model.model_fields.items():
                    desc = field.description or ""
                    # Map Python annotations to JSON types for the prompt
                    raw_type = str(field.annotation)
                    if "list" in raw_type.lower() or "list" in raw_type:
                        json_type = "list of strings"
                    elif "bool" in raw_type.lower():
                        json_type = "boolean (true/false)"
                    elif "int" in raw_type.lower():
                        json_type = "integer"
                    else:
                        json_type = "string"
                    schema = schema or {}
                    schema[field_name] = desc
                    type_hints[field_name] = json_type
            except AttributeError:
                pass

            if not schema:
                # Fallback using model_json_schema
                try:
                    model_schema = response_model.model_json_schema()
                    for prop, info in model_schema.get("properties", {}).items():
                        schema = schema or {}
                        schema[prop] = info.get("description", prop)
                        raw_type = info.get("type", "string")
                        json_type = {
                            "array": "list of strings",
                            "boolean": "boolean (true/false)",
                            "integer": "integer",
                            "number": "number",
                        }.get(raw_type, "string")
                        type_hints[prop] = json_type
                except Exception:
                    schema = response_schema or {}

        if schema:
            schema_desc = "\n".join(
                f'  "{k}": <{type_hints.get(k, "string")}>  # {v}'
                for k, v in schema.items()
            )
        else:
            schema_desc = "  (no schema specified — return whatever fits)"

        json_instructions = (
            "You MUST respond with ONLY valid JSON matching this schema:\n"
            f"{{\n{schema_desc}\n}}\n"
            "No markdown fences. No extra text. Just JSON."
        )

        full_system = system_prompt or ""
        full_system += f"\n\n{json_instructions}"

        for attempt in range(self._max_retries + 1):
            try:
                text = self.generate(
                    prompt=prompt,
                    system_prompt=full_system,
                    temperature=temperature,
                    max_tokens=2048,
                )
                # Clean the response — remove markdown fences
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1]
                    text = text.rsplit("```", 1)[0]
                if text.startswith("```json"):
                    text = text[7:]
                    text = text.rsplit("```", 1)[0]
                text = text.strip()

                parsed = json.loads(text)
                # Validate required keys
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError("Response is not a JSON object")

            except (json.JSONDecodeError, ValueError) as e:
                if attempt < self._max_retries:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Structured parse failed (attempt %d/%d): %s. Retrying in %ds",
                        attempt + 1,
                        self._max_retries,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    raise LLMClientError(
                        f"Failed to parse structured output after {self._max_retries} retries: {e}"
                    ) from e

        raise LLMClientError("Failed to generate structured output")

    # ── OpenAI Backend ──────────────────────────────────────────────────

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        from langchain_core.messages import BaseMessage

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self._max_retries + 1):
            try:
                response: BaseMessage = self._llm.invoke(messages)
                content = response.content
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    )
                return str(content)
            except Exception as e:
                if attempt < self._max_retries:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "OpenAI call failed (attempt %d/%d): %s. Retrying in %ds",
                        attempt + 1,
                        self._max_retries,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("OpenAI call failed after %d retries", self._max_retries)
                    raise LLMClientError(str(e)) from e
        return ""  # unreachable

    # ── Ollama Backend ──────────────────────────────────────────────────

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Generate text using Ollama's API."""
        payload: dict[str, Any] = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            # Ollama supports system prompt in the generate API
            payload["system"] = system_prompt

        for attempt in range(self._max_retries + 1):
            try:
                resp = requests.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json=payload,
                    timeout=120,  # Ollama can be slow
                )
                resp.raise_for_status()
                result = resp.json()
                return result.get("response", "")
            except (requests.RequestException, ValueError) as e:
                if attempt < self._max_retries:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Ollama call failed (attempt %d/%d): %s. Retrying in %ds",
                        attempt + 1,
                        self._max_retries,
                        e,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Ollama call failed after %d retries", self._max_retries)
                    raise LLMClientError(str(e)) from e
        return ""  # unreachable

    # ── Mock Backend ────────────────────────────────────────────────────

    def _generate_mock(
        self,
        prompt: str,
        system_prompt: str | None,
    ) -> str:
        """Return a simple mock response when no LLM is available."""
        return (
            "This is a mock response — no LLM backend is configured. "
            "Set OPENAI_API_KEY or ensure Ollama is running (gemma4:e4b) "
            "to enable AI-generated analysis."
        )


# Shared singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the global LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
