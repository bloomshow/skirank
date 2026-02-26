import { fetchRankingsMap } from "../../lib/api";
import MapView from "../../components/MapView";

export const metadata = {
  title: "Map — SkiRank",
};

export default async function MapPage() {
  let resorts: Awaited<ReturnType<typeof fetchRankingsMap>> = [];
  try {
    resorts = await fetchRankingsMap(0);
  } catch {
    // Backend offline
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-4">
      <h1 className="text-2xl font-bold text-slate-800">Resort Map</h1>
      <p className="text-slate-500 text-sm">
        Colour-coded by composite score — green (80+), yellow (60–79), orange (40–59), red (&lt;40).
      </p>
      <MapView resorts={resorts} />
    </div>
  );
}
