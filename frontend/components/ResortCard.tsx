"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import type { RankingEntry, ForecastSnowDay, ForecastDay, ClientWeights } from "../lib/types";
import { fetchResortForecast } from "../lib/api";
import { useAppContext } from "../context/AppContext";
import { fmtDepth, fmtSnow, fmtTemp, fmtWind } from "../lib/units";

const COUNTRY_FLAGS: Record<string, string> = {
  US: "🇺🇸", CA: "🇨🇦", FR: "🇫🇷", AT: "🇦🇹", CH: "🇨🇭",
  IT: "🇮🇹", JP: "🇯🇵", AU: "🇦🇺", NZ: "🇳🇿", NO: "🇳🇴",
  SE: "🇸🇪", DE: "🇩🇪", SK: "🇸🇰", SI: "🇸🇮", ES: "🇪🇸",
  AR: "🇦🇷", CL: "🇨🇱", KR: "🇰🇷", CN: "🇨🇳", BG: "🇧🇬",
  AD: "🇦🇩", RO: "🇷🇴", FI: "🇫🇮", GB: "🇬🇧",
};

// ── Tile colour helpers ───────────────────────────────────────────────────────

function baseTileColor(cm: number | null): string {
  if (cm === null) return "bg-slate-50 text-slate-400";
  if (cm > 150) return "bg-green-50 text-green-800";
  if (cm > 80)  return "bg-yellow-50 text-yellow-800";
  if (cm > 0)   return "bg-red-50 text-red-800";
  return "bg-slate-50 text-slate-500";
}

function snowTileColor(cm: number | null, greenThreshold: number, yellowThreshold: number): string {
  if (cm === null || cm === 0) return "bg-slate-50 text-slate-500";
  if (cm > greenThreshold)  return "bg-green-50 text-green-800";
  if (cm > yellowThreshold) return "bg-yellow-50 text-yellow-800";
  return "bg-slate-50 text-slate-500";
}

function tempTileColor(c: number | null): string {
  if (c === null) return "bg-slate-50 text-slate-400";
  if (c > 2)    return "bg-red-50 text-red-800";
  if (c > 0)    return "bg-orange-50 text-orange-800";
  if (c > -5)   return "bg-yellow-50 text-yellow-800";
  if (c > -15)  return "bg-green-50 text-green-800";
  if (c > -25)  return "bg-blue-50 text-blue-700";
  return "bg-indigo-50 text-indigo-700";
}

function windTileColor(kmh: number | null): string {
  if (kmh === null) return "bg-slate-50 text-slate-400";
  if (kmh < 20)  return "bg-green-50 text-green-800";
  if (kmh < 50)  return "bg-yellow-50 text-yellow-800";
  return "bg-red-50 text-red-800";
}

function neutralTile(): string {
  return "bg-slate-50 text-slate-500";
}

// ── Sparkline ─────────────────────────────────────────────────────────────────

function MiniSparkline({ days }: { days: ForecastSnowDay[] }) {
  const vals = days.map((d) => d.snowfall_cm ?? 0);
  const max = Math.max(1, ...vals);
  return (
    <svg width={days.length * 7} height={24} className="mt-1">
      {vals.map((v, i) => {
        const h = (v / max) * 20;
        return (
          <rect
            key={i}
            x={i * 7}
            y={24 - h}
            width={5}
            height={h}
            className="fill-blue-300"
            rx={1}
          />
        );
      })}
    </svg>
  );
}

// ── Metric tile ───────────────────────────────────────────────────────────────

interface TileProps {
  icon: string;
  primary: string;
  secondary?: string;
  label: string;
  colorClass: string;
  isZeroWeight?: boolean;
  children?: React.ReactNode;
}

function MetricTile({ icon, primary, secondary, label, colorClass, isZeroWeight, children }: TileProps) {
  const cls = isZeroWeight ? "bg-slate-50 text-slate-400" : colorClass;
  return (
    <div className={`flex-1 min-w-0 rounded-lg px-1.5 py-2 text-center ${cls}`}>
      <div className="text-sm leading-none mb-0.5">{icon}</div>
      <div className="text-sm font-semibold leading-tight truncate">{primary}</div>
      {secondary && (
        <div className="text-xs opacity-60 leading-tight hidden sm:block">{secondary}</div>
      )}
      <div className="text-xs opacity-70 mt-0.5 leading-tight truncate">{label}</div>
      {children}
    </div>
  );
}

// ── Forecast table (expanded) ─────────────────────────────────────────────────

function ForecastTable({ days, units }: { days: ForecastDay[]; units: "metric" | "imperial" }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-slate-600 border-collapse">
        <thead>
          <tr className="text-slate-400 border-b border-slate-100">
            <th className="text-left py-1 pr-3 font-medium">Date</th>
            <th className="text-right py-1 pr-3 font-medium">Snow</th>
            <th className="text-right py-1 pr-3 font-medium">High</th>
            <th className="text-right py-1 pr-3 font-medium">Low</th>
            <th className="text-right py-1 font-medium">Wind</th>
          </tr>
        </thead>
        <tbody>
          {days.slice(0, 16).map((d) => {
            const snow = fmtSnow(d.snowfall_cm, units);
            const hi = fmtTemp(d.temperature_max_c, units);
            const lo = fmtTemp(d.temperature_min_c, units);
            const wind = fmtWind(d.wind_speed_max_kmh, units);
            return (
              <tr key={d.forecast_date} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="py-1 pr-3">
                  {new Date(d.forecast_date + "T12:00:00").toLocaleDateString(undefined, {
                    month: "short", day: "numeric",
                  })}
                </td>
                <td className="text-right py-1 pr-3 font-medium">
                  {d.snowfall_cm ? snow.primary : <span className="text-slate-300">—</span>}
                </td>
                <td className="text-right py-1 pr-3">{hi.primary}</td>
                <td className="text-right py-1 pr-3">{lo.primary}</td>
                <td className="text-right py-1">{wind.primary}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface ResortCardProps {
  entry: RankingEntry;
}

export default function ResortCard({ entry }: ResortCardProps) {
  const { state } = useAppContext();
  const { resort, stale_data, forecast_sparkline, forecast_source, depth_source, metrics, position_delta } = entry;
  const { unitSystem, clientWeights, horizon } = state;

  const [expanded, setExpanded] = useState(false);
  const [fullForecast, setFullForecast] = useState<ForecastDay[] | null>(null);
  const [loadingForecast, setLoadingForecast] = useState(false);

  useEffect(() => {
    if (!expanded || fullForecast !== null) return;
    setLoadingForecast(true);
    fetchResortForecast(resort.slug)
      .then(setFullForecast)
      .catch(() => setFullForecast([]))
      .finally(() => setLoadingForecast(false));
  }, [expanded, resort.slug, fullForecast]);

  const flag = resort.country ? (COUNTRY_FLAGS[resort.country] ?? "") : "";

  // ── Format metric values ──
  const depth = fmtDepth(metrics?.base_depth_cm, unitSystem);
  const fresh = fmtSnow(metrics?.new_snow_72h_cm, unitSystem);
  const fcst  = fmtSnow(metrics?.forecast_snow_cm, unitSystem);
  const temp  = fmtTemp(metrics?.temperature_c, unitSystem);
  const wind  = fmtWind(metrics?.wind_kmh, unitSystem);

  const forecastLabel = horizon === 0 ? "7-day" : `${horizon}-day`;

  // Forecast display: show "None forecast" if 0
  const fcstPrimary =
    (metrics?.forecast_snow_cm ?? 0) === 0 ? "None" : fcst.primary;
  const fcstColorClass =
    (metrics?.forecast_snow_cm ?? 0) === 0
      ? "bg-slate-50 text-slate-400"
      : snowTileColor(metrics?.forecast_snow_cm ?? null, 30, 10);

  // ── Position delta ──
  const deltaEl =
    position_delta !== null && position_delta !== undefined ? (
      <span
        className={`text-xs font-medium opacity-50 ${
          position_delta > 0
            ? "text-green-600"
            : position_delta < 0
            ? "text-red-500"
            : "text-slate-400"
        }`}
      >
        {position_delta > 0
          ? `▲${position_delta}`
          : position_delta < 0
          ? `▼${Math.abs(position_delta)}`
          : "—"}
      </span>
    ) : null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-4 pb-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Link
              href={`/resort/${resort.slug}`}
              className="text-base font-semibold text-slate-900 hover:text-blue-600 transition-colors"
            >
              {resort.name}
            </Link>
            <span className="text-base">{flag}</span>
            {(resort.ski_region || resort.region) && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">
                {resort.ski_region ?? resort.region}
              </span>
            )}
            {stale_data && (
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                stale
              </span>
            )}
          </div>
          {resort.elevation_summit_m && (
            <p className="text-xs text-slate-400 mt-0.5">
              Summit {resort.elevation_summit_m.toLocaleString()}m
            </p>
          )}
        </div>
        {deltaEl}
      </div>

      {/* Metric tiles */}
      <div className="flex gap-1.5 px-3 pb-3">
        <MetricTile
          icon="❄️"
          primary={depth.primary}
          secondary={depth.secondary}
          label="Base"
          colorClass={baseTileColor(metrics?.base_depth_cm ?? null)}
          isZeroWeight={clientWeights.base_depth === 0}
        />
        <MetricTile
          icon="🌨️"
          primary={fresh.primary}
          secondary={fresh.secondary || undefined}
          label="72h fresh"
          colorClass={snowTileColor(metrics?.new_snow_72h_cm ?? null, 20, 5)}
          isZeroWeight={clientWeights.fresh_snow === 0}
        />
        <MetricTile
          icon="🔮"
          primary={fcstPrimary}
          secondary={fcst.secondary || undefined}
          label={forecastLabel}
          colorClass={fcstColorClass}
          isZeroWeight={clientWeights.forecast_snow === 0}
        >
          {forecast_sparkline && forecast_sparkline.length > 0 && (
            <MiniSparkline days={forecast_sparkline} />
          )}
        </MetricTile>
        <MetricTile
          icon="🌡️"
          primary={temp.primary}
          secondary={temp.secondary || undefined}
          label="Temp"
          colorClass={tempTileColor(metrics?.temperature_c ?? null)}
          isZeroWeight={clientWeights.temperature === 0}
        />
        <MetricTile
          icon="💨"
          primary={wind.primary}
          secondary={wind.secondary || undefined}
          label="Wind"
          colorClass={windTileColor(metrics?.wind_kmh ?? null)}
          isZeroWeight={clientWeights.wind === 0}
        />
      </div>

      {/* Footer: source badges + expand */}
      <div className="border-t border-slate-100 px-4 py-2 flex items-center gap-3 text-xs text-slate-400">
        {depth_source === "synoptic_station" && (
          <span title="Snow depth from on-mountain weather station">📡 Station</span>
        )}
        {forecast_source === "nws_hrrr" && (
          <span title="Forecast from NWS HRRR high-resolution model (3km)">🎯 High-res</span>
        )}
        <button
          onClick={() => setExpanded((p) => !p)}
          className="ml-auto text-xs text-blue-500 hover:text-blue-700 transition-colors"
        >
          {expanded ? "↑ Less" : "↓ More"}
        </button>
      </div>

      {/* Expanded section */}
      {expanded && (
        <div className="border-t border-slate-100 px-4 py-4 space-y-4">
          {loadingForecast && (
            <div className="text-xs text-slate-400">Loading forecast…</div>
          )}
          {fullForecast && fullForecast.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-2">16-day forecast</p>
              <ForecastTable days={fullForecast} units={unitSystem} />
            </div>
          )}
          <div className="flex flex-wrap gap-3 text-xs text-slate-500">
            {depth_source && (
              <span>
                Depth source:{" "}
                <span className="font-medium text-slate-700">
                  {depth_source === "synoptic_station" ? "On-mountain station" : "Weather model"}
                </span>
              </span>
            )}
            {forecast_source && (
              <span>
                Forecast:{" "}
                <span className="font-medium text-slate-700">
                  {forecast_source === "nws_hrrr" ? "NWS HRRR (3km)" : "Open-Meteo global"}
                </span>
              </span>
            )}
          </div>
          <div className="flex gap-4 text-xs">
            {resort.website_url && (
              <a
                href={resort.website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:text-blue-700"
              >
                Resort website →
              </a>
            )}
            <Link
              href={`/resort/${resort.slug}`}
              className="text-blue-500 hover:text-blue-700"
            >
              Full conditions page →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
