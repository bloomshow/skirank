"use client";

import Link from "next/link";
import type { RankingEntry, ForecastSnowDay } from "../lib/types";

const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸", CA: "🇨🇦", FR: "🇫🇷", AT: "🇦🇹", CH: "🇨🇭",
  IT: "🇮🇹", JP: "🇯🇵", AU: "🇦🇺", NZ: "🇳🇿", NO: "🇳🇴",
  SE: "🇸🇪", DE: "🇩🇪", SK: "🇸🇰", SI: "🇸🇮", ES: "🇪🇸",
  AR: "🇦🇷", CL: "🇨🇱", KR: "🇰🇷", CN: "🇨🇳", BG: "🇧🇬",
  AD: "🇦🇩", RO: "🇷🇴", FI: "🇫🇮",
};

function scoreBadgeClass(score: number | null): string {
  if (score === null) return "bg-slate-200 text-slate-600";
  if (score >= 80) return "bg-green-100 text-green-800";
  if (score >= 60) return "bg-yellow-100 text-yellow-800";
  if (score >= 40) return "bg-orange-100 text-orange-800";
  return "bg-red-100 text-red-800";
}

function SubBar({ label, value }: { label: string; value: number | null }) {
  const pct = value !== null ? Math.min(100, Math.max(0, value)) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 text-slate-500 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-6 text-right text-slate-500">{value !== null ? Math.round(value) : "—"}</span>
    </div>
  );
}

function SnowSparkline({ days }: { days: ForecastSnowDay[] }) {
  const max = Math.max(1, ...days.map((d) => d.snowfall_cm ?? 0));
  return (
    <svg width={7 * 8} height={40} className="mt-2">
      {days.map((d, i) => {
        const h = d.snowfall_cm ? (d.snowfall_cm / max) * 36 : 0;
        return (
          <rect
            key={i}
            x={i * 8}
            y={40 - h}
            width={6}
            height={h}
            className="fill-blue-400"
            rx={1}
          />
        );
      })}
    </svg>
  );
}

function formatDepth(cm: number | null): string {
  if (cm === null) return "—";
  const inches = Math.round(cm / 2.54);
  return `${cm}cm (${inches}")`;
}

interface ResortCardProps {
  entry: RankingEntry;
}

export default function ResortCard({ entry }: ResortCardProps) {
  const { rank, resort, score, sub_scores, snapshot, stale_data, predicted_snow_cm, forecast_sparkline, forecast_source, depth_source } = entry;
  const flag = resort.country ? (COUNTRY_FLAGS[resort.country] ?? resort.country) : "";

  return (
    <Link
      href={`/resort/${resort.slug}`}
      className="block bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md hover:border-blue-300 transition-all p-4"
    >
      <div className="flex items-start gap-4">
        {/* Rank */}
        <div className="text-2xl font-bold text-slate-400 w-10 text-center shrink-0">
          {rank}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-base font-semibold text-slate-900 truncate">{resort.name}</span>
            <span className="text-base">{flag}</span>
            {resort.region && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {resort.region}
              </span>
            )}
            {stale_data && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                stale data
              </span>
            )}
          </div>
          {resort.elevation_summit_m && (
            <p className="text-xs text-slate-400 mt-0.5">
              Summit {resort.elevation_summit_m.toLocaleString()}m
            </p>
          )}

          {/* Snapshot stats */}
          <div className="flex gap-4 mt-2 text-xs text-slate-600 flex-wrap">
            <span className="flex items-center gap-1">
              <span className="text-slate-400">Base</span>{" "}
              {formatDepth(snapshot.snow_depth_cm)}
              {snapshot.snow_depth_cm !== null && snapshot.snow_depth_cm < 20 && (
                <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-xs">thin cover</span>
              )}
              {depth_source && (
                <span
                  title={depth_source === "synoptic_station" ? "Snow depth from on-mountain station" : "Snow depth estimated from weather model"}
                  className={`hidden sm:inline px-1.5 py-0.5 rounded text-xs font-medium ${
                    depth_source === "synoptic_station"
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {depth_source === "synoptic_station" ? "Station" : "Estimated"}
                </span>
              )}
            </span>
            <span>
              <span className="text-slate-400">New 72h</span>{" "}
              {snapshot.new_snow_72h_cm !== null ? `${snapshot.new_snow_72h_cm}cm` : "—"}
            </span>
            <span>
              <span className="text-slate-400">Temp</span>{" "}
              {snapshot.temperature_c !== null ? `${snapshot.temperature_c}°C` : "—"}
            </span>
            <span>
              <span className="text-slate-400">Wind</span>{" "}
              {snapshot.wind_speed_kmh !== null ? `${snapshot.wind_speed_kmh}km/h` : "—"}
            </span>
            {predicted_snow_cm !== null && (
              <span className="flex items-center gap-1">
                <span className="text-slate-400">7d snow</span>{" "}
                {Math.round(predicted_snow_cm)}cm
                {forecast_source && (
                  <span
                    title={forecast_source === "nws_hrrr" ? "Forecast from NWS HRRR high-resolution model (3km)" : "Forecast from Open-Meteo global ensemble model"}
                    className={`hidden sm:inline px-1.5 py-0.5 rounded text-xs font-medium ${
                      forecast_source === "nws_hrrr"
                        ? "bg-green-100 text-green-700"
                        : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {forecast_source === "nws_hrrr" ? "High-res" : "Global model"}
                  </span>
                )}
              </span>
            )}
          </div>

          {/* Snow sparkline */}
          {forecast_sparkline && forecast_sparkline.length > 0 && (
            <SnowSparkline days={forecast_sparkline} />
          )}

          {/* Sub-score bars */}
          <div className="mt-3 space-y-1">
            <SubBar label="Base" value={sub_scores.base_depth} />
            <SubBar label="Fresh" value={sub_scores.fresh_snow} />
            <SubBar label="Temp" value={sub_scores.temperature} />
            <SubBar label="Wind" value={sub_scores.wind} />
          </div>
        </div>

        {/* Score badge */}
        <div className={`shrink-0 px-3 py-1.5 rounded-xl text-lg font-bold ${scoreBadgeClass(score)}`}>
          {score !== null ? Math.round(score) : "—"}
        </div>
      </div>
    </Link>
  );
}
