"""Prompts for Gap Analyzer Agent."""

GAP_NUANCE_PROMPT = """You are a career evidence analyzer. Your job is to determine whether a candidate's experience evidence demonstrates competency in a specific skill, even if the skill is not named explicitly.

Skill to evaluate: {skill}
JD context: {jd_role_title} at {jd_company}

Evidence bullets:
{evidence_bullets}

Analyze whether the evidence demonstrates this skill. Return JSON only:
{{
  "demonstrates_skill": true/false,
  "confidence": "high"/"medium"/"low",
  "reasoning": "one sentence explanation",
  "relevant_bullet_ids": []
}}"""
