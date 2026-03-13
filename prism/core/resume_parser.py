"""
core/resume_parser.py

Parse Krishna's resume .docx into structured sections and retrievable chunks.
Also builds the ChromaDB persistent vector store.
"""

import re
from pathlib import Path
from typing import Optional

from docx import Document
import chromadb
from chromadb.utils import embedding_functions


# ─────────────────────────────────────────────────────────────────────────────
# Parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

SECTION_KEYWORDS = {
    "summary":        ["summary", "profile", "objective", "about"],
    "experience":     ["experience", "employment", "work history", "career"],
    "education":      ["education", "academic", "degree", "university", "college"],
    "skills":         ["skills", "technical skills", "competencies", "technologies"],
    "certifications": ["certification", "certificate", "credential", "award"],
    "projects":       ["project", "portfolio"],
}

DATE_PATTERN = re.compile(
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|"
    r"April|June|July|August|September|October|November|December)"
    r"\s+\d{4}",
    re.IGNORECASE,
)

EMAIL_PATTERN   = re.compile(r"[\w.+-]+@[\w-]+\.\w{2,}")
PHONE_PATTERN   = re.compile(r"[\+\(]?\d[\d\s\-\(\)]{7,}\d")
LINKEDIN_PATTERN = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)
PERCENT_PATTERN = re.compile(r"\d+\.?\d*%")
YEAR_EXP_PATTERN = re.compile(r"\d+\s+years?", re.IGNORECASE)


def _is_section_header(para) -> Optional[str]:
    """Return section key if paragraph looks like a section header, else None."""
    text = para.text.strip()
    if not text:
        return None
    is_bold = any(run.bold for run in para.runs if run.text.strip())
    is_caps = text.isupper()
    is_short = len(text) < 40
    if not (is_bold or is_caps or is_short):
        return None
    lower = text.lower()
    for section, keywords in SECTION_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return section
    return None


def _is_bullet(para) -> bool:
    text = para.text.strip()
    if not text:
        return False
    if text[0] in ("•", "-", "*", "◦", "▪", "–", "→"):
        return True
    style_name = (para.style.name or "").lower()
    if "list" in style_name:
        return True
    # Indented paragraphs are often bullets
    if para.paragraph_format.left_indent and para.paragraph_format.left_indent > 0:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_resume_docx(docx_path: str) -> dict:
    """
    Parse Krishna's resume .docx into structured sections.

    Returns:
        {
            "contact":   {name, email, phone, location, linkedin},
            "summary":   "full text",
            "experience": [
                {title, company, location, dates, bullets, full_text}
            ],
            "education":  [{degree, school, dates, specialization}],
            "skills":     {raw_text, categories},
            "certifications": "...",
            "raw_full_text": "entire resume as plain text"
        }
    """
    doc = Document(docx_path)
    paragraphs = [p for p in doc.paragraphs if p.text.strip()]

    # ── Extract raw full text ─────────────────────────────────────────────
    raw_full_text = "\n".join(p.text.strip() for p in paragraphs)

    # ── Split into sections ───────────────────────────────────────────────
    sections: dict = {
        "contact_lines": [],
        "summary": [],
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
    }

    current_section = "contact_lines"
    for para in paragraphs:
        header = _is_section_header(para)
        if header:
            current_section = header
            continue
        sections[current_section].append(para)

    # ── Contact Info ──────────────────────────────────────────────────────
    contact_text = "\n".join(p.text.strip() for p in sections["contact_lines"])
    email_match   = EMAIL_PATTERN.search(contact_text)
    phone_match   = PHONE_PATTERN.search(contact_text)
    linkedin_match = LINKEDIN_PATTERN.search(contact_text)

    contact_lines = [p.text.strip() for p in sections["contact_lines"] if p.text.strip()]
    name = contact_lines[0] if contact_lines else ""

    # Guess location: look for a line with a city/state pattern
    location = ""
    for line in contact_lines:
        if re.search(r",\s*[A-Z]{2}", line) or any(
            x in line.lower() for x in ["usa", "india", "remote", "tx", "ca", "ny"]
        ):
            location = line
            break

    contact = {
        "name":     name,
        "email":    email_match.group() if email_match else "",
        "phone":    phone_match.group() if phone_match else "",
        "location": location,
        "linkedin": linkedin_match.group() if linkedin_match else "",
    }

    # ── Summary ───────────────────────────────────────────────────────────
    summary_text = " ".join(p.text.strip() for p in sections["summary"])

    # ── Experience ────────────────────────────────────────────────────────
    experience = []
    current_job = None

    for para in sections["experience"]:
        text = para.text.strip()
        if not text:
            continue

        # Detect job header lines:
        # Patterns: "Title | Company | Dates", "Title at Company", or lines with dates
        has_date = bool(DATE_PATTERN.search(text))
        is_title_line = (
            "|" in text
            or " at " in text.lower()
            or (has_date and len(text) < 120 and not _is_bullet(para))
        )

        if is_title_line and not _is_bullet(para):
            if current_job:
                current_job["full_text"] = (
                    f"{current_job['title']} at {current_job['company']} "
                    f"({current_job['location']}) | {current_job['dates']}\n"
                    + "\n".join(current_job["bullets"])
                )
                experience.append(current_job)

            # Parse the title line
            if "|" in text:
                parts = [p.strip() for p in text.split("|")]
                title    = parts[0] if len(parts) > 0 else text
                company  = parts[1] if len(parts) > 1 else ""
                dates    = parts[2] if len(parts) > 2 else ""
                location_job = parts[3] if len(parts) > 3 else ""
            else:
                title    = text
                company  = ""
                dates    = ""
                location_job = ""
                # Try to extract dates from following lines or same line
                date_match = DATE_PATTERN.search(text)
                if date_match:
                    dates = text[date_match.start():]
                    title = text[:date_match.start()].strip(" |–-")

            current_job = {
                "title":    title,
                "company":  company,
                "location": location_job,
                "dates":    dates,
                "bullets":  [],
                "full_text": "",
            }
        elif current_job is not None:
            # Subsequent lines: either company/date clarification or bullets
            if _is_bullet(para):
                bullet = text.lstrip("•-*◦▪–→ ").strip()
                current_job["bullets"].append(bullet)
            elif not current_job["company"] and not has_date:
                current_job["company"] = text
            elif not current_job["dates"] and has_date:
                current_job["dates"] = text
            else:
                current_job["bullets"].append(text)

    if current_job:
        current_job["full_text"] = (
            f"{current_job['title']} at {current_job['company']} "
            f"({current_job['location']}) | {current_job['dates']}\n"
            + "\n".join(current_job["bullets"])
        )
        experience.append(current_job)

    # ── Education ─────────────────────────────────────────────────────────
    education = []
    current_edu = None
    for para in sections["education"]:
        text = para.text.strip()
        if not text:
            continue
        has_date = bool(DATE_PATTERN.search(text))
        if has_date or any(
            kw in text.lower()
            for kw in ["university", "college", "institute", "bs ", "ms ", "phd", "b.tech", "m.tech", "bachelor", "master"]
        ):
            current_edu = {"degree": text, "school": "", "dates": "", "specialization": ""}
            education.append(current_edu)
        elif current_edu:
            if not current_edu["school"]:
                current_edu["school"] = text
            elif not current_edu["specialization"]:
                current_edu["specialization"] = text

    # ── Skills ────────────────────────────────────────────────────────────
    skills_raw = "\n".join(p.text.strip() for p in sections["skills"])
    skills_categories: dict = {}
    current_cat = "General"
    for para in sections["skills"]:
        text = para.text.strip()
        if not text:
            continue
        # Category headers: short, ends with ":" or is bold
        is_cat = (
            text.endswith(":")
            or any(run.bold for run in para.runs if run.text.strip())
            and len(text) < 40
        )
        if is_cat:
            current_cat = text.rstrip(":")
            skills_categories[current_cat] = []
        else:
            if current_cat not in skills_categories:
                skills_categories[current_cat] = []
            # Split by commas
            items = [s.strip() for s in re.split(r"[,;]", text) if s.strip()]
            skills_categories[current_cat].extend(items)

    # ── Certifications ────────────────────────────────────────────────────
    certs_text = "\n".join(p.text.strip() for p in sections["certifications"])

    return {
        "contact":        contact,
        "summary":        summary_text,
        "experience":     experience,
        "education":      education,
        "skills":         {"raw_text": skills_raw, "categories": skills_categories},
        "certifications": certs_text,
        "raw_full_text":  raw_full_text,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chunker
# ─────────────────────────────────────────────────────────────────────────────

def chunk_resume(parsed: dict) -> list:
    """
    Convert parsed resume dict into retrievable chunks (10-15 total).

    Each chunk:
        {id, section, role_rank, text, context, metadata, metrics}
    """
    chunks = []

    def _extract_metrics(text: str) -> list:
        metrics = PERCENT_PATTERN.findall(text)
        metrics += YEAR_EXP_PATTERN.findall(text)
        return list(set(metrics))

    # ── Summary chunk ──────────────────────────────────────────────────────
    if parsed.get("summary"):
        text = parsed["summary"]
        chunks.append({
            "id":       "summary",
            "section":  "summary",
            "role_rank": None,
            "text":     text,
            "context":  "",
            "metadata": {"section": "summary"},
            "metrics":  _extract_metrics(text),
        })

    # ── Experience chunks (one per job) ────────────────────────────────────
    for rank, job in enumerate(parsed.get("experience", []), start=1):
        text = job["full_text"] or (
            f"{job['title']} at {job['company']} | {job['dates']}\n"
            + "\n".join(job["bullets"])
        )
        chunks.append({
            "id":       f"exp_{rank-1}",
            "section":  "experience",
            "role_rank": rank,
            "text":     text,
            "context":  "",
            "metadata": {
                "section":   "experience",
                "company":   job.get("company", ""),
                "title":     job.get("title", ""),
                "dates":     job.get("dates", ""),
                "role_rank": rank,
            },
            "metrics":  _extract_metrics(text),
        })

    # ── Skills chunks (split by category) ─────────────────────────────────
    skills = parsed.get("skills", {})
    cats = skills.get("categories", {})
    if cats:
        # Group into ~2 chunks
        items = list(cats.items())
        mid = max(1, len(items) // 2)
        for i, batch in enumerate([items[:mid], items[mid:]]):
            if not batch:
                continue
            text = "\n".join(f"{cat}: {', '.join(vals)}" for cat, vals in batch)
            chunks.append({
                "id":       f"skills_{i}",
                "section":  "skills",
                "role_rank": None,
                "text":     text,
                "context":  "",
                "metadata": {"section": "skills", "categories": [c for c, _ in batch]},
                "metrics":  [],
            })
    elif skills.get("raw_text"):
        chunks.append({
            "id":       "skills_0",
            "section":  "skills",
            "role_rank": None,
            "text":     skills["raw_text"],
            "context":  "",
            "metadata": {"section": "skills"},
            "metrics":  [],
        })

    # ── Education chunk ────────────────────────────────────────────────────
    edu_list = parsed.get("education", [])
    if edu_list:
        text = "\n".join(
            f"{e.get('degree','')} — {e.get('school','')} {e.get('dates','')} {e.get('specialization','')}"
            for e in edu_list
        )
        chunks.append({
            "id":       "education",
            "section":  "education",
            "role_rank": None,
            "text":     text.strip(),
            "context":  "",
            "metadata": {"section": "education"},
            "metrics":  [],
        })

    # ── Certifications chunk (if present) ──────────────────────────────────
    if parsed.get("certifications"):
        text = parsed["certifications"]
        chunks.append({
            "id":       "certifications",
            "section":  "certifications",
            "role_rank": None,
            "text":     text,
            "context":  "",
            "metadata": {"section": "certifications"},
            "metrics":  [],
        })

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Verified metrics extractor
# ─────────────────────────────────────────────────────────────────────────────

def extract_verified_metrics(parsed: dict) -> dict:
    """
    Regex-extract ALL metrics from full resume text.
    Returns {metric: context_description}
    """
    text = parsed["raw_full_text"]
    metrics = {}

    # Percentages (including ranges like 88-92%)
    for match in re.finditer(r"\d+\.?\d*(?:-\d+\.?\d*)?%", text):
        pct = match.group()
        start = max(0, match.start() - 60)
        context = text[start:match.end()].strip()
        # Normalize: strip leading partial words
        context = re.sub(r"^\S*\s", "", context).strip()
        metrics[pct] = context

    # "X years" patterns
    for match in re.finditer(r"\d+\s+years?", text, re.IGNORECASE):
        metrics[match.group()] = "years of experience"

    return metrics


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB vector store builder
# ─────────────────────────────────────────────────────────────────────────────

def build_vector_store(chunks: list, persist_dir: str = "./chroma_store"):
    """
    Build ChromaDB collection with sentence-transformer embeddings.

    Model: all-MiniLM-L6-v2
    - 384 dimensions
    - Fast inference (~14ms per query)
    - Downloads once (~90MB), cached locally after
    - Runs entirely locally — no API calls

    If collection already has documents → return it (don't re-embed).
    """
    client = chromadb.PersistentClient(path=persist_dir)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_or_create_collection(
        name="krishna_resume",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == 0:
        collection.add(
            documents=[c["text"] for c in chunks],
            metadatas=[
                {k: str(v) for k, v in c["metadata"].items()}
                for c in chunks
            ],
            ids=[c["id"] for c in chunks],
        )

    return collection
