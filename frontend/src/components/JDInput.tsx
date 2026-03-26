import { useState } from "react";
import { api } from "../lib/api";
import { useAppStore } from "../store/appStore";
import { useProfile } from "../hooks/useProfile";
import { useGraphStatus } from "../hooks/useGraphStatus";

/**
 * Screen 1 — JD Input
 * User enters company, role, and pastes the job description.
 * Profile sidebar shows name, skill count, and top 5 skills.
 */
export default function JDInput() {
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const setRunId = useAppStore((s) => s.setRunId);
  const setJobContext = useAppStore((s) => s.setJobContext);
  const { data: profile, isLoading: profileLoading } = useProfile();

  // Start polling as soon as we have a runId
  useGraphStatus();

  const handleSubmit = async () => {
    setError(null);
    if (!companyName.trim()) { setError("Company name is required"); return; }
    if (!jobTitle.trim()) { setError("Job title is required"); return; }
    if (jdText.trim().length < 50) { setError("Please paste a full job description (minimum 50 characters)"); return; }
    if (jdText.trim().length > 10_000) { setError("Job description is too long (max 10,000 characters)"); return; }

    setLoading(true);
    try {
      const res = await api.graph.run({
        company_name: companyName.trim(),
        job_title: jobTitle.trim(),
        jd_text: jdText.trim(),
      });
      setJobContext(companyName.trim(), jobTitle.trim());
      setRunId(res.run_id);
    } catch (err: any) {
      setError(err.message ?? "Failed to start analysis. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const topSkills = (profile?.skills_json ?? [])
    .slice(0, 5)
    .map((s) => (typeof s === "string" ? s : s.skill));

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Main panel */}
      <div className="flex-1 max-w-3xl mx-auto py-12 px-6">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">ResumeForge AI</h1>
          <p className="text-gray-500 mt-1">
            Paste a job description and get an ATS-optimised resume in minutes.
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Company name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                maxLength={200}
                placeholder="Acme Corp"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Job title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={jobTitle}
                onChange={(e) => setJobTitle(e.target.value)}
                maxLength={200}
                placeholder="Senior Software Engineer"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Job description <span className="text-red-500">*</span>
            </label>
            <textarea
              value={jdText}
              onChange={(e) => setJdText(e.target.value)}
              maxLength={10_000}
              rows={10}
              placeholder="Paste the full job description here..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-transparent outline-none resize-none"
              style={{ minHeight: 120 }}
            />
            <div className="flex justify-between mt-1">
              {error && <p className="text-red-500 text-xs">{error}</p>}
              <span className="text-xs text-gray-400 ml-auto">
                {jdText.length.toLocaleString()} / 10,000
              </span>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full py-3 bg-brand-600 text-white font-semibold rounded-xl hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Spinner /> Analysing ATS score…
              </>
            ) : (
              "Analyse ATS score →"
            )}
          </button>
        </div>
      </div>

      {/* Profile sidebar */}
      <aside className="w-72 bg-white border-l border-gray-200 p-6 hidden lg:block">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
          Your Profile
        </h2>
        {profileLoading ? (
          <div className="space-y-2">
            <div className="h-4 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
          </div>
        ) : profile ? (
          <div className="space-y-4">
            <div>
              <p className="font-medium text-gray-900">{profile.full_name ?? "—"}</p>
              <p className="text-xs text-gray-400">{profile.email ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">
                Skills ({profile.skills_json?.length ?? 0})
              </p>
              <div className="flex flex-wrap gap-1">
                {topSkills.map((skill) => (
                  <span
                    key={skill}
                    className="px-2 py-0.5 bg-brand-50 text-brand-700 text-xs rounded-full"
                  >
                    {skill}
                  </span>
                ))}
                {(profile.skills_json?.length ?? 0) > 5 && (
                  <span className="text-xs text-gray-400">
                    +{profile.skills_json.length - 5} more
                  </span>
                )}
              </div>
            </div>
            {profile.master_resume_url && (
              <a
                href={profile.master_resume_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-brand-600 hover:underline"
              >
                View master resume
              </a>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-400">
            No profile found.{" "}
            <a href="/profile" className="text-brand-600 hover:underline">
              Create one
            </a>
          </p>
        )}
      </aside>
    </div>
  );
}

function Spinner() {
  return (
    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}
