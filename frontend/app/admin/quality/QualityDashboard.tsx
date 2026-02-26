"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "https://skirank-production.up.railway.app") +
  "/api/v1";
const ADMIN_KEY = "skirank-admin-2026";

interface QualityReport {
  quality_summary: Record<string, number>;
  total_resorts: number;
  flagged_resorts: {
    name: string;
    slug: string;
    quality: string;
    flags: string[];
    last_updated: string | null;
  }[];
  last_pipeline_run: string | null;
}

const QUALITY_ORDER = ["verified", "good", "suspect", "unreliable", "stale"];
const QUALITY_LABELS: Record<string, { icon: string; cls: string }> = {
  verified:   { icon: "✅", cls: "text-green-700" },
  good:       { icon: "✅", cls: "text-green-600" },
  suspect:    { icon: "⚠️",  cls: "text-amber-700" },
  unreliable: { icon: "❓",  cls: "text-slate-500" },
  stale:      { icon: "🕐",  cls: "text-slate-400" },
};

function bar(count: number, total: number) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  const filled = Math.round(pct / 5);
  return "█".repeat(filled) + "░".repeat(20 - filled);
}

export default function QualityDashboard() {
  const [report, setReport] = useState<QualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [triggerMsg, setTriggerMsg] = useState<string | null>(null);

  const fetchReport = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/admin/quality-report`, {
        headers: { "x-admin-key": ADMIN_KEY },
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setReport(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    }
  }, []);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  async function triggerPipeline() {
    setTriggering(true);
    setTriggerMsg(null);
    try {
      const res = await fetch(`${API_BASE}/admin/run-pipeline`, {
        method: "POST",
        headers: { "x-admin-key": ADMIN_KEY },
      });
      const data = await res.json();
      setTriggerMsg(data.message || "Pipeline started");
    } catch {
      setTriggerMsg("Failed to trigger pipeline");
    } finally {
      setTriggering(false);
    }
  }

  if (error) {
    return <p className="text-red-500 text-sm">{error}</p>;
  }
  if (!report) {
    return <p className="text-slate-400 text-sm">Loading quality report…</p>;
  }

  const { quality_summary, total_resorts, flagged_resorts, last_pipeline_run } = report;

  return (
    <div className="space-y-8">
      {/* Header info */}
      <div className="text-sm text-slate-500">
        Last pipeline run:{" "}
        <span className="font-medium text-slate-700">
          {last_pipeline_run
            ? new Date(last_pipeline_run).toUTCString()
            : "Unknown"}
        </span>
      </div>

      {/* Quality summary */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">📊 Quality Summary</h2>
        <div className="font-mono text-sm space-y-1.5">
          {QUALITY_ORDER.map((tier) => {
            const count = quality_summary[tier] ?? 0;
            const { icon, cls } = QUALITY_LABELS[tier] ?? { icon: "·", cls: "text-slate-500" };
            const pct = total_resorts > 0 ? Math.round((count / total_resorts) * 100) : 0;
            return (
              <div key={tier} className="flex items-center gap-3">
                <span className={`w-24 capitalize ${cls}`}>
                  {icon} {tier}
                </span>
                <span className="w-6 text-right text-slate-600">{count}</span>
                <span className="text-slate-300">{bar(count, total_resorts)}</span>
                <span className="text-slate-400">{pct}%</span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-slate-400 mt-2">Total: {total_resorts} resorts with snapshots</p>
      </div>

      {/* Flagged resorts */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">
          ⚠️ Flagged Resorts ({flagged_resorts.length})
        </h2>
        {flagged_resorts.length === 0 ? (
          <p className="text-sm text-green-600">No flagged resorts — all data looks good.</p>
        ) : (
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-xs text-slate-600">
              <thead className="bg-slate-50 text-slate-400 border-b border-slate-200">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Resort</th>
                  <th className="text-left px-4 py-2 font-medium">Quality</th>
                  <th className="text-left px-4 py-2 font-medium">Flags</th>
                  <th className="text-left px-4 py-2 font-medium">Last updated</th>
                </tr>
              </thead>
              <tbody>
                {flagged_resorts.map((r) => {
                  const { icon, cls } = QUALITY_LABELS[r.quality] ?? { icon: "·", cls: "" };
                  return (
                    <tr key={r.slug} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2 font-medium text-slate-800">{r.name}</td>
                      <td className={`px-4 py-2 capitalize ${cls}`}>
                        {icon} {r.quality}
                      </td>
                      <td className="px-4 py-2 text-slate-500">
                        {r.flags.length > 0 ? r.flags.join(", ") : "—"}
                      </td>
                      <td className="px-4 py-2 text-slate-400">
                        {r.last_updated
                          ? new Date(r.last_updated).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={triggerPipeline}
          disabled={triggering}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {triggering ? "Starting…" : "Re-run pipeline"}
        </button>
        <button
          onClick={fetchReport}
          className="px-4 py-2 border border-slate-200 text-sm text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
        >
          Refresh
        </button>
        {triggerMsg && <p className="text-sm text-slate-500">{triggerMsg}</p>}
      </div>
    </div>
  );
}
