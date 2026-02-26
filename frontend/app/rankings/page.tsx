import { fetchRegions } from "../../lib/api";
import type { RegionEntry } from "../../lib/types";
import ControlBar from "../../components/ControlBar";
import RankingsList from "../../components/RankingsList";

export const metadata = {
  title: "Rankings — SkiRank",
  description: "Live global ski resort rankings updated daily.",
};

export default async function RankingsPage() {
  let regions: RegionEntry[] = [];
  try {
    regions = await fetchRegions();
  } catch {
    // Backend offline
  }

  return (
    <div className="min-h-screen">
      <ControlBar regions={regions} />
      <div className="max-w-5xl mx-auto px-4 py-8">
        <RankingsList />
      </div>
    </div>
  );
}
