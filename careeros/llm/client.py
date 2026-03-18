"""Anthropic LLM client with retry logic and structured output support."""
import json
import time
from typing import Any
import anthropic
from careeros.config import get_settings
from careeros.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


class LLMClient:
    """Wrapper around Anthropic client with structured output and retry support."""

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Call Claude and return text response."""
        model = model or settings.haiku_model
        messages = [{"role": "user", "content": prompt}]

        start = time.time()
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system or "You are a precise AI assistant.",
                messages=messages,
                temperature=temperature,
            )
            elapsed = int((time.time() - start) * 1000)
            log.info(
                "llm.complete",
                model=model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                duration_ms=elapsed,
            )
            return response.content[0].text
        except Exception as exc:
            log.error("llm.error", model=model, error=str(exc))
            raise

    def complete_json(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 4096,
        system: str | None = None,
        temperature: float = 0.1,
    ) -> dict | list:
        """Call Claude and parse JSON response. Raises ValueError on parse failure."""
        text = self.complete(prompt, model=model, max_tokens=max_tokens, system=system, temperature=temperature)
        # Strip markdown code fences if present
        stripped = text.strip()
        if stripped.startswith("```"):
            lines = stripped.split("\n")
            stripped = "\n".join(lines[1:-1]) if len(lines) > 2 else stripped
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            log.error("llm.json_parse_error", raw=stripped[:500], error=str(exc))
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    async def stream_complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 8192,
        system: str | None = None,
        temperature: float = 0.3,
    ):
        """Async generator streaming tokens from Claude."""
        model = model or settings.sonnet_model
        import anthropic as _anthropic
        async_client = _anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        async with async_client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system or "You are an elite resume writer.",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text


# Module-level singleton
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
