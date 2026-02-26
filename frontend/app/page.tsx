import Link from "next/link";
import { fetchRankings, fetchResorts } from "../lib/api";

export default async function HomePage() {
  let top5: Awaited<ReturnType<typeof fetchRankings>>["results"] = [];
  let totalResorts = 0;

  try {
    const data = await fetchRankings({ horizon_days: 0 }, 1, 5);
    top5 = data.results;
    totalResorts = data.meta.total;
  } catch {
    // Backend not running yet — show empty state
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-16 space-y-16">
      {/* Hero */}
      <section className="text-center space-y-6">
        <h1 className="text-5xl font-extrabold text-slate-900 tracking-tight">
          Find the best snow on the planet
        </h1>
        <p className="text-xl text-slate-500 max-w-2xl mx-auto">
          SkiRank scores every major ski resort worldwide daily — based on real snowpack,
          fresh powder, temperature, and 14-day forecasts. No resort PR spin.
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/rankings"
            className="px-6 py-3 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-700 transition-colors shadow-md"
          >
            View Rankings
          </Link>
          <Link
            href="/map"
            className="px-6 py-3 bg-white text-slate-700 border border-slate-200 rounded-xl font-semibold hover:bg-slate-50 transition-colors shadow-sm"
          >
            Map View
          </Link>
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-3 gap-6 text-center">
        {[
          { label: "Resorts tracked", value: totalResorts > 0 ? totalResorts.toLocaleString() : "200+" },
          { label: "Forecast horizon", value: "14 days" },
          { label: "Data freshness", value: "Daily" },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <p className="text-3xl font-bold text-blue-600">{value}</p>
            <p className="text-sm text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </section>

      {/* Top 5 today */}
      {top5.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-slate-800">Top 5 Today</h2>
            <Link href="/rankings" className="text-sm text-blue-500 hover:underline">
              Full rankings →
            </Link>
          </div>
          <div className="space-y-3">
            {top5.map((entry) => (
              <Link
                key={entry.resort.id}
                href={`/resort/${entry.resort.slug}`}
                className="flex items-center gap-4 bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md hover:border-blue-300 transition-all"
              >
                <span className="text-2xl font-bold text-slate-300 w-8">{entry.rank}</span>
                <div className="flex-1">
                  <p className="font-semibold text-slate-800">{entry.resort.name}</p>
                  <p className="text-xs text-slate-400">{entry.resort.region}</p>
                </div>
                <div
                  className={`px-3 py-1 rounded-xl font-bold text-lg ${
                    (entry.score ?? 0) >= 80
                      ? "bg-green-100 text-green-800"
                      : (entry.score ?? 0) >= 60
                      ? "bg-yellow-100 text-yellow-800"
                      : "bg-orange-100 text-orange-800"
                  }`}
                >
                  {entry.score !== null ? Math.round(entry.score) : "—"}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
