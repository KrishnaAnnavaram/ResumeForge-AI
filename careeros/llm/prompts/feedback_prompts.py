"""Prompts for Feedback Interpreter Agent."""

FEEDBACK_INTERPRETATION_PROMPT = """You are a career assistant parsing user feedback on a generated resume and cover letter.

Current session context:
- Resume version: {resume_version}
- Cover letter version: {cl_version}
- Available sections: {available_sections}

User feedback:
{feedback_raw}

Classify and structure this feedback. Return JSON only:
{{
  "action": "approve"/"refine_section"/"full_regen"/"reject",
  "targets": [
    {{
      "section": "summary"/"experience_COMPANY"/"skills"/"cover_letter"/"education",
      "instruction": "specific instruction for revision",
      "priority": "high"/"medium"/"low"
    }}
  ],
  "preserve": ["list of things to keep unchanged"],
  "clarification_needed": false,
  "clarification_question": null
}}

If feedback is too vague (e.g. "make it better" with no specifics), set clarification_needed=true and provide a helpful clarification_question."""
