import { Suspense } from "react";
import { fetchHierarchy } from "../../lib/api";
import type { HierarchyResponse } from "../../lib/types";
import ControlBar from "../../components/ControlBar";
import RankingsList from "../../components/RankingsList";

export const metadata = {
  title: "Rankings — SkiRank",
  description: "Live global ski resort rankings updated daily.",
};

export default async function RankingsPage() {
  let hierarchy: HierarchyResponse = { continents: [] };
  try {
    hierarchy = await fetchHierarchy();
  } catch {
    // Backend offline
  }

  return (
    <div className="min-h-screen">
      <Suspense fallback={<div className="h-16 bg-white border-b border-slate-200" />}>
        <ControlBar hierarchy={hierarchy} />
      </Suspense>
      <div className="max-w-5xl mx-auto px-4 py-8">
        <RankingsList />
      </div>
    </div>
  );
}
