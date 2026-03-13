"""tests/test_parser.py — Unit tests for resume_parser utilities."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.resume_parser import extract_verified_metrics, chunk_resume


def test_extract_percentages():
    """Percentage patterns should be captured."""
    parsed = {"raw_full_text": "Achieved 45% reduction and 91% accuracy in production."}
    m = extract_verified_metrics(parsed)
    assert "45%" in m
    assert "91%" in m


def test_extract_decimal_percentage():
    """Decimal percentages like 99.9% should be captured."""
    parsed = {"raw_full_text": "Maintained 99.9% uptime across all services."}
    m = extract_verified_metrics(parsed)
    assert "99.9%" in m


def test_extract_years():
    """'X years' pattern should be captured."""
    parsed = {"raw_full_text": "5 years of experience in machine learning."}
    m = extract_verified_metrics(parsed)
    assert any("years" in k.lower() for k in m)


def test_extract_multiple_metrics():
    """Multiple metrics in one text should all be extracted."""
    text = "Reduced latency by 30%, improved accuracy by 15%, saved 20% cost."
    parsed = {"raw_full_text": text}
    m = extract_verified_metrics(parsed)
    assert "30%" in m
    assert "15%" in m
    assert "20%" in m


def test_chunk_resume_sections():
    """chunk_resume should produce chunks with valid section fields."""
    parsed = {
        "summary": "AI Engineer with 5 years of experience.",
        "experience": [
            {
                "title": "ML Engineer", "company": "ACME", "location": "TX",
                "dates": "Jan 2023 – Present",
                "bullets": ["Built BERT models achieving 90% accuracy."],
                "full_text": "ML Engineer at ACME (TX) | Jan 2023 – Present\nBuilt BERT models achieving 90% accuracy.",
            }
        ],
        "education": [
            {"degree": "MS Data Science", "school": "UNT", "dates": "2024", "specialization": "NLP"}
        ],
        "skills": {
            "raw_text": "Python, PyTorch, AWS",
            "categories": {"ML": ["Python", "PyTorch"], "Cloud": ["AWS"]},
        },
        "certifications": "",
    }
    chunks = chunk_resume(parsed)
    sections = {c["section"] for c in chunks}
    assert "summary"    in sections
    assert "experience" in sections
    assert "education"  in sections
    assert "skills"     in sections


def test_chunk_ids_unique():
    """All chunk IDs should be unique."""
    parsed = {
        "summary": "Summary text.",
        "experience": [
            {"title": "Job1", "company": "Co1", "location": "", "dates": "2023",
             "bullets": [], "full_text": "Job1 at Co1 | 2023"},
            {"title": "Job2", "company": "Co2", "location": "", "dates": "2022",
             "bullets": [], "full_text": "Job2 at Co2 | 2022"},
        ],
        "education":       [],
        "skills":          {"raw_text": "Python", "categories": {}},
        "certifications":  "",
    }
    chunks = chunk_resume(parsed)
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "Chunk IDs must be unique"
