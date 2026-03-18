"""Resume structured data extractor using Claude."""
from careeros.llm.client import get_llm_client
from careeros.config import get_settings
from careeros.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()

RESUME_EXTRACTION_PROMPT = """From the resume below, extract ALL structured career data. Return ONLY valid JSON.

Extract:
- profile: {{full_name, headline, summary, location, linkedin, github}}
- experiences: [{{company, title, employment_type, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD or null), is_current, domain, description, bullets: [{{content, metrics: [], skills_used: []}}]}}]
- skills: [{{name, category, proficiency (expert/proficient/familiar), years_used (number or null)}}]
- education: [{{institution, degree, field, start_date, end_date, gpa}}]
- certifications: [{{name, issuer, issued_date (YYYY-MM-DD or null), credential_id}}]

For each bullet:
- metrics: extract ALL numbers (%, $, time savings, user counts, etc.)
- skills_used: ALL technologies, tools, frameworks, languages mentioned

Be exhaustive. Extract every experience, every bullet, every skill. Do not summarize or truncate.
Return ONLY valid JSON, no markdown, no explanation.

Resume:
{raw_text}"""


def extract_resume_data(raw_text: str) -> dict:
    """Extract structured career data from resume text via LLM."""
    llm = get_llm_client()
    prompt = RESUME_EXTRACTION_PROMPT.format(raw_text=raw_text[:15000])  # truncate for context

    log.info("resume_extractor.start", text_length=len(raw_text))
    result = llm.complete_json(
        prompt,
        model=settings.sonnet_model,
        max_tokens=8000,
        temperature=0.1,
    )
    log.info(
        "resume_extractor.complete",
        experiences=len(result.get("experiences", [])),
        skills=len(result.get("skills", [])),
    )
    return result
