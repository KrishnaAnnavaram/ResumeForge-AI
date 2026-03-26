"""
llm/gpt_client.py — OpenAI GPT-4o wrapper for bullet point rewriting ONLY.

Responsibilities:
- Receive each original bullet + its rewrite hint from Claude's gap JSON
- Return a JSON array of rewritten bullets
- Retry with exponential backoff, circuit breaker

GPT-4o NEVER sees the full resume, summary, or scoring context.
"""

import asyncio
import json
import random
from typing import Any, Optional

import openai

from backend.core.circuit_breaker import get_circuit_breaker
from backend.core.config import get_settings
from backend.core.exceptions import GPTError
from backend.core.guardrails import validate_bullet_list
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_client: Optional[openai.AsyncOpenAI] = None


def get_openai_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def rewrite_bullets(
    bullets: list[dict[str, str]],
    job_title: str,
) -> list[str]:
    """
    Rewrite experience bullet points for a target role.

    Args:
        bullets: list of {"original": str, "hint": str}
                 Each hint comes from Claude's gap JSON rewrite_hints.
        job_title: target role title for context.

    Returns:
        list of rewritten bullet strings (same order as input).
    """
    if not bullets:
        return []

    cb = get_circuit_breaker("gpt4o")
    client = get_openai_client()

    system = """You are a professional resume bullet point writer.
Your ONLY job is to rewrite experience bullet points to be more achievement-focused,
keyword-rich, and ATS-optimised for the target role.

Rules:
- Start each bullet with a strong action verb
- Include quantifiable achievements where possible (use estimates if needed)
- Inject the suggested keywords naturally — they must fit the original context
- Keep each bullet to 1-2 lines maximum
- Never fabricate companies, titles, degrees, or certifications
- Never add experience the candidate does not have

Return ONLY a valid JSON array of rewritten bullet strings.
Example: ["Led migration of 3 microservices to Docker reducing deploy time by 40%", "..."]"""

    bullets_payload = json.dumps([
        {"original": b["original"], "rewrite_hint": b.get("hint", "")}
        for b in bullets
    ], indent=2)

    user_message = f"""Target role: {job_title}

Bullets to rewrite:
{bullets_payload}

Return the rewritten bullets as a JSON array in the same order. No markdown."""

    last_exc: Exception = Exception("Unknown error")
    for attempt in range(3):
        try:
            async with cb:
                response = await client.chat.completions.create(
                    model=settings.gpt4o_model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=settings.gpt4o_max_tokens_per_bullet * len(bullets),
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                usage = response.usage
                logger.info(
                    "GPT-4o call complete",
                    model=settings.gpt4o_model,
                    input_tokens=usage.prompt_tokens if usage else 0,
                    output_tokens=usage.completion_tokens if usage else 0,
                    bullet_count=len(bullets),
                    attempt=attempt + 1,
                )

                raw = response.choices[0].message.content
                parsed = json.loads(raw)

                # GPT may return {"bullets": [...]} or just [...]
                if isinstance(parsed, dict):
                    for key in ["bullets", "rewritten_bullets", "results", "data"]:
                        if key in parsed and isinstance(parsed[key], list):
                            parsed = parsed[key]
                            break
                    else:
                        # Try first list value
                        for v in parsed.values():
                            if isinstance(v, list):
                                parsed = v
                                break

                return validate_bullet_list(parsed)

        except openai.RateLimitError as exc:
            last_exc = exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "GPT-4o rate limit — backing off",
                attempt=attempt + 1,
                wait_s=round(wait, 2),
            )
            await asyncio.sleep(wait)

        except openai.APIStatusError as exc:
            last_exc = exc
            if exc.status_code >= 500:
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "GPT-4o server error — backing off",
                    status=exc.status_code,
                    attempt=attempt + 1,
                    wait_s=round(wait, 2),
                )
                await asyncio.sleep(wait)
            else:
                raise GPTError(f"GPT-4o API error {exc.status_code}")

        except Exception as exc:
            last_exc = exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "GPT-4o call failed — backing off",
                attempt=attempt + 1,
                error=str(exc),
                wait_s=round(wait, 2),
            )
            await asyncio.sleep(wait)

    raise GPTError(
        f"GPT-4o bullet rewrite failed after 3 attempts: {last_exc}",
        detail=str(last_exc),
    )
