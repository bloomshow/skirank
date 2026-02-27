"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE_URL || "https://skirank-production.up.railway.app") +
  "/api/v1";
const ADMIN_KEY = "skirank-admin-2026";

interface OverrideInfo {
  depth_cm: number;
  reason: string;
  set_at: string | null;
  cumulative_new_snow_cm: number;
  threshold_cm: number;
}

interface ResortQuality {
  name: string;
  slug: string;
  website_url: string | null;
  quality: string;
  flags: string[];
  current_depth_cm: number | null;
  last_updated: string | null;
  override: OverrideInfo | null;
}

interface QualityReport {
  quality_summary: Record<string, number>;
  total_resorts: number;
  flagged_resorts: ResortQuality[];
  overridden_resorts: ResortQuality[];
  last_pipeline_run: string | null;
}

const QUALITY_ORDER = ["verified", "good", "suspect", "unreliable", "stale"];
const QUALITY_META: Record<string, { icon: string; cls: string }> = {
  verified:   { icon: "✅", cls: "text-green-700" },
  good:       { icon: "✅", cls: "text-green-600" },
  suspect:    { icon: "⚠️",  cls: "text-amber-700" },
  unreliable: { icon: "❓",  cls: "text-slate-500" },
  stale:      { icon: "🕐",  cls: "text-slate-400" },
};

function bar(count: number, total: number) {
  const filled = total > 0 ? Math.round((count / total) * 20) : 0;
  return "█".repeat(filled) + "░".repeat(20 - filled);
}

// ── Single resort row with override form ─────────────────────────────────────

function ResortOverrideRow({
  resort,
  onSave,
  onClear,
}: {
  resort: ResortQuality;
  onSave: (slug: string, depth: number, reason: string, threshold: number) => Promise<void>;
  onClear: (slug: string) => Promise<void>;
}) {
  const [depthInput, setDepthInput] = useState(
    String(resort.override?.depth_cm ?? resort.current_depth_cm ?? "")
  );
  const [reason, setReason] = useState(resort.override?.reason ?? "");
  const [threshold, setThreshold] = useState(String(resort.override?.threshold_cm ?? 20));
  const [saving, setSaving] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const qMeta = QUALITY_META[resort.quality] ?? { icon: "·", cls: "text-slate-500" };
  const hasOverride = !!resort.override;

  async function handleSave() {
    const depth = parseFloat(depthInput);
    if (isNaN(depth) || depth <= 0) { setMsg("Enter a valid depth > 0"); return; }
    setSaving(true); setMsg(null);
    try {
      await onSave(resort.slug, depth, reason, parseFloat(threshold) || 20);
      setMsg("Saved ✓");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    } finally { setSaving(false); }
  }

  async function handleClear() {
    setClearing(true); setMsg(null);
    try {
      await onClear(resort.slug);
      setMsg("Cleared");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Clear failed");
    } finally { setClearing(false); }
  }

  return (
    <div className="border border-slate-200 rounded-lg p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-slate-800">{resort.name}</span>
            <span className={`text-xs capitalize ${qMeta.cls}`}>
              {qMeta.icon} {resort.quality}
            </span>
            {hasOverride && (
              <span className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                📝 Override active
              </span>
            )}
          </div>
          {resort.flags.length > 0 && (
            <p className="text-xs text-slate-500 mt-0.5 font-mono">
              {resort.flags.join(" · ")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {resort.website_url && (
            <a
              href={resort.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-500 hover:text-blue-700 whitespace-nowrap"
            >
              Snow report →
            </a>
          )}
        </div>
      </div>

      {/* Override progress bar (if active) */}
      {hasOverride && resort.override && (
        <div className="bg-slate-50 rounded p-2 text-xs text-slate-600">
          <div className="flex justify-between mb-1">
            <span>
              Override: <strong>{resort.override.depth_cm}cm</strong>
              {resort.override.reason && (
                <span className="text-slate-400 ml-1">— {resort.override.reason}</span>
              )}
            </span>
            <span className="text-slate-400">
              {resort.override.cumulative_new_snow_cm.toFixed(1)}/{resort.override.threshold_cm}cm new snow
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-1.5">
            <div
              className="bg-blue-400 h-1.5 rounded-full transition-all"
              style={{
                width: `${Math.min(100, (resort.override.cumulative_new_snow_cm / resort.override.threshold_cm) * 100)}%`,
              }}
            />
          </div>
          <p className="text-slate-400 mt-1">
            Auto-expires when {resort.override.threshold_cm}cm new snow accumulates since{" "}
            {resort.override.set_at ? new Date(resort.override.set_at).toLocaleDateString() : "override date"}
          </p>
        </div>
      )}

      {/* Override form */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_2fr_auto_auto] gap-2 items-end">
        <div>
          <label className="text-xs text-slate-500 block mb-1">
            Override depth (cm)
            {resort.current_depth_cm != null && (
              <span className="text-slate-400 ml-1">
                · current: {resort.current_depth_cm}cm
              </span>
            )}
          </label>
          <input
            type="number"
            step="0.1"
            min="0"
            value={depthInput}
            onChange={(e) => setDepthInput(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="e.g. 185.0"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Note (optional)</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
            placeholder="e.g. Verified against webcam, station reading high"
          />
        </div>
        <div>
          <label className="text-xs text-slate-500 block mb-1">Expire after (cm new snow)</label>
          <input
            type="number"
            step="1"
            min="5"
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            className="w-20 border border-slate-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            {saving ? "Saving…" : hasOverride ? "Update" : "Save override"}
          </button>
          {hasOverride && (
            <button
              onClick={handleClear}
              disabled={clearing}
              className="px-3 py-1.5 border border-slate-300 text-sm text-slate-600 rounded hover:bg-slate-50 disabled:opacity-50 transition-colors"
            >
              {clearing ? "…" : "Clear"}
            </button>
          )}
        </div>
      </div>
      {msg && <p className="text-xs text-slate-500">{msg}</p>}
    </div>
  );
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

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

  useEffect(() => { fetchReport(); }, [fetchReport]);

  async function saveOverride(slug: string, depth: number, reason: string, threshold: number) {
    const res = await fetch(`${API_BASE}/admin/set-override`, {
      method: "POST",
      headers: { "x-admin-key": ADMIN_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ resort_slug: slug, depth_cm: depth, reason, threshold_cm: threshold }),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    await fetchReport();
  }

  async function clearOverride(slug: string) {
    const res = await fetch(`${API_BASE}/admin/clear-override/${slug}`, {
      method: "DELETE",
      headers: { "x-admin-key": ADMIN_KEY },
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    await fetchReport();
  }

  async function triggerPipeline() {
    setTriggering(true); setTriggerMsg(null);
    try {
      const res = await fetch(`${API_BASE}/admin/run-pipeline`, {
        method: "POST",
        headers: { "x-admin-key": ADMIN_KEY },
      });
      const data = await res.json();
      setTriggerMsg(data.message || "Pipeline started");
    } catch {
      setTriggerMsg("Failed to trigger pipeline");
    } finally { setTriggering(false); }
  }

  if (error) return <p className="text-red-500 text-sm">{error}</p>;
  if (!report) return <p className="text-slate-400 text-sm">Loading quality report…</p>;

  const { quality_summary, total_resorts, flagged_resorts, overridden_resorts, last_pipeline_run } = report;

  return (
    <div className="space-y-10">

      {/* Pipeline info */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <p className="text-sm text-slate-500">
          Last pipeline run:{" "}
          <span className="font-medium text-slate-700">
            {last_pipeline_run ? new Date(last_pipeline_run).toUTCString() : "Unknown"}
          </span>
        </p>
        <div className="flex items-center gap-3">
          <button
            onClick={triggerPipeline}
            disabled={triggering}
            className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {triggering ? "Starting…" : "Re-run pipeline"}
          </button>
          <button
            onClick={fetchReport}
            className="px-3 py-1.5 border border-slate-200 text-sm text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
          >
            Refresh
          </button>
          {triggerMsg && <p className="text-sm text-slate-500">{triggerMsg}</p>}
        </div>
      </div>

      {/* Quality summary */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-3">📊 Quality Summary</h2>
        <div className="font-mono text-sm space-y-1.5">
          {QUALITY_ORDER.map((tier) => {
            const count = quality_summary[tier] ?? 0;
            const { icon, cls } = QUALITY_META[tier] ?? { icon: "·", cls: "text-slate-500" };
            const pct = total_resorts > 0 ? Math.round((count / total_resorts) * 100) : 0;
            return (
              <div key={tier} className="flex items-center gap-3">
                <span className={`w-24 capitalize ${cls}`}>{icon} {tier}</span>
                <span className="w-6 text-right text-slate-600">{count}</span>
                <span className="text-slate-300">{bar(count, total_resorts)}</span>
                <span className="text-slate-400">{pct}%</span>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-slate-400 mt-2">{total_resorts} resorts with snapshots</p>
      </div>

      {/* Flagged resorts with override forms */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 mb-1">
          ⚠️ Flagged Resorts ({flagged_resorts.length})
        </h2>
        <p className="text-xs text-slate-400 mb-3">
          Set a manual override to correct a bad reading. The override persists until the
          specified amount of new snow accumulates, then the pipeline resumes using live data.
        </p>
        {flagged_resorts.length === 0 ? (
          <p className="text-sm text-green-600">No flagged resorts — all data looks good.</p>
        ) : (
          <div className="space-y-3">
            {flagged_resorts.map((r) => (
              <ResortOverrideRow
                key={r.slug}
                resort={r}
                onSave={saveOverride}
                onClear={clearOverride}
              />
            ))}
          </div>
        )}
      </div>

      {/* Active overrides on non-flagged resorts */}
      {overridden_resorts.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-700 mb-1">
            📝 Active Overrides — Non-flagged ({overridden_resorts.length})
          </h2>
          <p className="text-xs text-slate-400 mb-3">
            These resorts have an active override but currently pass all quality checks (pipeline
            accepted the overridden depth). Override will auto-expire when new snow threshold is reached.
          </p>
          <div className="space-y-3">
            {overridden_resorts.map((r) => (
              <ResortOverrideRow
                key={r.slug}
                resort={r}
                onSave={saveOverride}
                onClear={clearOverride}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
