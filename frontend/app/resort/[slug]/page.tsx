import { notFound } from "next/navigation";
import { fetchResort } from "../../../lib/api";
import ScoreGauge from "../../../components/ScoreGauge";
import ForecastTable from "../../../components/ForecastTable";

interface Props {
  params: { slug: string };
}

export async function generateMetadata({ params }: Props) {
  try {
    const data = await fetchResort(params.slug);
    return { title: `${data.resort.name} — SkiRank` };
  } catch {
    return { title: "Resort — SkiRank" };
  }
}

const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸", CA: "🇨🇦", FR: "🇫🇷", AT: "🇦🇹", CH: "🇨🇭",
  IT: "🇮🇹", JP: "🇯🇵", AU: "🇦🇺", NZ: "🇳🇿", NO: "🇳🇴",
  SE: "🇸🇪", DE: "🇩🇪", SK: "🇸🇰", SI: "🇸🇮", ES: "🇪🇸",
};

export default async function ResortDetailPage({ params }: Props) {
  let data: Awaited<ReturnType<typeof fetchResort>>;
  try {
    data = await fetchResort(params.slug);
  } catch {
    notFound();
  }

  const { resort, current_score, sub_scores, snapshot, forecast } = data;
  const flag = resort.country ? (COUNTRY_FLAGS[resort.country] ?? resort.country) : "";

  const subScoreItems = [
    { label: "Base Depth", value: sub_scores.base_depth },
    { label: "Fresh Snow", value: sub_scores.fresh_snow },
    { label: "Temperature", value: sub_scores.temperature },
    { label: "Wind", value: sub_scores.wind },
    { label: "Forecast Confidence", value: sub_scores.forecast },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-10">
      {/* Hero */}
      <section className="space-y-2">
        <div className="flex items-center gap-3 flex-wrap">
          <h1 className="text-3xl font-extrabold text-slate-900">{resort.name}</h1>
          <span className="text-2xl">{flag}</span>
        </div>
        <div className="flex gap-3 text-sm text-slate-500 flex-wrap">
          {resort.region && <span>{resort.region}</span>}
          {resort.subregion && <span>· {resort.subregion}</span>}
          {resort.elevation_summit_m && (
            <span>· Summit {resort.elevation_summit_m.toLocaleString()}m</span>
          )}
          {resort.elevation_base_m && (
            <span>· Base {resort.elevation_base_m.toLocaleString()}m</span>
          )}
          {resort.aspect && <span>· {resort.aspect}-facing</span>}
        </div>
        {resort.website_url && (
          <a
            href={resort.website_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline"
          >
            Official website →
          </a>
        )}
      </section>

      {/* Score + sub-scores */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-700 mb-4">Current Score</h2>
        <div className="flex items-center gap-8 flex-wrap">
          <ScoreGauge score={current_score} size={120} />
          <div className="flex-1 space-y-3 min-w-48">
            {subScoreItems.map(({ label, value }) => (
              <div key={label} className="space-y-1">
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{label}</span>
                  <span>{value !== null ? Math.round(value) : "—"}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all"
                    style={{ width: `${value !== null ? Math.min(100, value) : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Current conditions */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-700 mb-4">Current Conditions</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "Base depth", value: snapshot.snow_depth_cm !== null ? `${snapshot.snow_depth_cm} cm` : "—" },
            { label: "New snow 72h", value: snapshot.new_snow_72h_cm !== null ? `${snapshot.new_snow_72h_cm} cm` : "—" },
            { label: "Temperature", value: snapshot.temperature_c !== null ? `${snapshot.temperature_c}°C` : "—" },
            { label: "Wind speed", value: snapshot.wind_speed_kmh !== null ? `${snapshot.wind_speed_kmh} km/h` : "—" },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <p className="text-2xl font-bold text-slate-800">{value}</p>
              <p className="text-xs text-slate-400 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 16-day forecast */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-slate-700 mb-4">16-Day Forecast</h2>
        <ForecastTable forecast={forecast} />
      </section>
    </div>
  );
}
