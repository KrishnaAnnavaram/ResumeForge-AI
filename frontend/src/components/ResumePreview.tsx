import { useState } from "react";
import { api } from "../lib/api";
import { useAppStore } from "../store/appStore";

/**
 * Screen 3 — Resume Preview
 * Shows the generated resume with injected keywords highlighted in amber.
 * Gate 2: user confirms or requests regeneration.
 */
export default function ResumePreview() {
  const runId = useAppStore((s) => s.runId);
  const resumeText = useAppStore((s) => s.resumeText);
  const resumeVersion = useAppStore((s) => s.resumeVersion);
  const atsScore = useAppStore((s) => s.atsScore);
  const atsGap = useAppStore((s) => s.atsGap);
  const companyName = useAppStore((s) => s.companyName);
  const jobTitle = useAppStore((s) => s.jobTitle);

  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<"confirming" | "regenerating" | null>(null);

  const handleConfirm = async () => {
    if (!runId) return;
    setAction("confirming");
    setLoading(true);
    try {
      await api.graph.resume(runId, { is_confirmed: true });
      // Polling will navigate to /cover-letter
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerate = async () => {
    if (!runId) return;
    setAction("regenerating");
    setLoading(true);
    try {
      // is_confirmed = false → graph stays at show_resume and re-runs resume_writer
      await api.graph.resume(runId, { is_confirmed: false, user_confirmed: true });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const score = atsScore ?? 0;
  const injectedKeywords = atsGap?.matched_keywords ?? [];
  const scoreGreen = score >= 95;

  // Highlight injected keywords in resume text
  const highlightedHtml = highlightKeywords(resumeText ?? "", injectedKeywords);

  return (
    <div className="min-h-screen bg-gray-100 py-8 px-4">
      <div className="max-w-5xl mx-auto flex gap-6">

        {/* Resume paper */}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-xl font-bold text-gray-900">Resume Preview</h1>
              <p className="text-sm text-gray-500">
                {jobTitle} at {companyName} — Version {resumeVersion ?? 1}
              </p>
            </div>
            <div
              className={`px-3 py-1 rounded-full text-sm font-semibold ${
                scoreGreen
                  ? "bg-green-100 text-green-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              ATS {Math.round(score)}%{scoreGreen ? " ✓" : ""}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 font-serif text-sm leading-relaxed">
            {resumeText ? (
              <div
                dangerouslySetInnerHTML={{ __html: highlightedHtml }}
                className="prose max-w-none"
              />
            ) : (
              <div className="text-gray-400 text-center py-20">
                Loading resume…
              </div>
            )}
          </div>

          {/* Keyword legend */}
          {injectedKeywords.length > 0 && (
            <p className="text-xs text-gray-500 mt-3">
              <span
                className="inline-block px-1 rounded"
                style={{ background: "#FAEEDA" }}
              >
                Highlighted
              </span>{" "}
              keywords were injected to improve ATS matching.
            </p>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-64 shrink-0 space-y-4">
          {/* Actions */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="w-full py-2.5 bg-brand-600 text-white text-sm font-semibold rounded-lg hover:bg-brand-700 disabled:opacity-50 transition"
            >
              {action === "confirming" && loading
                ? "Confirming…"
                : "Confirm + download PDF"}
            </button>
            <button
              onClick={handleRegenerate}
              disabled={loading}
              className="w-full py-2.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 transition"
            >
              {action === "regenerating" && loading ? "Regenerating…" : "Regenerate ↻"}
            </button>
          </div>

          {/* Section scores */}
          {atsGap?.section_scores && (
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <h3 className="text-xs font-semibold text-gray-500 uppercase mb-3">
                Section Scores
              </h3>
              {Object.entries(atsGap.section_scores).map(([sec, val]) => (
                <div key={sec} className="mb-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="capitalize text-gray-600">{sec}</span>
                    <span className="font-medium">{Math.round(val as number)}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${(val as number) >= 80 ? "bg-green-400" : (val as number) >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                      style={{ width: `${val}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Wrap matched keywords with amber highlight spans. */
function highlightKeywords(text: string, keywords: string[]): string {
  if (!keywords.length) return escapeHtml(text).replace(/\n/g, "<br>");
  let escaped = escapeHtml(text);
  for (const kw of keywords) {
    const safe = escapeHtml(kw).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`\\b(${safe})\\b`, "gi");
    escaped = escaped.replace(
      re,
      `<mark style="background:#FAEEDA;padding:0 2px;border-radius:2px;">$1</mark>`
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
