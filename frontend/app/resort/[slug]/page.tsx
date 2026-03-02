import { notFound } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { fetchResort } from "../../../lib/api";
import ForecastTable from "../../../components/ForecastTable";
import ScoreGauge from "../../../components/ScoreGauge";
import type { ResortDetailFull } from "../../../lib/types";

// Client-only components
const SeasonChart = dynamic(() => import("../../../components/SeasonChart"), { ssr: false });
const ConditionSummaries = dynamic(() => import("../../../components/ConditionSummaries"), { ssr: false });

interface Props {
  params: { slug: string };
}

// ---------------------------------------------------------------------------
// Metadata
// ---------------------------------------------------------------------------

export async function generateMetadata({ params }: Props) {
  try {
    const data = await fetchResort(params.slug);
    const { resort, snapshot } = data;
    const depth = snapshot.snow_depth_cm !== null ? `${snapshot.snow_depth_cm}cm base` : null;
    const desc = depth
      ? `${resort.name} ski conditions: ${depth}. Live rankings, 16-day forecast & AI condition analysis.`
      : `${resort.name} live ski conditions, rankings, and 16-day snow forecast on SkiRank.`;
    return {
      title: `${resort.name} Ski Conditions — SkiRank`,
      description: desc,
      openGraph: {
        title: `${resort.name} — SkiRank`,
        description: desc,
        type: "website",
      },
    };
  } catch {
    return { title: "Resort — SkiRank" };
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸", CA: "🇨🇦", FR: "🇫🇷", AT: "🇦🇹", CH: "🇨🇭",
  IT: "🇮🇹", JP: "🇯🇵", AU: "🇦🇺", NZ: "🇳🇿", NO: "🇳🇴",
  SE: "🇸🇪", DE: "🇩🇪", SK: "🇸🇰", SI: "🇸🇮", ES: "🇪🇸",
  AD: "🇦🇩", FI: "🇫🇮", KR: "🇰🇷", AR: "🇦🇷", CL: "🇨🇱",
  BG: "🇧🇬", RO: "🇷🇴", GB: "🇬🇧",
};

const CONTINENT_GRADIENT: Record<string, string> = {
  "North America": "from-blue-900 to-indigo-700",
  "Europe":        "from-red-900 to-rose-700",
  "Asia":          "from-emerald-900 to-teal-700",
  "South America": "from-orange-900 to-amber-700",
  "Oceania":       "from-cyan-900 to-sky-700",
};

function ordinal(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function qualityBadgeClass(q: string | undefined): string {
  switch (q) {
    case "verified":   return "bg-green-100 text-green-700";
    case "good":       return "bg-green-50 text-green-600";
    case "suspect":    return "bg-amber-100 text-amber-700";
    case "unreliable": return "bg-slate-100 text-slate-500";
    case "stale":      return "bg-slate-100 text-slate-400";
    default:           return "bg-slate-100 text-slate-500";
  }
}

function qualityLabel(q: string | undefined, source: string | null | undefined): string {
  if (q === "verified" && source === "manual_override") return "📝 Verified (manual)";
  if (q === "verified" && source === "synoptic_station") return "📡 Station verified";
  if (q === "good")       return "✅ Good data";
  if (q === "suspect")    return "⚠️ Suspect";
  if (q === "unreliable") return "❓ Uncertain";
  if (q === "stale")      return "🕐 Stale";
  return "· " + (q ?? "unknown");
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start) return "—";
  const fmt = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("en-GB", {
    weekday: "short", day: "numeric", month: "short",
  });
  if (!end || start === end) return fmt(start);
  return `${fmt(start)} – ${fmt(end)}`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ResortDetailPage({ params }: Props) {
  let data: ResortDetailFull;
  try {
    data = await fetchResort(params.slug);
  } catch {
    notFound();
  }

  const {
    resort,
    current_score,
    sub_scores,
    snapshot,
    data_quality,
    forecast,
    depth_history_30d,
    powder_intelligence,
    rankings,
    nearby_resorts,
    summary,
  } = data;

  const flag = resort.country ? (COUNTRY_FLAGS[resort.country] ?? resort.country) : "";
  const gradient = CONTINENT_GRADIENT[resort.continent ?? ""] ?? "from-slate-800 to-slate-600";

  const subScoreItems = [
    { label: "Base Depth",    value: sub_scores.base_depth,    icon: "🏔️" },
    { label: "Fresh Snow",    value: sub_scores.fresh_snow,    icon: "❄️" },
    { label: "Temperature",   value: sub_scores.temperature,   icon: "🌡️" },
    { label: "Wind",          value: sub_scores.wind,          icon: "💨" },
    { label: "Forecast",      value: sub_scores.forecast,      icon: "📅" },
  ];

  const powderDays = forecast.filter((f) => (f.snowfall_cm ?? 0) >= 10);

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className={`bg-gradient-to-br ${gradient} text-white`}>
        <div className="max-w-4xl mx-auto px-4 pt-6 pb-10">
          {/* Breadcrumb */}
          <nav className="text-xs text-white/60 mb-4 flex items-center gap-1.5">
            <Link href="/" className="hover:text-white transition-colors">SkiRank</Link>
            <span>/</span>
            {resort.continent && (
              <>
                <Link
                  href={`/?continent=${resort.continent.toLowerCase().replace(/\s+/g, "-")}`}
                  className="hover:text-white transition-colors"
                >
                  {resort.continent}
                </Link>
                <span>/</span>
              </>
            )}
            {resort.ski_region && (
              <>
                <span>{resort.ski_region}</span>
                <span>/</span>
              </>
            )}
            <span className="text-white/80">{resort.name}</span>
          </nav>

          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight">{resort.name}</h1>
                <span className="text-3xl">{flag}</span>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-white/70">
                {resort.ski_region && <span>{resort.ski_region}</span>}
                {resort.elevation_summit_m && (
                  <span>· Summit {resort.elevation_summit_m.toLocaleString()}m</span>
                )}
                {resort.elevation_base_m && (
                  <span>· Base {resort.elevation_base_m.toLocaleString()}m</span>
                )}
                {resort.vertical_drop_m && (
                  <span>· {resort.vertical_drop_m}m vertical</span>
                )}
                {resort.aspect && <span>· {resort.aspect}-facing</span>}
              </div>
              {resort.website_url && (
                <a
                  href={resort.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs text-white/60 hover:text-white underline underline-offset-2 transition-colors"
                >
                  Official website →
                </a>
              )}
            </div>

            {/* Score orb */}
            <div className="text-center">
              <ScoreGauge score={current_score} size={100} />
              <p className="text-xs text-white/60 mt-1">SkiRank score</p>
            </div>
          </div>

          {/* Hero stat strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
            {[
              {
                label: "Base depth",
                value: snapshot.snow_depth_cm !== null ? `${snapshot.snow_depth_cm} cm` : "—",
                sub: data_quality
                  ? <span className={`text-xs px-1.5 py-0.5 rounded-full ${qualityBadgeClass(data_quality.overall)}`}>
                      {qualityLabel(data_quality.overall, data_quality.depth_source)}
                    </span>
                  : null,
              },
              {
                label: "Fresh snow 72h",
                value: snapshot.new_snow_72h_cm !== null ? `${snapshot.new_snow_72h_cm} cm` : "—",
                sub: null,
              },
              {
                label: "Temperature",
                value: snapshot.temperature_c !== null ? `${snapshot.temperature_c}°C` : "—",
                sub: null,
              },
              {
                label: "7-day forecast",
                value: `${powder_intelligence.total_new_snow_7d} cm`,
                sub: <span className="text-xs text-white/50">new snow</span>,
              },
            ].map(({ label, value, sub }) => (
              <div key={label} className="bg-white/10 rounded-xl p-3 backdrop-blur-sm">
                <p className="text-xl font-bold">{value}</p>
                <p className="text-xs text-white/60 mt-0.5">{label}</p>
                {sub && <div className="mt-1">{sub}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">

        {/* ── AI Condition Summaries ──────────────────────────────────────── */}
        {summary && (
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-700 mb-4">
              ✨ AI Condition Analysis
            </h2>
            <ConditionSummaries summary={summary} />
          </section>
        )}

        {/* ── Rankings ───────────────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-700 mb-4">🏅 Rankings</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                label: "Global",
                rank: rankings.global_rank,
                total: rankings.global_total,
              },
              {
                label: resort.continent ?? "Continental",
                rank: rankings.continental_rank,
                total: rankings.continental_total,
              },
              {
                label: resort.ski_region ?? "Regional",
                rank: rankings.regional_rank,
                total: rankings.regional_total,
              },
            ].map(({ label, rank, total }) => (
              <div key={label} className="text-center p-3 bg-slate-50 rounded-xl">
                <p className="text-2xl font-extrabold text-slate-800">{ordinal(rank)}</p>
                <p className="text-xs text-slate-500 mt-0.5 truncate">{label}</p>
                {total !== null && total !== undefined && (
                  <p className="text-xs text-slate-400">of {total}</p>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── Score Deep-Dive ─────────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-700 mb-4">📊 Score Breakdown</h2>
          <div className="space-y-3">
            {subScoreItems.map(({ label, value, icon }) => (
              <div key={label} className="space-y-1">
                <div className="flex justify-between items-center text-xs text-slate-500">
                  <span>{icon} {label}</span>
                  <span className="font-medium text-slate-700">
                    {value !== null && value !== undefined ? Math.round(value) : "—"} / 100
                  </span>
                </div>
                <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${value !== null && value !== undefined ? Math.min(100, value) : 0}%`,
                      background: value !== null && value !== undefined && value >= 70
                        ? "linear-gradient(90deg,#22c55e,#16a34a)"
                        : value !== null && value !== undefined && value >= 40
                        ? "linear-gradient(90deg,#3b82f6,#2563eb)"
                        : "linear-gradient(90deg,#f59e0b,#d97706)",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Season Trajectory ───────────────────────────────────────────── */}
        {depth_history_30d.length > 2 && (
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-700 mb-4">
              📈 Season Trajectory — Base Depth
            </h2>
            <SeasonChart depthHistory={depth_history_30d} forecast={forecast} />
          </section>
        )}

        {/* ── Powder Intelligence ─────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-700 mb-4">
            ❄️ Powder Intelligence
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
            {[
              { label: "Powder days (14d)", value: String(powder_intelligence.powder_days_14d) },
              { label: "New snow (7d)",     value: `${powder_intelligence.total_new_snow_7d} cm` },
              { label: "New snow (14d)",    value: `${powder_intelligence.total_new_snow_14d} cm` },
              {
                label: "Best window",
                value: formatDateRange(
                  powder_intelligence.best_window_start,
                  powder_intelligence.best_window_end,
                ),
              },
            ].map(({ label, value }) => (
              <div key={label} className="text-center p-3 bg-blue-50 rounded-xl">
                <p className="text-xl font-bold text-blue-700">{value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{label}</p>
              </div>
            ))}
          </div>

          {powderDays.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-2">
                Powder days in forecast (≥10cm)
              </p>
              <div className="flex flex-wrap gap-2">
                {powderDays.map((f) => (
                  <div
                    key={String(f.forecast_date)}
                    className="flex items-center gap-1.5 bg-blue-600 text-white text-xs px-2.5 py-1 rounded-full font-medium"
                  >
                    <span>❄️</span>
                    <span>
                      {new Date(String(f.forecast_date) + "T12:00:00").toLocaleDateString("en-GB", {
                        weekday: "short", day: "numeric", month: "short",
                      })}
                    </span>
                    <span className="opacity-80">{f.snowfall_cm}cm</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {powderDays.length === 0 && (
            <p className="text-sm text-slate-400">No major powder days forecast in the next 14 days.</p>
          )}
        </section>

        {/* ── 16-Day Forecast ─────────────────────────────────────────────── */}
        <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-base font-semibold text-slate-700 mb-4">🗓 16-Day Forecast</h2>
          <ForecastTable forecast={forecast} highlightPowder />
        </section>

        {/* ── Mountain Profile ─────────────────────────────────────────────── */}
        {(resort.elevation_summit_m || resort.elevation_base_m || resort.num_runs || resort.vertical_drop_m) && (
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-700 mb-4">🏔️ Mountain Profile</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: "Summit", value: resort.elevation_summit_m ? `${resort.elevation_summit_m.toLocaleString()}m` : "—" },
                { label: "Base",   value: resort.elevation_base_m   ? `${resort.elevation_base_m.toLocaleString()}m`   : "—" },
                { label: "Vertical drop", value: resort.vertical_drop_m ? `${resort.vertical_drop_m}m` : "—" },
                { label: "Runs",   value: resort.num_runs ? String(resort.num_runs) : "—" },
              ].map(({ label, value }) => (
                <div key={label} className="text-center p-3 bg-slate-50 rounded-xl">
                  <p className="text-xl font-bold text-slate-800">{value}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{label}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── Nearby Resorts ──────────────────────────────────────────────── */}
        {nearby_resorts.length > 0 && (
          <section className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-base font-semibold text-slate-700 mb-4">
              📍 Nearby Resorts
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {nearby_resorts.map((nr) => (
                <Link
                  key={nr.slug}
                  href={`/resort/${nr.slug}`}
                  className="block border border-slate-200 rounded-xl p-4 hover:border-blue-300 hover:bg-blue-50/30 transition-colors group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-sm text-slate-800 group-hover:text-blue-700 transition-colors">
                      {nr.name}
                    </span>
                    {nr.country && (
                      <span className="text-base">{COUNTRY_FLAGS[nr.country] ?? nr.country}</span>
                    )}
                  </div>
                  <div className="flex items-center justify-between text-xs text-slate-500">
                    <span>{nr.distance_km} km away</span>
                    <div className="flex items-center gap-2">
                      {nr.snow_depth_cm !== null && (
                        <span className="text-blue-600 font-medium">{nr.snow_depth_cm}cm</span>
                      )}
                      {nr.score !== null && (
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">
                          {Math.round(nr.score)}
                        </span>
                      )}
                    </div>
                  </div>
                  {nr.ski_region && (
                    <p className="text-xs text-slate-400 mt-0.5">{nr.ski_region}</p>
                  )}
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Footer nav */}
        <div className="flex justify-between text-sm pb-4">
          <Link href="/" className="text-blue-500 hover:text-blue-700 transition-colors">
            ← Back to rankings
          </Link>
          {resort.website_url && (
            <a
              href={resort.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 hover:text-blue-700 transition-colors"
            >
              Official website →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
