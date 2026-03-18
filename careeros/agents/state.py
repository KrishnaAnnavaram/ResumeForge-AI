"""CareerOS LangGraph state definition."""
from typing import TypedDict, Optional


class CareerOSState(TypedDict):
    session_id: str
    user_id: str

    # Layer 1 — Intake
    jd_raw: str
    jd_id: Optional[str]
    jd_structured: Optional[dict]
    profile: Optional[dict]
    match_score: Optional[float]
    layer1_warnings: list[str]

    # Layer 2 — Intelligence
    evidence_set: Optional[list[dict]]
    gap_analysis: Optional[dict]
    low_evidence_warning: bool

    # Layer 3 — Planning
    rewrite_plan: Optional[dict]

    # Layer 4 — Generation
    resume_draft: Optional[dict]
    cl_draft: Optional[dict]
    resume_version_id: Optional[str]
    cl_version_id: Optional[str]

    # Layer 5 — Validation
    critic_report: Optional[dict]
    critic_retry_count: int

    # Layer 6 — Refinement
    user_feedback_raw: Optional[str]
    feedback_parsed: Optional[dict]

    # Control
    iteration: int
    status: str
    error: Optional[str]
    should_stream: bool
