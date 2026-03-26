import { useState } from "react";
import { api } from "../lib/api";
import { useAppStore } from "../store/appStore";

/**
 * Screen 2 — ATS Dashboard
 * Shows overall score, section bars, matched/missing keywords, experience gaps.
 * Gate 1: user confirms or declines resume generation.
 */
export default function ATSDashboard() {
  const runId = useAppStore((s) => s.runId);
  const atsScore = useAppStore((s) => s.atsScore);
  const atsGap = useAppStore((s) => s.atsGap);
  const companyName = useAppStore((s) => s.companyName);
  const jobTitle = useAppStore((s) => s.jobTitle);
  const [loading, setLoading] = useState(false);
  const [declined, setDeclined] = useState(false);

  const handleGenerate = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      await api.graph.resume(runId, { user_confirmed: true });
    } catch (err) {
      console.error(err);
    }
    // Polling will navigate to /resume when ready
  };

  const handleDecline = async () => {
    if (!runId) return;
    try {
      await api.graph.resume(runId, { user_confirmed: false });
    } catch {}
    setDeclined(true);
  };

  if (declined) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-sm">
          <div className="text-4xl mb-4">👋</div>
          <h2 className="text-xl font-bold text-gray-800">No problem!</h2>
          <p className="text-gray-500 mt-2">You can come back any time.</p>
          <a href="/" className="mt-4 inline-block text-brand-600 hover:underline">
            Start new analysis
          </a>
        </div>
      </div>
    );
  }

  const score = atsScore ?? 0;
  const gap = atsGap;
  const sectionScores = gap?.section_scores ?? {};
  const scoreColor =
    score >= 80 ? "text-green-600" : score >= 60 ? "text-amber-500" : "text-red-500";
  const scoreBg =
    score >= 80 ? "bg-green-50 border-green-200" : score >= 60 ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200";

  const sections = [
    { label: "Summary", key: "summary" },
    { label: "Skills", key: "skills" },
    { label: "Experience", key: "experience" },
    { label: "Education", key: "education" },
    { label: "Certifications", key: "certifications" },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ATS Analysis</h1>
          <p className="text-gray-500 text-sm mt-1">
            {jobTitle} at {companyName}
          </p>
        </div>

        {/* Score card */}
        <div className={`rounded-2xl border p-8 flex items-center gap-8 ${scoreBg}`}>
          <div className="text-center">
            <div className={`text-7xl font-extrabold ${scoreColor}`}>
              {Math.round(score)}
              <span className="text-3xl">%</span>
            </div>
            <p className="text-sm text-gray-500 mt-1">ATS Match Score</p>
          </div>
          <div className="flex-1 space-y-3">
            {sections.map(({ label, key }) => {
              const val = sectionScores[key] ?? 0;
              return (
                <div key={key}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-medium">{Math.round(val)}%</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${val >= 80 ? "bg-green-500" : val >= 60 ? "bg-amber-400" : "bg-red-400"}`}
                      style={{ width: `${val}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          {/* Matched keywords */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Matched Keywords ({gap?.matched_keywords?.length ?? 0})
            </h3>
            <div className="flex flex-wrap gap-2">
              {(gap?.matched_keywords ?? []).map((kw) => (
                <span key={kw} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full">
                  {kw}
                </span>
              ))}
              {(!gap?.matched_keywords?.length) && (
                <p className="text-xs text-gray-400">No matches found</p>
              )}
            </div>
          </div>

          {/* Missing keywords */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Missing Keywords ({gap?.missing_keywords?.length ?? 0})
            </h3>
            <div className="flex flex-wrap gap-2">
              {(gap?.missing_keywords ?? []).map((kw) => (
                <span key={kw} className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">
                  {kw}
                </span>
              ))}
              {(!gap?.missing_keywords?.length) && (
                <p className="text-xs text-green-600">All keywords matched!</p>
              )}
            </div>
          </div>
        </div>

        {/* Experience gaps */}
        {(gap?.experience_gaps?.length ?? 0) > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Experience Gaps</h3>
            <ul className="space-y-3">
              {gap!.experience_gaps.map((eg, i) => (
                <li key={i} className="flex gap-3">
                  <span className="shrink-0 w-2 h-2 rounded-full bg-amber-400 mt-2" />
                  <div>
                    <p className="text-sm text-gray-800">{eg.gap}</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Suggested action: {eg.action}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* CTA */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleDecline}
            className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-100 transition text-sm"
          >
            Not now
          </button>
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="px-6 py-2.5 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-50 transition flex items-center gap-2 text-sm"
          >
            {loading ? "Generating…" : "Generate optimised resume →"}
          </button>
        </div>
      </div>
    </div>
  );
}
