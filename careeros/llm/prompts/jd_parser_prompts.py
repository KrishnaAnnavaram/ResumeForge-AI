"""Prompts for JD Parser Agent."""

JD_CORE_EXTRACTION_PROMPT = """You are a precise job description parser. Extract structured information from the job description below. Return ONLY valid JSON. No explanation. No markdown. Only the JSON object.

If a field is not present, return null for strings or [] for arrays. Do not infer. Do not guess. Extract only what is explicitly stated.

Extract:
- company: company name or null
- role_title: exact job title
- seniority: one of [junior, mid, senior, staff, principal, lead, manager, director] or null
- employment_type: one of [full-time, contract, part-time, intern] or null
- location: city/state or null
- remote_policy: one of [remote, hybrid, onsite] or null
- required_skills: list of required technical skills (exact terms from JD)
- preferred_skills: list of preferred/nice-to-have skills
- soft_skills: list of soft skills mentioned
- responsibilities: list of key responsibilities (max 8, concise)
- domain: business domain (Enterprise AI / FinTech / Healthcare / E-commerce / etc.) or null
- industry: industry vertical or null
- team_context: brief description of team/product context or null

Job Description:
{raw_jd_text}"""


JD_SIGNAL_EXTRACTION_PROMPT = """You are a job signal analyst. Extract meta-signals from the job description below. Return ONLY valid JSON.

Extract:
- seniority_signals: list of phrases indicating expected seniority level
- tone: overall tone (formal/technical/startup/corporate) or null
- company_stage: one of [startup, scaleup, enterprise, public] or null
- culture_signals: list of culture indicators from the text
- hiring_signals: object with keys: urgency (high/medium/low/null), team_size_hint (string or null), growth_opportunity (bool), technical_depth (high/medium/low)
- ats_keywords: list of important technical keywords that should appear in a resume to pass ATS

Job Description:
{raw_jd_text}"""
