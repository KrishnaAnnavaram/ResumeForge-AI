# Prism — AI Resume Optimizer

**Personal AI-powered resume optimizer for Krishna Annavaram.**
Takes a job description → outputs a perfectly ATS-optimized resume + cover letter + logs to Google Sheets.

---

## Pipeline Architecture

```
START
  ├─────────────────────────────────────────┐
  ▼                                         ▼
jd_cleaner                           resume_loader        ← PARALLEL
  │                                         │
  ▼                                         ▼
jd_intelligence                  resume_contextualizer    ← PARALLEL
  │                                         │
  │                                         ▼
  │                                  hybrid_indexer
  │                                         │
  └──────────────────┬──────────────────────┘
                     ▼
              hybrid_retriever                            ← waits for both
                     │
                     ▼
                  rewriter ◄──────────────────────────┐
                     │                                │
                     ▼                                │
                   critic                             │
                     │                                │
          ┌──────────┴──────────┐                     │
        pass                  retry               reflector
          │                                           │
          │           └───────────────────────────────┘
          ▼
      fact_checker     ← ─ ─ HITL INTERRUPT HERE ─ ─ ─
          │
          ▼
      ats_formatter
          │
          ▼
      voice_extractor
          │
          ▼
        humanizer
          │
          ▼
      cover_letter
          │
          ▼
    report_assembler
          │
          ▼
         END

  └─────────────────────────────────────────────────┘
  After output files saved → APPLICATION TRACKER PROMPT
  "Did you apply?" → logs row to Google Sheets automatically
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key
cp .env.example .env
# Edit .env → add your ANTHROPIC_API_KEY

# 3. (Optional) Set up Google Sheets tracker
# See credentials/README.md for 5-minute setup

# 4. Place Krishna's resume .docx in the project root or prism_files/

# 5. Run
python run.py optimize \
  --company "Anthropic" \
  --role "Staff ML Engineer" \
  --jd path/to/anthropic_jd.txt
```

---

## Commands

| Command | Description |
|---------|-------------|
| `python run.py optimize -c COMPANY -r ROLE -j JD_FILE` | Run full optimization + tracker |
| `python run.py status` | View application dashboard from Google Sheets |
| `python run.py update -c COMPANY -r ROLE -s Interviewing` | Update application status |

### Options for `optimize`

| Flag | Description |
|------|-------------|
| `--company / -c` | Company name (required) |
| `--role / -r` | Job role/title (required) |
| `--jd / -j` | Path to `.txt` JD file OR raw JD text (required) |
| `--thread` | Resume an existing thread ID |
| `--url` | Job posting URL (optional) |
| `--no-hitl` | Skip human review checkpoint (run end-to-end) |

---

## The 10 Flaws Fixed

| Old Approach | Prism Fix |
|---|---|
| Generic rewrite | Hybrid BM25 + ChromaDB retrieval finds exactly relevant sections |
| Keyword stuffing | Target 70-75%, hard ceiling 80% (research-backed) |
| Invented metrics | Fact Checker verifies against ground truth from actual .docx |
| One-shot rewrite | Reflexion loop: Critic → Reflector → Rewriter (max 3x) |
| AI-sounding output | Voice Extractor fingerprints style; Humanizer applies it |
| Biased critic | Separate agent persona — cold forensic auditor, no bias |
| No persistence | ChromaDB: local, persistent, zero server |
| Manual tracking | Auto-logs every application to Google Sheets |
| Static context | Contextual Retrieval: 2-sentence LLM context per chunk (+49% BM25 accuracy) |
| Cover letter clichés | 4-paragraph structure with banned opener list + AI risk score |

---

## Scoring Rubric (Critic Node)

| Dimension | Points | Criteria |
|---|---|---|
| Keyword Coverage | 25 | Keywords in context, both forms, 70-80% density |
| Bullet Quality | 25 | Action verbs, quantified, no pronouns, varied lengths |
| Structure | 25 | Standard headers, single-column, reverse-chrono, skills first |
| Humanness | 25 | No AI clichés, natural rhythm, sounds like real engineer |
| **Total** | **100** | **≥85 = pass; <85 = retry (max 3 loops)** |

---

## Google Sheets Tracker

**Sheet ID:** `1tsNo8KtZfI3h6twxXLLBCZjBPczWP1RYfB_ZScP5YPI`
**Setup:** See `credentials/README.md`

After every run, Prism asks:
- *"Did you apply?"* → logs as **Applied**
- *"Save as To Apply?"* → logs as **To Apply**
- Fail gracefully → saves JSON locally if no credentials

---

## Research Citations

- **Contextual Retrieval** (Anthropic, 2024): 2-sentence LLM context per chunk improves BM25 accuracy by 49%
- **RRF Fusion** (Cormack et al., 2009): k=60 standard in literature; BM25 + semantic > either alone
- **Reflexion** (Shinn et al., 2023): LLM self-reflection with external critique improves task accuracy
- **ATS Keyword Density**: 70-75% optimal; >80% triggers spam filters in modern ATS systems
- **Resume Length**: 2-page resumes get 2.9x more interviews for 5+ year candidates (Ladders Research, 2018)
- **all-MiniLM-L6-v2**: 384-dim sentence embeddings, ~14ms inference, strong semantic matching for technical text

---

## File Structure

```
prism/
├── .env                       ← API keys (never commit)
├── .env.example               ← Template
├── .gitignore
├── requirements.txt
├── README.md
├── run.py                     ← CLI entry point
├── credentials/
│   └── README.md              ← Google OAuth setup guide
├── core/
│   ├── __init__.py
│   ├── state.py               ← LangGraph TypedDict (30 fields)
│   ├── resume_parser.py       ← .docx → structured chunks + ChromaDB
│   ├── vector_store.py        ← BM25 + ChromaDB + RRF hybrid retrieval
│   ├── agents.py              ← All 15 agent node implementations
│   ├── graph.py               ← LangGraph pipeline builder
│   └── tracker.py             ← Google Sheets job application tracker
├── output/                    ← Generated resumes + cover letters
├── chroma_store/              ← Persistent vector DB (local, no server)
└── tests/
    ├── test_routing.py        ← Reflexion routing tests
    ├── test_parser.py         ← Resume parser tests
    └── test_tracker.py        ← Tracker tests
```

---

*Built by Krishna Annavaram — annavaramkrishna@gmail.com*
