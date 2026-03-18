"""JD API schemas."""
from pydantic import BaseModel


class JDAnalyzeRequest(BaseModel):
    raw_text: str
    source_url: str | None = None


class JDResponse(BaseModel):
    jd_id: str
    company: str | None
    role_title: str | None
    seniority: str | None
    required_skills: list[str]
    preferred_skills: list[str]
    ats_keywords: list[str]
    domain: str | None
    parse_confidence: float
    parse_warnings: list[str]
    match_score: float | None
