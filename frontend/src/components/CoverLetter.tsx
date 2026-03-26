import { useState } from "react";
import { api } from "../lib/api";
import { useAppStore } from "../store/appStore";

/**
 * Screen 4 — Cover Letter
 * Gate 3: asks user if they want a cover letter (NEVER auto-generates).
 * Generated state: shows cover letter with soft skill highlights.
 */
export default function CoverLetter() {
  const runId = useAppStore((s) => s.runId);
  const coverLetterText = useAppStore((s) => s.coverLetterText);
  const atsGap = useAppStore((s) => s.atsGap);
  const companyName = useAppStore((s) => s.companyName);
  const jobTitle = useAppStore((s) => s.jobTitle);

  const [loading, setLoading] = useState(false);
  const [asked, setAsked] = useState(false);

  // ── Gate 3 ask state ──────────────────────────────────────────────────
  if (!asked && !coverLetterText) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-sm border border-gray-200 p-10 text-center">
          <div className="text-5xl mb-5">✉️</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            Generate a cover letter?
          </h2>
          <p className="text-gray-500 mb-8">
            Create a personalised cover letter for{" "}
            <strong>{jobTitle}</strong> at <strong>{companyName}</strong> using
            your soft skills.
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={async () => {
                if (!runId) return;
                setLoading(true);
                setAsked(true);
                try {
                  await api.graph.resume(runId, { wants_cover_letter: false });
                } catch {}
                setLoading(false);
              }}
              className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition text-sm"
            >
              Skip
            </button>
            <button
              onClick={async () => {
                if (!runId) return;
                setLoading(true);
                setAsked(true);
                try {
                  await api.graph.resume(runId, { wants_cover_letter: true });
                } catch {
                  setLoading(false);
                }
                // Polling will navigate when ready — leave loading=true
              }}
              disabled={loading}
              className="px-6 py-2.5 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-50 transition text-sm"
            >
              {loading ? "Generating…" : "Yes, generate"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Loading state (after user said yes, waiting for LLM) ──────────────
  if (asked && !coverLetterText) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin h-10 w-10 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-500">Writing your cover letter…</p>
        </div>
      </div>
    );
  }

  // ── Generated state ───────────────────────────────────────────────────
  // Soft skills to highlight come from the matched keywords soft_skills
  const softSkillsUsed = (atsGap as any)?.soft_skills_used ??
    atsGap?.matched_keywords?.slice(0, 5) ?? [];

  const highlightedHtml = highlightSoftSkills(coverLetterText ?? "", softSkillsUsed);

  const handleContinue = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      // Resume after show_cover_letter interrupt
      await api.graph.resume(runId, {});
    } catch {}
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Cover Letter</h1>
            <p className="text-sm text-gray-500">
              {jobTitle} at {companyName}
            </p>
          </div>
        </div>

        {/* Cover letter paper */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 font-serif text-sm leading-relaxed mb-4">
          <div dangerouslySetInnerHTML={{ __html: highlightedHtml }} />
        </div>

        {/* Soft skills used */}
        {softSkillsUsed.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
            <p className="text-xs font-medium text-gray-500 mb-2">Soft skills woven in</p>
            <div className="flex flex-wrap gap-2">
              {softSkillsUsed.map((sk: string) => (
                <span
                  key={sk}
                  className="px-2 py-1 rounded-full text-xs"
                  style={{ background: "#E1F5EE", color: "#1a6b4a" }}
                >
                  {sk}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            onClick={handleContinue}
            disabled={loading}
            className="px-6 py-2.5 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-50 transition text-sm"
          >
            {loading ? "Saving…" : "Continue to feedback →"}
          </button>
        </div>
      </div>
    </div>
  );
}

function highlightSoftSkills(text: string, skills: string[]): string {
  if (!skills.length) return escapeHtml(text).replace(/\n/g, "<br>");
  let escaped = escapeHtml(text);
  for (const sk of skills) {
    const safe = escapeHtml(sk).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`\\b(${safe})\\b`, "gi");
    escaped = escaped.replace(
      re,
      `<mark style="background:#E1F5EE;padding:0 2px;border-radius:2px;">$1</mark>`
    );
  }
  return escaped.replace(/\n/g, "<br>");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
