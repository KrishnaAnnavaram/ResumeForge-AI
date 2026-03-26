/**
 * api.ts — Typed API client for the ResumeForge AI backend.
 *
 * All calls attach the Supabase JWT automatically.
 * Throws structured ApiError on non-2xx responses.
 */
import { getAuthToken } from "./supabase";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? "";

// ── Error type ────────────────────────────────────────────────────────────────
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Base fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getAuthToken();

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.headers ?? {}),
    },
  });

  if (!res.ok) {
    let body: { error?: string; message?: string } = {};
    try {
      body = await res.json();
    } catch {}
    throw new ApiError(
      res.status,
      body.error ?? "UNKNOWN_ERROR",
      body.message ?? `HTTP ${res.status}`
    );
  }

  return res.json() as Promise<T>;
}

// ── Types ─────────────────────────────────────────────────────────────────────
export interface GraphRunResponse {
  run_id: string;
  status: "running" | "interrupted" | "complete";
}

export interface GraphStatusResponse {
  run_id: string;
  status: "running" | "interrupted" | "complete";
  interrupt_node: string | null;
  state: {
    ats_score?: number;
    ats_gap?: AtsGap;
    jd_keywords?: JdKeywords;
    resume_text?: string;
    resume_version?: number;
    resume_id?: string;
    cover_letter_text?: string;
    cover_letter_id?: string;
    job_id?: string;
    error_message?: string | null;
  };
}

export interface AtsGap {
  missing_keywords: string[];
  matched_keywords: string[];
  experience_gaps: Array<{ gap: string; action: string }>;
  section_scores: {
    summary: number;
    skills: number;
    experience: number;
    education: number;
    certifications: number;
  };
  rewrite_hints: Array<{ section: string; hint: string }>;
}

export interface JdKeywords {
  hard_skills: string[];
  soft_skills: string[];
  tools: string[];
  certifications: string[];
  action_verbs: string[];
  min_years: number;
}

export interface Profile {
  id: string;
  user_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  raw_resume_text: string | null;
  skills_json: Array<{ skill: string; level?: string; years?: number }>;
  soft_skills_json: string[];
  experience_json: Array<{
    company: string;
    title: string;
    years: number;
    bullets: string[];
  }>;
  education_json: Array<{
    degree: string;
    institution: string;
    year?: number;
  }>;
  certifications_json: string[];
  master_resume_url: string | null;
  updated_at: string;
}

export interface LogEntry {
  id: string;
  applied: boolean;
  applied_on: string | null;
  feedback_rating: number | null;
  feedback_notes: string | null;
  logged_at: string;
  jobs: { company_name: string; job_title: string; ats_score_initial: number };
  resumes: { id: string; version: number; ats_score_final: number; pdf_url: string | null };
  cover_letters: { id: string; pdf_url: string | null } | null;
}

export interface LogsStats {
  total_applications: number;
  total_applied: number;
  avg_ats_score: number;
  avg_rating: number;
}

// ── API methods ───────────────────────────────────────────────────────────────
export const api = {
  graph: {
    run: (body: {
      company_name: string;
      job_title: string;
      jd_text: string;
    }) =>
      apiFetch<GraphRunResponse>("/api/graph/run", {
        method: "POST",
        body: JSON.stringify(body),
      }),

    status: (runId: string) =>
      apiFetch<GraphStatusResponse>(`/api/graph/status/${runId}`),

    resume: (
      runId: string,
      body: {
        user_confirmed?: boolean;
        is_confirmed?: boolean;
        wants_cover_letter?: boolean;
        feedback_rating?: number;
        feedback_notes?: string;
        applied?: boolean;
        applied_on?: string;
      }
    ) =>
      apiFetch<{ run_id: string; status: string }>(
        `/api/graph/resume/${runId}`,
        {
          method: "POST",
          body: JSON.stringify(body),
        }
      ),
  },

  resume: {
    get: (resumeId: string) => apiFetch<any>(`/api/resume/${resumeId}`),
  },

  logs: {
    list: (limit = 20, offset = 0) =>
      apiFetch<{ logs: LogEntry[]; stats: LogsStats }>(
        `/api/logs?limit=${limit}&offset=${offset}`
      ),
  },

  profile: {
    get: () => apiFetch<Profile>("/api/profile"),
    upsert: (body: Partial<Profile>) =>
      apiFetch<Profile>("/api/profile", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
};
