"use client";

import { useState, useEffect, useCallback } from "react";
import type { RankingEntry, MetricsSnapshot, ClientWeights } from "../lib/types";
import { fetchRankings } from "../lib/api";
import { useAppContext } from "../context/AppContext";
import ResortCard from "./ResortCard";

// ── Client-side scoring ───────────────────────────────────────────────────────

function tempScore(c: number | null): number {
  if (c === null) return 0;
  if (c > 2)    return 0;
  if (c > 0)    return 20;
  if (c > -5)   return 60;
  if (c > -15)  return 100;
  if (c > -25)  return 80;
  return 50;
}

function windScore(kmh: number | null): number {
  if (kmh === null) return 0;
  if (kmh < 20)  return 100;
  if (kmh < 40)  return 80;
  if (kmh < 60)  return 50;
  if (kmh < 80)  return 20;
  return 0;
}

function calcClientScore(m: MetricsSnapshot | null | undefined, w: ClientWeights): number {
  if (!m) return 0;
  const totalWeight = w.base_depth + w.fresh_snow + w.forecast_snow + w.temperature + w.wind;
  if (totalWeight === 0) return 0;

  const norm = {
    base_depth:   Math.min(100, ((m.base_depth_cm ?? 0) / 200) * 100),
    fresh_snow:   Math.min(100, ((m.new_snow_72h_cm ?? 0) / 50) * 100),
    forecast_snow: Math.min(100, ((m.forecast_snow_cm ?? 0) / 60) * 100),
    temperature:  tempScore(m.temperature_c ?? null),
    wind:         windScore(m.wind_kmh ?? null),
  };

  return (
    norm.base_depth   * w.base_depth +
    norm.fresh_snow   * w.fresh_snow +
    norm.forecast_snow * w.forecast_snow +
    norm.temperature  * w.temperature +
    norm.wind         * w.wind
  ) / totalWeight;
}

function rankResorts(entries: RankingEntry[], weights: ClientWeights): RankingEntry[] {
  return [...entries]
    .sort((a, b) => calcClientScore(b.metrics, weights) - calcClientScore(a.metrics, weights));
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function RankingsList() {
  const { filters, state } = useAppContext();
  const [serverEntries, setServerEntries] = useState<RankingEntry[]>([]);
  const [sortedEntries, setSortedEntries] = useState<RankingEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch from API when filters (region/horizon) change
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchRankings(filters, 1, 200);
      setServerEntries(data.results);
      setTotal(data.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load rankings");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  // Re-rank and filter client-side when weights or hideUncertain change (debounced 150ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      const ranked = rankResorts(serverEntries, state.clientWeights);
      const filtered = state.hideUncertain
        ? ranked.filter((e) => {
            const q = e.data_quality?.overall;
            return q !== "unreliable" && q !== "stale";
          })
        : ranked;
      setSortedEntries(filtered);
    }, 150);
    return () => clearTimeout(timer);
  }, [serverEntries, state.clientWeights, state.hideUncertain]);

  if (error) {
    return (
      <div className="text-center py-16 text-red-500">
        <p className="text-lg font-medium">Error loading rankings</p>
        <p className="text-sm text-slate-500 mt-1">{error}</p>
        <button
          onClick={load}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">
          {loading ? "Loading…" : `${total.toLocaleString()} resorts`}
        </p>
      </div>

      <div className="space-y-3">
        {loading
          ? Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
            ))
          : sortedEntries.map((entry) => (
              <ResortCard key={entry.resort.id} entry={entry} />
            ))}
      </div>
    </div>
  );
}
