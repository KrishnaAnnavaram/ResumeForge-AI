"""Tests for Gap Analyzer logic."""
import pytest
from careeros.agents.gap_analyzer_agent import _skill_in_evidence


def test_skill_found_in_evidence():
    evidence = [
        {
            "bullet_id": "abc123",
            "content": "Built RAG pipeline using LangChain",
            "skills_used": ["Python", "LangChain", "RAG"],
            "metrics": ["40% latency reduction"],
        }
    ]
    found, ids = _skill_in_evidence("LangChain", evidence)
    assert found is True
    assert "abc123" in ids


def test_skill_not_in_evidence():
    evidence = [
        {
            "bullet_id": "abc123",
            "content": "Built data pipelines",
            "skills_used": ["Python", "Spark"],
            "metrics": [],
        }
    ]
    found, ids = _skill_in_evidence("Kubernetes", evidence)
    assert found is False
    assert ids == []


def test_skill_case_insensitive():
    evidence = [
        {
            "bullet_id": "abc123",
            "content": "Used pytorch for training",
            "skills_used": ["PyTorch", "Python"],
            "metrics": [],
        }
    ]
    found, ids = _skill_in_evidence("pytorch", evidence)
    assert found is True


def test_empty_evidence():
    found, ids = _skill_in_evidence("Python", [])
    assert found is False
    assert ids == []
