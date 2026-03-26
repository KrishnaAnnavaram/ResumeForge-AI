import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type LogEntry, type LogsStats } from "../lib/api";

/**
 * Screen 5 — Application Log Table
 * 4 stat cards + filter bar + paginated table.
 */
export default function LogTable() {
  const [filter, setFilter] = useState<"all" | "applied" | "pending">("all");
  const [minScore, setMinScore] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["logs"],
    queryFn: () => api.logs.list(50, 0),
    staleTime: 30_000,
  });

  const logs: LogEntry[] = data?.logs ?? [];
  const stats: LogsStats = data?.stats ?? {
    total_applications: 0,
    total_applied: 0,
    avg_ats_score: 0,
    avg_rating: 0,
  };

  // Client-side filtering
  const filtered = logs.filter((log) => {
    if (filter === "applied" && !log.applied) return false;
    if (filter === "pending" && log.applied) return false;
    if (minScore !== null && log.resumes.ats_score_final < minScore) return false;
    if (search) {
      const q = search.toLowerCase();
      if (
        !log.jobs.company_name.toLowerCase().includes(q) &&
        !log.jobs.job_title.toLowerCase().includes(q)
      ) return false;
    }
    return true;
  });

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <h1 className="text-2xl font-bold text-gray-900">Application Log</h1>

        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard label="Total Applications" value={stats.total_applications} />
          <StatCard label="Applied" value={stats.total_applied} color="text-green-600" />
          <StatCard
            label="Avg ATS Score"
            value={`${stats.avg_ats_score?.toFixed(1) ?? 0}%`}
            color={stats.avg_ats_score >= 80 ? "text-green-600" : "text-amber-500"}
          />
          <StatCard
            label="Avg Rating"
            value={<StarRating rating={Math.round(stats.avg_rating ?? 0)} />}
          />
        </div>

        {/* Filter bar */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 flex flex-wrap items-center gap-3">
          {/* Status pills */}
          <div className="flex gap-2">
            {(["all", "applied", "pending"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full text-sm capitalize transition ${
                  filter === f
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          {/* Score filter */}
          <div className="flex gap-2">
            {[null, 90, 80].map((s) => (
              <button
                key={s ?? "all"}
                onClick={() => setMinScore(s)}
                className={`px-3 py-1 rounded-full text-xs transition ${
                  minScore === s
                    ? "bg-brand-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {s === null ? "All scores" : `${s}%+`}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search company or role…"
            className="ml-auto border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 outline-none w-48"
          />
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          {isLoading ? (
            <div className="py-16 text-center text-gray-400">Loading…</div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center text-gray-400">
              No applications found.{" "}
              <a href="/" className="text-brand-600 hover:underline">
                Start one now
              </a>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left">
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    Company / Role
                  </th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    ATS Score
                  </th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    Status
                  </th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    Rating
                  </th>
                  <th className="px-5 py-3 text-xs font-semibold text-gray-500 uppercase">
                    Applied On
                  </th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filtered.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50 transition">
                    <td className="px-5 py-3">
                      <p className="font-medium text-gray-900">
                        {log.jobs.company_name}
                      </p>
                      <p className="text-xs text-gray-400">{log.jobs.job_title}</p>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`font-semibold ${
                          log.resumes.ats_score_final >= 95
                            ? "text-green-600"
                            : log.resumes.ats_score_final >= 80
                            ? "text-amber-500"
                            : "text-red-500"
                        }`}
                      >
                        {log.resumes.ats_score_final?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge applied={log.applied} appliedOn={log.applied_on} />
                    </td>
                    <td className="px-5 py-3">
                      <StarRating rating={log.feedback_rating ?? 0} />
                    </td>
                    <td className="px-5 py-3 text-gray-500 text-xs">
                      {log.applied_on
                        ? new Date(log.applied_on).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-5 py-3">
                      {log.resumes.pdf_url && (
                        <a
                          href={log.resumes.pdf_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-xs text-brand-600 hover:underline"
                        >
                          View PDF
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color = "text-gray-900",
}: {
  label: string;
  value: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function StatusBadge({
  applied,
  appliedOn,
}: {
  applied: boolean;
  appliedOn: string | null;
}) {
  if (applied) {
    return (
      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
        Applied
      </span>
    );
  }
  if (appliedOn) {
    return (
      <span className="px-2 py-1 bg-amber-100 text-amber-700 text-xs rounded-full">
        Pending
      </span>
    );
  }
  return (
    <span className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full">
      Not applied
    </span>
  );
}

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="text-yellow-400 text-base">
      {"★".repeat(rating)}
      {"☆".repeat(Math.max(0, 5 - rating))}
    </span>
  );
}
