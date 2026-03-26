# CLAUDE.md — Resume AI Agent

This file is read by Claude Code before every task. It contains the complete system specification.
Do not skip this file. Read it fully before writing any code.

---

## Project overview

Personal resume generation system. Multi-user. Multi-LLM. User pastes a job description, the system
generates an ATS-optimised resume and cover letter tailored to that JD, and tracks all applications
in a log table.

**Tech stack:**
- Frontend: React 18 + Tailwind CSS + TanStack Query + React Router + Zustand
- Backend: Python 3.11 + FastAPI + LangGraph
- Database: Supabase (PostgreSQL + pgvector + Supabase Storage)
- Cache: Upstash Redis (profile cache + ATS score cache)
- LLMs: Claude (Anthropic) + GPT-4o (OpenAI)
- Orchestration: LangGraph with PostgresSaver checkpointer wired to Supabase
- Protocol: MCP (Model Context Protocol) — 5 custom servers
- PDF rendering: WeasyPrint (headless PDF from HTML templates)

**Repo structure:**
```
resume-ai-agent/
├── frontend/                  # React + Tailwind
│   ├── src/
│   │   ├── components/        # One file per screen
│   │   ├── hooks/             # useGraphStatus · useProfile
│   │   ├── lib/               # supabase.ts · api.ts
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.ts
├── backend/                   # Python · FastAPI
│   ├── agents/                # LangGraph nodes + graph
│   ├── mcp_servers/           # 5 MCP server files
│   ├── llm/                   # claude_client.py · gpt_client.py
│   ├── api/                   # routes.py · auth.py
│   ├── main.py
│   └── requirements.txt
├── supabase/
│   └── migrations/            # 6 SQL migration files
├── CLAUDE.md                  # This file
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## CRITICAL — Multi-LLM responsibilities

**Claude does NOT write bullet points. GPT-4o does NOT score, structure, or generate PDFs.**
Keep this split at all times. Do not consolidate to one LLM.

### Claude (Anthropic)

Model: `claude-opus-4-5` for ATS analysis. `claude-sonnet-4-5` for resume assembly + cover letter.

Responsible for:
- **ATS analyzer agent** — read and deeply understand the JD, extract structured keywords
  (hard skills, soft skills, tools, certifications, action verbs, seniority level, min years),
  compute ATS match score against user profile, build the full rich gap JSON
- **ATS re-score agent** — score the newly written resume using same ATS logic, verify it hits ≥ 95%
- **Resume assembler** — take GPT-4o's rewritten bullets, assemble full structured resume,
  write the summary section and skills section in Claude's own voice, ensure coherence
- **Cover letter agent** — generate personalised cover letter using the user's soft skills,
  weave them naturally into achievement-based prose
- **PDF generation** — pass assembled resume/cover letter to Doc gen MCP for PDF rendering

### GPT-4o (OpenAI)

Model: `gpt-4o`

Responsible for:
- **Bullet point rewriting ONLY**
- Receives: each original experience bullet from the user's profile + the matching rewrite hint
  from Claude's gap JSON
- Returns: rewritten bullet as a string — punchy, varied, achievement-focused, keyword-injected
- Called inside `backend/agents/resume_writer.py` via `gpt_client.py`
- Output is a JSON array of rewritten bullets
- GPT-4o never sees the full resume, never writes summaries, never scores anything

### Why this split

GPT-4o produces more natural, varied achievement prose for bullet points.
Claude is superior at structured reasoning, scoring, semantic understanding, and document coherence.
This combination produces better resumes than either model alone.

---

## LangGraph graph — backend/agents/graph.py

### State object — backend/agents/state.py

```python
from typing import TypedDict, Optional

class ResumeState(TypedDict):
    # Inputs — set at graph start
    user_id: str
    job_id: str
    jd_text: str

    # ATS analysis stage
    ats_score: float
    ats_gap: dict              # full rich gap JSON — see schema below
    jd_keywords: dict

    # Generation stage
    resume_text: str
    resume_version: int
    retry_count: int

    # User decision fields
    user_confirmed: bool       # Gate 1 — generate resume?
    is_confirmed: bool         # Gate 2 — confirm this version?
    wants_cover_letter: bool   # Gate 3 — generate cover letter?

    # Output fields
    resume_id: str
    cover_letter_text: str
    cover_letter_id: str
    resume_pdf_url: str
    cover_pdf_url: str

    # Feedback fields
    applied: bool
    applied_on: Optional[str]
    feedback_rating: int       # 1–5
    feedback_notes: str
```

### Nodes (in order)

1. `ats_analyzer` — Claude node
2. `show_ats` — interrupt node (human-in-the-loop, no LLM)
3. `resume_writer` — GPT-4o bullets → Claude assembly
4. `ats_rescorer` — Claude node
5. `show_resume` — interrupt node (human-in-the-loop)
6. `cover_letter_ask` — interrupt node (asks user gate 3)
7. `cover_letter` — Claude node
8. `show_cover_letter` — interrupt node
9. `feedback_log` — writes to Supabase

### Conditional edges

```python
def route_after_ats(state: ResumeState) -> str:
    if state["user_confirmed"]:
        return "resume_writer"
    return END

def route_after_rescore(state: ResumeState) -> str:
    if state["ats_score"] >= 95 or state["retry_count"] >= 3:
        return "show_resume"
    return "resume_writer"

def route_after_resume_confirm(state: ResumeState) -> str:
    if state["wants_cover_letter"]:
        return "cover_letter"
    return "feedback_log"
```

### Graph compilation

```python
from langgraph.checkpoint.postgres import PostgresSaver
import os

checkpointer = PostgresSaver.from_conn_string(os.environ["SUPABASE_DB_URL"])

graph = StateGraph(ResumeState)
# add all nodes
# add all edges and conditional edges
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["show_ats", "show_resume", "cover_letter_ask", "show_cover_letter"]
)
```

### Key constants

- ATS pass threshold: **95**
- Max retries: **3**
- Cover letter: **ask first** — never auto-generate

---

## MCP servers — backend/mcp_servers/

**Hard rule: agents NEVER import the Supabase client directly. All DB access goes through Storage MCP.**

Each MCP server is a class with async tool methods. Agents call tools via:
```python
result = await mcp.call_tool(server="profile-mcp", tool="get_profile", input={"user_id": user_id})
```

Every tool validates `user_id` against `auth.uid()` before executing.
Every tool returns a standard error format on failure: `{"error": str, "code": str}`.

### profile_mcp.py

Tools:
- `get_profile(user_id: str)` → full profile object
- `get_resume_text(user_id: str)` → plain text of master resume
- `get_skills(user_id: str)` → skills_json array `[{skill, level, years}]`
- `get_soft_skills(user_id: str)` → soft_skills_json array `["leadership", ...]`
- `get_experience(user_id: str)` → experience_json array `[{company, title, years, bullets[]}]`
- `update_profile(user_id: str, fields: dict)` → updated profile + invalidates Redis cache

Caching: `get_profile`, `get_skills`, `get_soft_skills`, `get_experience` all read from
Redis first (`profile:{user_id}` key, TTL 30 min). Fall back to Supabase on miss.

### ats_mcp.py

Tools (pure computation — no DB writes):
- `extract_jd_keywords(jd_text: str)` → `{hard_skills[], soft_skills[], tools[], certifications[], action_verbs[], min_years}`
- `score_resume(resume_text: str, jd_keywords: dict, profile_skills: list)` → `{overall_score: float, section_scores: {summary, skills, experience, education, certifications}}`
- `get_match_list(profile_skills: list, jd_keywords: dict)` → `matched_keywords[]`
- `get_gap_list(profile_skills: list, jd_keywords: dict, resume_text: str)` → `missing_keywords[]`
- `get_experience_gaps(jd_text: str, experience_json: list)` → `[{gap: str, action: str}]`
- `build_gap_json(score_result, match_result, gap_result, resume_text)` → full rich gap JSON (see schema)

### storage_mcp.py

Tools (only server that writes to Supabase DB):
- `save_job(user_id, company_name, job_title, jd_text, keywords_json, ats_score, gap_json)` → `{job_id: uuid}`
- `save_resume(user_id, job_id, version, resume_text, ats_score_final)` → `{resume_id: uuid}` — sets is_active=true, previous version is_active=false
- `confirm_resume(resume_id: uuid)` → sets is_confirmed=true, confirmed_at=now()
- `save_cover_letter(user_id, resume_id, job_id, generated_text, soft_skills_used, pdf_url)` → `{cover_letter_id: uuid}`
- `get_resume_versions(job_id, user_id)` → `[{resume_id, version, ats_score_final, is_confirmed, created_at}]`
- `get_job_history(user_id, limit)` → recent jobs list for log table

### docgen_mcp.py

Tools:
- `render_resume_pdf(resume_text, profile, template, user_id, job_id, version)` → `{pdf_url: str}` — uploads to Supabase Storage at `/{user_id}/jobs/{job_id}/resume_v{n}.pdf`
- `render_cover_pdf(cover_text, profile, company, user_id, job_id)` → `{pdf_url: str}` — uploads to `/{user_id}/jobs/{job_id}/cover.pdf`
- `get_download_url(storage_path, user_id)` → fresh signed URL (regenerates if expired)
- `list_templates()` → `[{id, name, preview_url}]`

Uses WeasyPrint to render HTML templates to PDF. Templates live in `backend/templates/`.

### log_mcp.py

Tools:
- `append_log(user_id, job_id, resume_id, cover_letter_id, applied, applied_on, feedback_rating, feedback_notes)` → `{log_id: uuid}` — cover_letter_id is nullable
- `mark_applied(log_id, applied_on)` → updates applied=true for existing log row
- `get_all_logs(user_id, limit, offset)` → paginated log rows joined with jobs + resumes
- `filter_logs(user_id, applied, min_score, date_from, date_to)` → filtered rows
- `get_stats(user_id)` → `{total_applications, total_applied, avg_ats_score, avg_rating}`

---

## Supabase schema — 6 tables

All tables include: `id uuid DEFAULT gen_random_uuid() PRIMARY KEY`, `user_id uuid REFERENCES auth.users(id)`, `created_at timestamptz DEFAULT now()`.

All tables have Row Level Security enabled with policy: `USING (user_id = auth.uid())`.

### profiles

```sql
CREATE TABLE profiles (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) UNIQUE NOT NULL,
  full_name text,
  email text,
  phone text,
  linkedin_url text,
  raw_resume_text text,
  skills_json jsonb DEFAULT '[]',
  soft_skills_json jsonb DEFAULT '[]',
  experience_json jsonb DEFAULT '[]',
  education_json jsonb DEFAULT '[]',
  certifications_json jsonb DEFAULT '[]',
  master_resume_url text,
  embedding vector(1536),
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

### jobs

```sql
CREATE TABLE jobs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) NOT NULL,
  company_name text,
  job_title text,
  jd_raw_text text NOT NULL,
  jd_keywords_json jsonb DEFAULT '{}',
  ats_score_initial numeric(5,2),
  ats_gap_json jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now()
);
```

ats_gap_json structure:
```json
{
  "missing_keywords": ["GraphQL", "Docker", "CI/CD"],
  "experience_gaps": [
    {"gap": "JD needs 5+ yrs — resume shows 3 yrs", "action": "Reframe to show scope not just time"},
    {"gap": "Team lead experience not mentioned", "action": "Surface leadership from existing bullets"}
  ],
  "section_scores": {
    "summary": 55,
    "skills": 60,
    "experience": 70,
    "education": 90,
    "certifications": 80
  },
  "rewrite_hints": [
    {"section": "summary", "hint": "Lead with cloud and CI/CD experience"},
    {"section": "experience", "hint": "Add Docker and Lambda to job 1 bullets"},
    {"section": "skills", "hint": "Add GraphQL, CI/CD, containerisation"}
  ]
}
```

### resumes

```sql
CREATE TABLE resumes (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) NOT NULL,
  job_id uuid REFERENCES jobs(id) NOT NULL,
  version integer NOT NULL DEFAULT 1,
  generated_text text,
  ats_score_final numeric(5,2),
  pdf_url text,
  is_active boolean DEFAULT true,
  is_confirmed boolean DEFAULT false,
  confirmed_at timestamptz,
  embedding vector(1536),
  created_at timestamptz DEFAULT now()
);
```

### cover_letters

```sql
CREATE TABLE cover_letters (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) NOT NULL,
  resume_id uuid REFERENCES resumes(id) NOT NULL,
  job_id uuid REFERENCES jobs(id) NOT NULL,
  generated_text text,
  soft_skills_used jsonb DEFAULT '[]',
  pdf_url text,
  created_at timestamptz DEFAULT now()
);
```

### application_logs

```sql
CREATE TABLE application_logs (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) NOT NULL,
  job_id uuid REFERENCES jobs(id) NOT NULL,
  resume_id uuid REFERENCES resumes(id) NOT NULL,
  cover_letter_id uuid REFERENCES cover_letters(id),
  applied boolean DEFAULT false,
  applied_on date,
  feedback_rating smallint CHECK (feedback_rating BETWEEN 1 AND 5),
  feedback_notes text,
  logged_at timestamptz DEFAULT now()
);
```

### RLS policies (006_enable_rls_policies.sql)

```sql
-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cover_letters ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_logs ENABLE ROW LEVEL SECURITY;

-- Policy for each table (repeat pattern for all)
CREATE POLICY "Users see own profiles" ON profiles
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users see own jobs" ON jobs
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users see own resumes" ON resumes
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users see own cover letters" ON cover_letters
  FOR ALL USING (user_id = auth.uid());

CREATE POLICY "Users see own logs" ON application_logs
  FOR ALL USING (user_id = auth.uid());
```

### pgvector setup

```sql
-- Run this before migrations
CREATE EXTENSION IF NOT EXISTS vector;

-- Index for fast similarity search
CREATE INDEX ON profiles USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON resumes USING ivfflat (embedding vector_cosine_ops);
```

---

## Redis cache — Upstash

```python
# Key patterns
PROFILE_KEY = "profile:{user_id}"           # TTL: 1800s (30 min)
ATS_KEY     = "ats:{user_id}:{job_id}"       # TTL: 3600s (60 min)

# Invalidation rules
# - Call redis.delete(PROFILE_KEY) inside update_profile() in profile_mcp.py
# - ATS cache invalidates naturally on TTL — no manual invalidation needed
```

---

## FastAPI routes — backend/api/routes.py

```
POST   /api/graph/run              # Start a new LangGraph run — returns run_id
GET    /api/graph/status/{run_id}  # Poll for graph status: running | interrupted | complete
POST   /api/graph/resume/{run_id}  # Resume graph after interrupt — accepts state updates
GET    /api/resume/{resume_id}     # Get resume text + PDF URL
GET    /api/logs                   # Get all logs for current user
POST   /api/profile                # Create/update profile
GET    /api/profile                # Get current user profile
```

All routes require a valid Supabase JWT in the `Authorization: Bearer <token>` header.
Validate using `backend/api/auth.py` middleware — decode JWT with Supabase public key,
extract `user_id`, attach to request context.

---

## Frontend — React + Tailwind

### Routes

```
/              → JDInput.tsx       (Screen 1)
/ats           → ATSDashboard.tsx  (Screen 2)
/resume        → ResumePreview.tsx (Screen 3)
/cover-letter  → CoverLetter.tsx   (Screen 4)
/logs          → LogTable.tsx      (Screen 5)
```

### Global state — Zustand store

```typescript
interface AppStore {
  runId: string | null
  currentScreen: 'jd' | 'ats' | 'resume' | 'cover' | 'logs'
  userId: string | null
  jobId: string | null
  setRunId: (id: string) => void
  setScreen: (screen: string) => void
}
```

### LangGraph polling — useGraphStatus.ts

Poll `/api/graph/status/{run_id}` every 2 seconds.
When status is `"interrupted"` with `interrupt_node: "show_ats"` → navigate to `/ats`.
When status is `"interrupted"` with `interrupt_node: "show_resume"` → navigate to `/resume`.
When status is `"interrupted"` with `interrupt_node: "cover_letter_ask"` → navigate to `/cover-letter`.
When status is `"complete"` → navigate to `/logs`.

### Screen specifications

**Screen 1 — JDInput.tsx**
- Two text inputs: company_name, job_title
- Large textarea: jd_text (min-height 120px)
- Profile sidebar: shows user name, master_resume_url, skill count, top 5 skills
- Primary button: "Analyse ATS score →" — calls POST /api/graph/run
- On success: stores run_id in Zustand, starts polling

**Screen 2 — ATSDashboard.tsx**
- Large score display (overall ats_score as %)
- 5 horizontal bars: keywords, experience, skills, education, format (from section_scores)
- Section scores grid (5 cells)
- Matched keywords as green pills (from match_list)
- Missing keywords as red pills (from missing_keywords)
- Experience gaps list with action hints (from experience_gaps)
- Two buttons: "Generate optimised resume →" (sets user_confirmed=true, resumes graph) | "Not now" (ends)

**Screen 3 — ResumePreview.tsx**
- Full resume text rendered as formatted paper
- Injected keywords highlighted in amber (#FAEEDA background)
- Version history sidebar: shows all versions with ATS score
- Final ATS score badge (green if ≥ 95%)
- Buttons: "Confirm + download PDF" (sets is_confirmed=true) | "Regenerate ↻" | "Preview full PDF"

**Screen 4 — CoverLetter.tsx**
- Gate 3 ask state: title + sub + two buttons ("Yes, generate" | "Skip")
- Generated state: cover letter text, soft skills used as green pills, download + regenerate buttons
- Soft skill highlights in cover letter text shown in green (#E1F5EE background)
- "Continue to feedback →" button after generation

**Screen 5 — LogTable.tsx**
- 4 stat cards: total applications, total applied, avg ATS score, avg rating
- Filter bar: status pills (All/Applied/Pending) + score filters (90%+, 80%+) + search input
- Table: company+role, ATS score, status badge, star rating, applied date, view button
- Status badges: Applied (green), Pending (amber), Not applied (red)

---

## Environment variables — .env.example

```bash
# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_DB_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres

# Redis
UPSTASH_REDIS_URL=https://...upstash.io
UPSTASH_REDIS_TOKEN=...

# App
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
SECRET_KEY=your-secret-key-here
```

---

## Python requirements — backend/requirements.txt

```
fastapi==0.115.0
uvicorn==0.30.0
langgraph==0.2.0
langchain-anthropic==0.2.0
langchain-openai==0.2.0
anthropic==0.34.0
openai==1.47.0
supabase==2.7.0
psycopg2-binary==2.9.9
redis==5.0.0
weasyprint==62.0
python-jose==3.3.0
python-dotenv==1.0.0
pydantic==2.8.0
httpx==0.27.0
```

---

## Build order for Claude Code

Follow this order exactly. Each step depends on the previous.

```
Step 1  — supabase/migrations/
          Run 001 through 006 in order.
          Enable pgvector extension first.

Step 2  — backend/mcp_servers/
          Build all 5 MCP servers.
          Start with profile_mcp.py and storage_mcp.py.
          Test each tool independently before moving on.

Step 3  — backend/llm/
          claude_client.py — Anthropic SDK wrapper with retry logic
          gpt_client.py — OpenAI SDK wrapper with retry logic

Step 4  — backend/agents/state.py
          ResumeState TypedDict — every field listed in this file.

Step 5  — backend/agents/ (individual node files)
          ats_analyzer.py first (used by all other nodes)
          resume_writer.py second (GPT-4o bullets → Claude assembly)
          ats_rescorer.py third
          cover_letter.py fourth
          feedback_log.py fifth

Step 6  — backend/agents/graph.py
          Wire all nodes into StateGraph.
          Add all conditional edges.
          Compile with PostgresSaver checkpointer.
          Set interrupt_before list.

Step 7  — backend/api/
          auth.py — Supabase JWT middleware
          routes.py — all 7 API endpoints

Step 8  — backend/main.py
          FastAPI app, include routers, CORS config

Step 9  — frontend/src/lib/
          supabase.ts, api.ts

Step 10 — frontend/src/hooks/
          useGraphStatus.ts, useProfile.ts

Step 11 — frontend/src/components/
          Build in screen order: JDInput → ATSDashboard → ResumePreview → CoverLetter → LogTable

Step 12 — frontend/src/App.tsx
          React Router setup, nav, Zustand provider
```

---

## Common mistakes to avoid

- Do NOT call the Supabase client inside any agent file. Use Storage MCP only.
- Do NOT use GPT-4o for anything other than bullet rewriting.
- Do NOT auto-generate cover letters — always ask the user first (Gate 3).
- Do NOT store PDF files in the database — store only the Supabase Storage URL.
- Do NOT skip RLS policies — every table must have them.
- Do NOT hardcode API keys — always read from environment variables.
- Do NOT use synchronous Supabase calls in async FastAPI routes — use the async client.
- The retry loop max is 3. After 3 retries, accept the best score regardless.
- The ATS pass threshold is 95, not 100.
- `cover_letter_id` in application_logs is nullable — the user may skip cover letter.
