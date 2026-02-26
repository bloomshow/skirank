/**
 * SkiRank Data Quality Dashboard
 * Internal page — not linked from nav. Access via /admin/quality
 */
import { Suspense } from "react";
import QualityDashboard from "./QualityDashboard";

export const metadata = {
  title: "Data Quality — SkiRank Admin",
};

export default function QualityPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-10">
      <h1 className="text-xl font-bold text-slate-800 mb-1">SkiRank Data Quality Dashboard</h1>
      <p className="text-sm text-slate-500 mb-8">Internal tool — not linked from public nav.</p>
      <Suspense fallback={<div className="text-slate-400 text-sm">Loading…</div>}>
        <QualityDashboard />
      </Suspense>
    </div>
  );
}
