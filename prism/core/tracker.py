"""
core/tracker.py — Google Sheets Job Application Tracker

Connects to Krishna's Google Sheet and logs every application.
Supports both Service Account (headless) and OAuth (browser) auth.

Sheet ID: 1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI
"""

import os
import json
from datetime import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials as SACredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.environ.get(
    "GOOGLE_SHEET_ID",
    "1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI",
)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Date Applied",     # A
    "Company",          # B
    "Role",             # C
    "Status",           # D  Applied | To Apply | Interviewing | Offer | Rejected | Ghosted
    "ATS Score",        # E
    "Keyword Density %",# F
    "Keywords Matched", # G  e.g. 18/24
    "Must-Haves Matched",# H e.g. 8/10
    "Fact Check",       # I  PASS | FAIL
    "Reflexion Loops",  # J
    "Cover Letter Risk",# K  lower is better
    "JD Domain",        # L
    "Seniority",        # M
    "Resume File",      # N
    "Cover Letter File",# O
    "Notes",            # P  free text
    "Follow Up Date",   # Q  Krishna fills manually
    "Interview Date",   # R  Krishna fills manually
    "Outcome",          # S  Krishna fills manually
    "Salary Range",     # T
    "Job URL",          # U
    "Thread ID",        # V  for re-running Prism
]


def get_gspread_client():
    """
    Get authenticated gspread client.
    Tries Service Account first, falls back to OAuth.
    """
    sa_path    = os.environ.get("GOOGLE_CREDS_PATH", "credentials/service_account.json")
    oauth_path = os.environ.get("GOOGLE_OAUTH_PATH", "credentials/oauth_credentials.json")
    token_path = "credentials/token.json"

    # ── Service Account (preferred — no browser popup) ────────────────────
    if Path(sa_path).exists():
        creds = SACredentials.from_service_account_file(sa_path, scopes=SCOPES)
        return gspread.authorize(creds)

    # ── OAuth with cached token ───────────────────────────────────────────
    creds = None
    if Path(token_path).exists():
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif Path(oauth_path).exists():
            flow = InstalledAppFlow.from_client_secrets_file(oauth_path, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise ValueError(
                "No Google credentials found.\n"
                "Please follow setup instructions in credentials/README.md"
            )
        Path("credentials").mkdir(exist_ok=True)
        Path(token_path).write_text(creds.to_json())

    return gspread.authorize(creds)


def ensure_sheet_headers(worksheet):
    """Check if header row exists. If not, create it."""
    try:
        existing = worksheet.row_values(1)
        if existing != HEADERS:
            worksheet.update("A1", [HEADERS])
            worksheet.format(
                "A1:V1",
                {
                    "textFormat":          {"bold": True},
                    "backgroundColor":     {"red": 0.2, "green": 0.2, "blue": 0.6},
                    "horizontalAlignment": "CENTER",
                },
            )
    except Exception:
        worksheet.update("A1", [HEADERS])


def log_application(
    company: str,
    role: str,
    status: str,
    ats_report: dict,
    resume_file: str,
    cover_letter_file: str,
    thread_id: str,
    notes: str = "",
    job_url: str = "",
    salary_range: str = "",
) -> bool:
    """
    Log a job application to the Google Sheet.

    Returns True on success, False on failure.
    Failure is non-fatal — Prism continues even if Sheets write fails.
    """
    try:
        client = get_gspread_client()
        sheet  = client.open_by_key(SHEET_ID)

        # Use "Job Applications" tab or fall back to first sheet
        try:
            ws = sheet.worksheet("Job Applications")
        except gspread.WorksheetNotFound:
            try:
                ws = sheet.worksheet("Sheet1")
            except gspread.WorksheetNotFound:
                ws = sheet.add_worksheet("Job Applications", rows=1000, cols=22)

        ensure_sheet_headers(ws)

        keywords_matched = ats_report.get("keywords_matched", [])
        keywords_missing = ats_report.get("keywords_missing", [])
        all_kw_count     = len(keywords_matched) + len(keywords_missing)
        must_matched     = ats_report.get("must_haves_matched", [])
        # Approximate total must-haves
        must_total       = len(must_matched) + 2

        row = [
            datetime.now().strftime("%Y-%m-%d") if status == "Applied" else "",
            company,
            role,
            status,
            str(ats_report.get("final_ats_score", "")),
            str(round(ats_report.get("keyword_density_pct", 0), 1)),
            f"{len(keywords_matched)}/{all_kw_count}",
            f"{len(must_matched)}/{must_total}",
            "PASS" if ats_report.get("fact_check_passed", False) else "FAIL",
            str(ats_report.get("reflexion_loops_used", "")),
            str(ats_report.get("cover_letter_ai_risk", "")),
            ats_report.get("domain", ""),
            ats_report.get("seniority", ""),
            resume_file,
            cover_letter_file,
            notes,
            "",  # Follow Up Date — Krishna fills manually
            "",  # Interview Date — Krishna fills manually
            "",  # Outcome — Krishna fills manually
            salary_range,
            job_url,
            thread_id,
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        return True

    except Exception as e:
        print(f"[Tracker] Warning: Could not write to Google Sheets: {e}")
        print("[Tracker] Application data saved locally — you can add it manually.")
        return False


def get_application_stats() -> dict:
    """
    Read the sheet and return summary stats for the dashboard.
    """
    try:
        client   = get_gspread_client()
        sheet    = client.open_by_key(SHEET_ID)
        ws       = sheet.get_worksheet(0)
        all_rows = ws.get_all_records()

        if not all_rows:
            return {"total": 0, "by_status": {}}

        by_status: dict = {}
        for row in all_rows:
            s = row.get("Status", "Unknown")
            by_status[s] = by_status.get(s, 0) + 1

        scores = [
            int(r["ATS Score"])
            for r in all_rows
            if r.get("ATS Score") and str(r["ATS Score"]).isdigit()
        ]

        return {
            "total":         len(all_rows),
            "by_status":     by_status,
            "avg_ats_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "recent":        all_rows[-5:],
        }

    except Exception as e:
        return {"error": str(e), "total": 0}


def update_application_status(company: str, role: str, new_status: str) -> bool:
    """
    Find an existing row by company+role and update its Status column.
    """
    try:
        client = get_gspread_client()
        sheet  = client.open_by_key(SHEET_ID)
        ws     = sheet.get_worksheet(0)

        company_col = ws.col_values(2)  # Column B = Company
        role_col    = ws.col_values(3)  # Column C = Role

        for i, (c, r) in enumerate(zip(company_col, role_col), start=1):
            if c.lower() == company.lower() and r.lower() == role.lower():
                ws.update_cell(i, 4, new_status)  # Column D = Status
                return True

        return False

    except Exception:
        return False
