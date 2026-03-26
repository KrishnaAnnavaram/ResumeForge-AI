"""
llm/claude_client.py — Anthropic Claude SDK wrapper.

Features:
- Retry with exponential backoff (3 attempts: 2s, 4s, 8s + jitter)
- Circuit breaker (get_circuit_breaker("claude"))
- Token usage logging on every call
- Separate methods for Opus (ATS) and Sonnet (generation)
- Structured output parsing with fallback
"""

import asyncio
import json
import random
from typing import Any, Optional

import anthropic

from backend.core.circuit_breaker import get_circuit_breaker
from backend.core.config import get_settings
from backend.core.exceptions import ClaudeError
from backend.core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

_client: Optional[anthropic.AsyncAnthropic] = None


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def _call_claude(
    model: str,
    system: str,
    user_message: str,
    max_tokens: int,
    expect_json: bool = False,
) -> str:
    """
    Core Claude call with retry + circuit breaker.
    Returns the text content of Claude's first response block.
    """
    cb = get_circuit_breaker("claude")
    client = get_anthropic_client()

    last_exc: Exception = Exception("Unknown error")
    for attempt in range(3):
        try:
            async with cb:
                response = await client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user_message}],
                )
                usage = response.usage
                logger.info(
                    "Claude call complete",
                    model=model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    attempt=attempt + 1,
                )
                text = response.content[0].text
                return text

        except anthropic.RateLimitError as exc:
            last_exc = exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "Claude rate limit — backing off",
                attempt=attempt + 1,
                wait_s=round(wait, 2),
            )
            await asyncio.sleep(wait)

        except anthropic.APIStatusError as exc:
            last_exc = exc
            if exc.status_code >= 500:
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    "Claude server error — backing off",
                    status=exc.status_code,
                    attempt=attempt + 1,
                    wait_s=round(wait, 2),
                )
                await asyncio.sleep(wait)
            else:
                # 4xx errors are not retryable
                raise ClaudeError(f"Claude API error {exc.status_code}: {exc.message}")

        except Exception as exc:
            last_exc = exc
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "Claude call failed — backing off",
                attempt=attempt + 1,
                error=str(exc),
                wait_s=round(wait, 2),
            )
            await asyncio.sleep(wait)

    raise ClaudeError(
        f"Claude call failed after 3 attempts: {last_exc}",
        detail=str(last_exc),
    )


def _extract_json(text: str) -> Any:
    """
    Extract JSON from Claude's response.
    Claude often wraps JSON in markdown code fences.
    """
    import re
    # Try bare JSON first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try extracting from ```json ... ``` block
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    raise ClaudeError(
        "Claude returned malformed JSON",
        detail=f"raw_text={text[:500]}",
    )


# ── Public API ────────────────────────────────────────────────────────────────

async def analyze_jd(jd_text: str, profile: dict) -> dict[str, Any]:
    """
    Claude Opus: deep JD analysis → structured keyword + gap JSON.
    """
    system = """You are an expert ATS (Applicant Tracking System) analyst with 20 years of experience.
Your job is to extract structured keywords from a job description and score a candidate's profile against them.

You MUST return a single valid JSON object with this exact structure:
{
  "jd_keywords": {
    "hard_skills": ["Python", "FastAPI", ...],
    "soft_skills": ["leadership", "communication", ...],
    "tools": ["Docker", "Kubernetes", ...],
    "certifications": ["AWS Solutions Architect", ...],
    "action_verbs": ["built", "led", "scaled", ...],
    "min_years": 5,
    "seniority_level": "senior"
  },
  "ats_score": 72.5,
  "section_scores": {
    "summary": 60,
    "skills": 75,
    "experience": 80,
    "education": 90,
    "certifications": 70
  },
  "matched_keywords": ["Python", "FastAPI", ...],
  "missing_keywords": ["GraphQL", "Docker", ...],
  "experience_gaps": [
    {"gap": "JD needs 5+ yrs — profile shows 3 yrs", "action": "Reframe scope over tenure"}
  ],
  "rewrite_hints": [
    {"section": "summary", "hint": "Lead with cloud and CI/CD experience"},
    {"section": "experience", "hint": "Add Docker and Lambda to job 1 bullets"},
    {"section": "skills", "hint": "Add GraphQL, CI/CD, containerisation"}
  ]
}

Return ONLY the JSON — no explanations, no markdown, no preamble."""

    user_message = f"""JOB DESCRIPTION:
{jd_text}

CANDIDATE PROFILE:
Skills: {json.dumps(profile.get("skills_json", []))}
Experience: {json.dumps(profile.get("experience_json", []))}
Education: {json.dumps(profile.get("education_json", []))}
Certifications: {json.dumps(profile.get("certifications_json", []))}
Resume text: {profile.get("raw_resume_text", "")[:3000]}

Analyse this candidate against the job description. Be rigorous — score honestly."""

    text = await _call_claude(
        model=settings.claude_opus_model,
        system=system,
        user_message=user_message,
        max_tokens=settings.claude_opus_max_tokens,
        expect_json=True,
    )
    return _extract_json(text)


async def assemble_resume(
    profile: dict,
    rewritten_bullets: list[str],
    jd_keywords: dict,
    gap_json: dict,
    job_title: str,
    company_name: str,
) -> str:
    """
    Claude Sonnet: assemble full resume from GPT-4o bullets + profile data.
    Writes summary and skills sections in Claude's voice.
    Returns full resume as formatted text.
    """
    system = """You are a professional resume writer with 20 years of experience helping candidates land jobs at top companies.
You specialise in ATS-optimised resumes that read naturally to human reviewers.

Rules:
- Use the provided rewritten bullet points VERBATIM — do not alter them
- Write the Summary and Skills sections yourself in a confident, first-person-implied voice
- Naturally weave the missing keywords into Summary and Skills where truthful
- Format the resume using this structure:
  # [Full Name]
  [email] | [phone] | [linkedin]

  ## Summary
  [2-3 sentences, keyword-rich, achievement-focused]

  ## Skills
  [comma-separated or grouped skills list]

  ## Experience
  [for each role: Company | Title | Years]
  [bullet points — use the provided rewritten bullets]

  ## Education
  [degree, institution, year]

  ## Certifications
  [if any]

- Return ONLY the resume text — no JSON, no explanations."""

    bullets_text = "\n".join(f"- {b}" for b in rewritten_bullets)
    user_message = f"""TARGET ROLE: {job_title} at {company_name}

CANDIDATE PROFILE:
Name: {profile.get("full_name", "")}
Email: {profile.get("email", "")}
Phone: {profile.get("phone", "")}
LinkedIn: {profile.get("linkedin_url", "")}
Experience: {json.dumps(profile.get("experience_json", []), indent=2)}
Education: {json.dumps(profile.get("education_json", []), indent=2)}
Certifications: {json.dumps(profile.get("certifications_json", []), indent=2)}
Soft skills: {json.dumps(profile.get("soft_skills_json", []))}

REWRITTEN BULLET POINTS (use verbatim):
{bullets_text}

KEYWORDS TO WEAVE IN (in Summary/Skills where truthful):
Missing: {json.dumps(gap_json.get("missing_keywords", []))}
Rewrite hints: {json.dumps(gap_json.get("rewrite_hints", []), indent=2)}

Assemble the complete ATS-optimised resume now."""

    return await _call_claude(
        model=settings.claude_sonnet_model,
        system=system,
        user_message=user_message,
        max_tokens=settings.claude_sonnet_max_tokens,
    )


async def rescore_resume(resume_text: str, jd_text: str, jd_keywords: dict) -> dict[str, Any]:
    """
    Claude Opus: re-score the assembled resume. Returns score + section_scores.
    Must return JSON.
    """
    system = """You are an expert ATS scoring engine. Score the provided resume against the job description.

Return ONLY a JSON object:
{
  "ats_score": 95.0,
  "section_scores": {
    "summary": 95,
    "skills": 97,
    "experience": 96,
    "education": 90,
    "certifications": 85
  },
  "feedback": "Brief note on what could still improve"
}"""

    user_message = f"""JOB DESCRIPTION:
{jd_text[:3000]}

KEYWORDS REQUIRED:
{json.dumps(jd_keywords, indent=2)}

RESUME TO SCORE:
{resume_text}

Score this resume honestly against the JD. ATS score is a percentage 0-100."""

    text = await _call_claude(
        model=settings.claude_opus_model,
        system=system,
        user_message=user_message,
        max_tokens=1024,
        expect_json=True,
    )
    return _extract_json(text)


async def generate_cover_letter(
    profile: dict,
    job_title: str,
    company_name: str,
    jd_text: str,
    soft_skills: list[str],
) -> str:
    """
    Claude Sonnet: personalised cover letter.
    Weaves soft skills naturally into achievement-based prose.
    """
    system = """You are a professional cover letter writer. Write a compelling, personalised cover letter.

Rules:
- 3 paragraphs: opening hook, achievement examples, closing
- Weave soft skills naturally into achievement prose — never list them
- Be specific — reference the company name and role
- Achievement-focused — use numbers and impact where possible
- Warm but professional tone
- Do NOT use generic phrases like "I am writing to apply" or "I am a hard worker"
- Return ONLY the cover letter text"""

    user_message = f"""ROLE: {job_title} at {company_name}

JOB DESCRIPTION (first 2000 chars):
{jd_text[:2000]}

CANDIDATE:
Name: {profile.get("full_name", "")}
Experience: {json.dumps(profile.get("experience_json", []), indent=2)}
Soft skills to weave in: {json.dumps(soft_skills)}
Key hard skills: {json.dumps([s.get("skill", s) if isinstance(s, dict) else s for s in profile.get("skills_json", [])[:10]])}

Write the cover letter now."""

    return await _call_claude(
        model=settings.claude_sonnet_model,
        system=system,
        user_message=user_message,
        max_tokens=settings.claude_sonnet_max_tokens,
    )
