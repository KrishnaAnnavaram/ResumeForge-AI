from typing import TypedDict, Annotated


def replace(old, new):
    return new


def append_log(old: list, new: list) -> list:
    return (old or []) + (new or [])


class ResumeState(TypedDict):
    # INPUTS
    raw_jd:              Annotated[str, replace]
    company_name:        Annotated[str, replace]
    role_name:           Annotated[str, replace]
    job_url:             Annotated[str, replace]      # Optional — user can provide
    salary_range:        Annotated[str, replace]      # Optional — from JD or user

    # LAYER 0: PRE-PROCESSING
    clean_jd:            Annotated[str, replace]
    resume_chunks:       Annotated[list, replace]
    vector_collection:   Annotated[object, replace]   # ChromaDB collection
    verified_metrics:    Annotated[dict, replace]     # Ground truth from resume

    # LAYER 1: INTELLIGENCE
    jd_analysis:         Annotated[dict, replace]
    bm25_index:          Annotated[object, replace]
    chunk_texts:         Annotated[list, replace]

    # LAYER 2: RETRIEVAL
    retrieved_chunks:    Annotated[list, replace]

    # LAYER 3: REFLEXION LOOP
    draft_resume:        Annotated[str, replace]
    critic_score:        Annotated[int, replace]
    critic_report:       Annotated[dict, replace]
    reflection_notes:    Annotated[str, replace]
    loop_count:          Annotated[int, replace]

    # LAYER 4: QUALITY GATES
    fact_check_passed:   Annotated[bool, replace]
    fact_violations:     Annotated[list, replace]
    format_fixed_resume: Annotated[str, replace]

    # LAYER 5: HUMANIZER
    voice_fingerprint:   Annotated[dict, replace]
    humanized_resume:    Annotated[str, replace]

    # LAYER 6: COVER LETTER
    cover_letter:        Annotated[str, replace]
    cover_letter_score:  Annotated[int, replace]

    # HUMAN-IN-THE-LOOP
    human_approved:      Annotated[bool, replace]
    human_feedback:      Annotated[str, replace]

    # OUTPUTS
    ats_score_report:    Annotated[dict, replace]
    change_log:          Annotated[list, replace]
    resume_output_path:  Annotated[str, replace]      # Saved file path
    cover_letter_path:   Annotated[str, replace]      # Saved file path
    thread_id:           Annotated[str, replace]      # For re-running

    # AUDIT TRAIL (append-only)
    logs:                Annotated[list, append_log]
    errors:              Annotated[list, append_log]
