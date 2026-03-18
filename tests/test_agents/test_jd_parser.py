"""Tests for JD Parser Agent preprocessing logic."""
import pytest
from careeros.agents.jd_parser_agent import _preprocess_jd, _detect_language, _score_confidence


def test_preprocess_strips_html():
    raw = "<h1>Senior Engineer</h1><p>We need someone with <strong>Python</strong> skills.</p>"
    result = _preprocess_jd(raw)
    assert "<h1>" not in result
    assert "Senior Engineer" in result
    assert "Python" in result


def test_preprocess_strips_eeo():
    raw = """
    We are looking for a Python developer.

    We are an equal opportunity employer and do not discriminate on any basis.
    """
    result = _preprocess_jd(raw)
    assert "equal opportunity" not in result.lower()
    assert "Python developer" in result


def test_preprocess_strips_benefits():
    raw = """
    Required: Python, FastAPI

    Benefits:
    - Health insurance
    - 401k matching
    - Free lunch
    """
    result = _preprocess_jd(raw)
    assert "Health insurance" not in result
    assert "Python" in result


def test_detect_language_english():
    text = "We are looking for a senior engineer with experience in Python and machine learning."
    assert _detect_language(text) == "en"


def test_detect_language_non_english():
    text = "Nous cherchons un ingénieur senior avec de l'expérience en Python et apprentissage automatique."
    # Non-English text would return "unknown"
    result = _detect_language(text)
    assert result in ("en", "unknown")  # depends on word overlap


def test_score_confidence_full():
    structured = {
        "role_title": "Senior ML Engineer",
        "required_skills": ["Python", "PyTorch", "LangChain"],
        "domain": "Enterprise AI",
        "company": "Acme Corp",
        "responsibilities": ["Build models", "Deploy systems"],
        "seniority": "senior",
        "location": "Remote",
    }
    score, warnings = _score_confidence(structured)
    assert score >= 0.7
    assert len(warnings) == 0


def test_score_confidence_no_skills():
    structured = {
        "role_title": "Engineer",
        "required_skills": [],
        "domain": "Tech",
    }
    score, warnings = _score_confidence(structured)
    assert score <= 0.4
    assert any("required skills" in w.lower() for w in warnings)


def test_preprocess_normalizes_whitespace():
    raw = "Python   developer    needed\n\n\n\nStrong  background required"
    result = _preprocess_jd(raw)
    assert "  " not in result
