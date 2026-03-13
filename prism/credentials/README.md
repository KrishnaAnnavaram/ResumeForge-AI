# Google Sheets Setup for Prism

## One-time setup (~5 minutes)

### Option A: Service Account (Recommended — fully automatic, no browser popup)

1. Go to https://console.cloud.google.com
2. Create a new project called **"Prism"**
3. Enable the Google Sheets API:
   - APIs & Services → Library → search "Google Sheets API" → Enable
4. Create a Service Account:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Name it `prism-tracker` → Done
5. Download the JSON key:
   - Click the service account → Keys → Add Key → Create new key → JSON
   - Save as: `credentials/service_account.json`
6. Share your Google Sheet with the service account email:
   - Open the sheet → Share → paste the service account email
     (looks like `prism-tracker@your-project.iam.gserviceaccount.com`)
   - Set access to **Editor** → Done

Your sheet: https://docs.google.com/spreadsheets/d/1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI

---

### Option B: OAuth (uses your own Google account — browser popup on first run)

1. Go to https://console.cloud.google.com
2. APIs & Services → Credentials → Create Credentials → OAuth client ID
3. Application type: **Desktop app**
4. Download JSON → save as `credentials/oauth_credentials.json`
5. First run will open browser for one-time authorization
6. After auth, token is cached as `credentials/token.json` automatically
   (subsequent runs need no browser)

---

## Add to `.env` file

```env
GOOGLE_SHEET_ID=1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI

# Option A (Service Account):
GOOGLE_CREDS_PATH=credentials/service_account.json

# Option B (OAuth):
# GOOGLE_OAUTH_PATH=credentials/oauth_credentials.json
```

---

## What happens if credentials are missing?

Prism is designed to fail gracefully:
- If Google Sheets write fails → data saved locally as `output/{thread_id}_tracker.json`
- All other Prism features (resume + cover letter) work without Google credentials
- You can add the row manually to the sheet later

---

## Sheet columns (auto-filled by Prism)

| Col | Header | Source |
|-----|--------|--------|
| A | Date Applied | Auto |
| B | Company | Auto |
| C | Role | Auto |
| D | Status | Auto (Applied / To Apply) |
| E | ATS Score | Auto |
| F | Keyword Density % | Auto |
| G | Keywords Matched | Auto (e.g. 18/24) |
| H | Must-Haves Matched | Auto |
| I | Fact Check | Auto (PASS/FAIL) |
| J | Reflexion Loops | Auto |
| K | Cover Letter Risk | Auto (0-100, lower = better) |
| L | JD Domain | Auto |
| M | Seniority | Auto |
| N | Resume File | Auto (local path) |
| O | Cover Letter File | Auto (local path) |
| P | Notes | You fill at prompt |
| Q | Follow Up Date | You fill manually |
| R | Interview Date | You fill manually |
| S | Outcome | You fill manually |
| T | Salary Range | Auto (if in JD) |
| U | Job URL | You fill at prompt |
| V | Thread ID | Auto (for re-running Prism) |
