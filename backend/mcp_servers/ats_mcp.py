"""
mcp_servers/ats_mcp.py — ATS computation MCP server.

Pure computation — NO database writes. All scoring logic lives here.
Used by ats_analyzer and ats_rescorer agents.
"""

import re
from typing import Any

from backend.core.logger import get_logger
from backend.mcp_servers.base_mcp import BaseMCP

logger = get_logger(__name__)


class AtsMCP(BaseMCP):
    """
    Pure ATS keyword extraction and scoring.
    All methods are stateless — no DB, no cache.
    """

    def __init__(self) -> None:
        super().__init__()

    # ── Keyword extraction ────────────────────────────────────────────────

    async def extract_jd_keywords(self, jd_text: str) -> dict[str, Any]:
        """
        Extract structured keywords from a job description.
        Returns: {hard_skills, soft_skills, tools, certifications, action_verbs, min_years}

        This is a heuristic fallback; the primary extraction happens in the
        ats_analyzer LLM node (Claude Opus). This method is used for scoring
        when no LLM result is available.
        """
        try:
            text_lower = jd_text.lower()

            # Detect minimum years of experience
            years_match = re.findall(
                r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
                text_lower,
            )
            min_years = max((int(y) for y in years_match), default=0)

            # Common action verbs in JDs
            action_verbs = [
                w for w in [
                    "developed", "built", "designed", "implemented", "led",
                    "managed", "architected", "delivered", "optimised", "automated",
                    "collaborated", "mentored", "scaled", "deployed", "integrated",
                ]
                if w in text_lower
            ]

            return {
                "hard_skills": [],   # populated by Claude LLM call
                "soft_skills": [],
                "tools": [],
                "certifications": [],
                "action_verbs": action_verbs,
                "min_years": min_years,
                "raw_text": jd_text,
            }
        except Exception as exc:
            return self._error(str(exc), "KEYWORD_EXTRACTION_ERROR")

    # ── Scoring ───────────────────────────────────────────────────────────

    async def score_resume(
        self,
        resume_text: str,
        jd_keywords: dict,
        profile_skills: list,
    ) -> dict[str, Any]:
        """
        Compute an ATS match score for a resume against JD keywords.
        Returns: {overall_score, section_scores}
        """
        try:
            resume_lower = resume_text.lower()
            all_keywords = self._flatten_keywords(jd_keywords)

            if not all_keywords:
                return {
                    "overall_score": 0.0,
                    "section_scores": {
                        "summary": 0, "skills": 0, "experience": 0,
                        "education": 0, "certifications": 0,
                    },
                }

            # Section extraction (simple heuristic headers)
            sections = self._extract_sections(resume_text)

            # Score each section against its relevant keywords
            scores = {
                "summary": self._section_score(
                    sections.get("summary", ""),
                    jd_keywords.get("soft_skills", []) + jd_keywords.get("action_verbs", []),
                ),
                "skills": self._section_score(
                    sections.get("skills", ""),
                    jd_keywords.get("hard_skills", []) + jd_keywords.get("tools", []),
                ),
                "experience": self._section_score(
                    sections.get("experience", ""),
                    jd_keywords.get("hard_skills", []) + jd_keywords.get("tools", []),
                ),
                "education": self._section_score(
                    sections.get("education", ""),
                    jd_keywords.get("certifications", []),
                ),
                "certifications": self._section_score(
                    sections.get("certifications", ""),
                    jd_keywords.get("certifications", []),
                ),
            }

            # Weighted overall score
            weights = {
                "summary": 0.10,
                "skills": 0.25,
                "experience": 0.45,
                "education": 0.10,
                "certifications": 0.10,
            }
            overall = sum(scores[s] * weights[s] for s in weights)

            return {
                "overall_score": round(overall, 2),
                "section_scores": {k: round(v, 2) for k, v in scores.items()},
            }
        except Exception as exc:
            return self._error(str(exc), "SCORING_ERROR")

    async def get_match_list(
        self, profile_skills: list, jd_keywords: dict
    ) -> dict[str, Any]:
        try:
            profile_lower = {s.lower() if isinstance(s, str) else
                             s.get("skill", "").lower() for s in profile_skills}
            all_jd = self._flatten_keywords(jd_keywords)
            matched = [kw for kw in all_jd if kw.lower() in profile_lower]
            return {"matched_keywords": matched}
        except Exception as exc:
            return self._error(str(exc), "MATCH_LIST_ERROR")

    async def get_gap_list(
        self,
        profile_skills: list,
        jd_keywords: dict,
        resume_text: str,
    ) -> dict[str, Any]:
        try:
            resume_lower = resume_text.lower()
            profile_lower = {s.lower() if isinstance(s, str) else
                             s.get("skill", "").lower() for s in profile_skills}
            all_jd = self._flatten_keywords(jd_keywords)
            missing = [
                kw for kw in all_jd
                if kw.lower() not in profile_lower
                and kw.lower() not in resume_lower
            ]
            return {"missing_keywords": missing}
        except Exception as exc:
            return self._error(str(exc), "GAP_LIST_ERROR")

    async def get_experience_gaps(
        self, jd_text: str, experience_json: list
    ) -> dict[str, Any]:
        """
        Simple heuristic experience gap detection.
        The real analysis is done by Claude Opus in ats_analyzer.
        """
        try:
            gaps = []
            jd_lower = jd_text.lower()

            years_match = re.findall(
                r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
                jd_lower,
            )
            if years_match:
                req_years = max(int(y) for y in years_match)
                total_exp = sum(
                    int(e.get("years", 0)) for e in experience_json
                    if isinstance(e.get("years"), (int, float))
                )
                if total_exp < req_years:
                    gaps.append({
                        "gap": f"JD needs {req_years}+ yrs — resume shows {total_exp} yrs",
                        "action": "Reframe each role to show scope, impact, and breadth not just tenure",
                    })

            if "lead" in jd_lower or "manager" in jd_lower:
                has_leadership = any(
                    "lead" in str(e.get("title", "")).lower() or
                    "manager" in str(e.get("title", "")).lower()
                    for e in experience_json
                )
                if not has_leadership:
                    gaps.append({
                        "gap": "Team lead / management experience not prominent",
                        "action": "Surface leadership evidence from existing bullet points",
                    })

            return {"experience_gaps": gaps}
        except Exception as exc:
            return self._error(str(exc), "EXPERIENCE_GAP_ERROR")

    async def build_gap_json(
        self,
        score_result: dict,
        match_result: dict,
        gap_result: dict,
        experience_gaps: list,
        rewrite_hints: list,
    ) -> dict[str, Any]:
        """Assemble the full rich gap JSON stored in jobs.ats_gap_json."""
        try:
            return {
                "missing_keywords": gap_result.get("missing_keywords", []),
                "experience_gaps": experience_gaps,
                "section_scores": score_result.get("section_scores", {}),
                "matched_keywords": match_result.get("matched_keywords", []),
                "rewrite_hints": rewrite_hints,
            }
        except Exception as exc:
            return self._error(str(exc), "BUILD_GAP_JSON_ERROR")

    # ── Private helpers ───────────────────────────────────────────────────

    def _flatten_keywords(self, jd_keywords: dict) -> list[str]:
        result = []
        for key in ["hard_skills", "soft_skills", "tools", "certifications"]:
            result.extend(jd_keywords.get(key, []))
        return [str(k) for k in result if k]

    def _section_score(self, section_text: str, keywords: list[str]) -> float:
        if not keywords:
            return 100.0
        if not section_text:
            return 0.0
        text_lower = section_text.lower()
        hits = sum(1 for kw in keywords if kw.lower() in text_lower)
        return round((hits / len(keywords)) * 100, 2)

    def _extract_sections(self, resume_text: str) -> dict[str, str]:
        """
        Split resume into named sections using common header patterns.
        Returns a dict with keys: summary, skills, experience, education, certifications.
        """
        section_headers = {
            "summary": r"(summary|profile|objective|about)",
            "skills": r"(skills|technical\s+skills|competencies|technologies)",
            "experience": r"(experience|employment|work\s+history|career)",
            "education": r"(education|academic|degree|university)",
            "certifications": r"(certif|licens|accreditat)",
        }

        lines = resume_text.split("\n")
        current_section = "experience"  # default
        sections: dict[str, list[str]] = {k: [] for k in section_headers}

        for line in lines:
            line_lower = line.lower().strip()
            matched = False
            for sec, pattern in section_headers.items():
                if re.search(pattern, line_lower):
                    current_section = sec
                    matched = True
                    break
            if not matched:
                sections[current_section].append(line)

        return {k: "\n".join(v) for k, v in sections.items()}
