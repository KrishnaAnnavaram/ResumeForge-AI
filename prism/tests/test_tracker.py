"""tests/test_tracker.py — Unit tests for Google Sheets tracker."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from core.tracker import log_application, update_application_status


SAMPLE_REPORT = {
    "final_ats_score":      85,
    "keyword_density_pct":  74.0,
    "keywords_matched":     ["LangGraph", "RAG", "FAISS"],
    "keywords_missing":     ["Kubeflow"],
    "must_haves_matched":   ["Python", "LangGraph"],
    "fact_check_passed":    True,
    "reflexion_loops_used": 2,
    "cover_letter_ai_risk": 0,
    "domain":               "Healthcare AI",
    "seniority":            "Senior",
}


def test_log_returns_false_on_auth_error():
    """Tracker failure is non-fatal — should return False, not raise."""
    with patch("core.tracker.get_gspread_client", side_effect=Exception("No creds")):
        result = log_application(
            company           = "TestCo",
            role              = "ML Engineer",
            status            = "Applied",
            ats_report        = SAMPLE_REPORT,
            resume_file       = "output/test_resume.txt",
            cover_letter_file = "output/test_cl.txt",
            thread_id         = "testco_mlengineer_20250101",
        )
    assert result is False


def test_log_returns_true_on_success():
    """Successful write returns True."""
    mock_ws     = MagicMock()
    mock_sheet  = MagicMock()
    mock_client = MagicMock()

    mock_sheet.worksheet.return_value = mock_ws
    mock_ws.row_values.return_value   = []   # Empty sheet → trigger header write
    mock_client.open_by_key.return_value = mock_sheet

    with patch("core.tracker.get_gspread_client", return_value=mock_client):
        result = log_application(
            company           = "Google",
            role              = "Senior ML Engineer",
            status            = "Applied",
            ats_report        = SAMPLE_REPORT,
            resume_file       = "output/google_resume.txt",
            cover_letter_file = "output/google_cl.txt",
            thread_id         = "google_seniorml_20250315",
            notes             = "Referral from John",
            job_url           = "https://careers.google.com/jobs/123",
        )
    assert result is True
    mock_ws.append_row.assert_called_once()


def test_update_returns_false_on_auth_error():
    """Status update failure is non-fatal — should return False."""
    with patch("core.tracker.get_gspread_client", side_effect=Exception("No creds")):
        result = update_application_status("Google", "Senior ML Engineer", "Interviewing")
    assert result is False


def test_log_to_apply_status():
    """'To Apply' status should work the same as 'Applied'."""
    with patch("core.tracker.get_gspread_client", side_effect=Exception("mock")):
        result = log_application(
            company           = "Anthropic",
            role              = "Staff ML Engineer",
            status            = "To Apply",
            ats_report        = SAMPLE_REPORT,
            resume_file       = "output/anthropic_resume.txt",
            cover_letter_file = "output/anthropic_cl.txt",
            thread_id         = "anthropic_staff_20250315",
        )
    assert result is False   # Fails gracefully without credentials
