"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { HorizonDays, HierarchyResponse } from "../lib/types";
import { useAppContext } from "../context/AppContext";
import WeightSliders from "./WeightSliders";

const HORIZONS: { value: HorizonDays; label: string }[] = [
  { value: 0, label: "Today" },
  { value: 3, label: "3 Days" },
  { value: 7, label: "7 Days" },
  { value: 14, label: "14 Days" },
];

interface ControlBarProps {
  hierarchy: HierarchyResponse;
  totalResorts?: number;
}

export default function ControlBar({ hierarchy, totalResorts }: ControlBarProps) {
  const { state, dispatch } = useAppContext();
  const [showWeights, setShowWeights] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // On mount: read URL params and restore hierarchy state
  useEffect(() => {
    const cont = searchParams.get("continent");
    const mode = searchParams.get("mode") as "ski_region" | "country" | null;
    const srParam = searchParams.get("ski_region");
    const ctryParam = searchParams.get("country");

    if (cont) dispatch({ type: "SET_CONTINENT", payload: cont });
    if (mode) dispatch({ type: "SET_FILTER_MODE", payload: mode });
    if (srParam) dispatch({ type: "SET_SKI_REGIONS", payload: srParam.split(",").filter(Boolean) });
    if (ctryParam) dispatch({ type: "SET_COUNTRIES", payload: ctryParam.split(",").filter(Boolean) });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync URL when hierarchy state changes
  const syncUrl = useCallback(
    (continent: string | null, mode: string, skiRegions: string[], countries: string[]) => {
      const params = new URLSearchParams();
      if (continent) {
        params.set("continent", continent);
        if (mode !== "ski_region") params.set("mode", mode);
        if (mode === "ski_region" && skiRegions.length > 0)
          params.set("ski_region", skiRegions.join(","));
        if (mode === "country" && countries.length > 0)
          params.set("country", countries.join(","));
      }
      const qs = params.toString();
      router.replace(`/rankings${qs ? "?" + qs : ""}`, { scroll: false });
    },
    [router]
  );

  useEffect(() => {
    syncUrl(state.continent, state.filterMode, state.skiRegions, state.countries);
  }, [state.continent, state.filterMode, state.skiRegions, state.countries, syncUrl]);

  const activeContinentEntry = hierarchy.continents.find((c) => c.slug === state.continent);

  function setContinent(slug: string | null) {
    dispatch({ type: "SET_CONTINENT", payload: slug });
  }

  function toggleSkiRegion(slug: string) {
    dispatch({ type: "TOGGLE_SKI_REGION", payload: slug });
  }

  function toggleCountry(code: string) {
    dispatch({ type: "TOGGLE_COUNTRY", payload: code });
  }

  const allSkiRegionsSelected = state.skiRegions.length === 0;
  const allCountriesSelected = state.countries.length === 0;

  return (
    <div className="sticky top-0 z-20 bg-white/90 backdrop-blur border-b border-slate-200 shadow-sm">
      <div className="max-w-5xl mx-auto px-4 py-3 space-y-3">
        {/* Top row */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Horizon selector */}
          <div className="flex rounded-lg border border-slate-200 overflow-hidden">
            {HORIZONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => dispatch({ type: "SET_HORIZON", payload: value })}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  state.horizon === value
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Sort toggle */}
          <div className="flex rounded-lg border border-slate-200 overflow-hidden">
            <button
              onClick={() => dispatch({ type: "SET_SORT", payload: "score" })}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                state.sort === "score"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Score
            </button>
            <button
              onClick={() => dispatch({ type: "SET_SORT", payload: "predicted_snow" })}
              className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                state.sort === "predicted_snow"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              Predicted Snow
            </button>
          </div>

          {/* View toggle */}
          <div className="flex rounded-lg border border-slate-200 overflow-hidden ml-auto">
            {(["list", "map"] as const).map((v) => (
              <button
                key={v}
                onClick={() => dispatch({ type: "SET_VIEW", payload: v })}
                className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                  state.view === v
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                {v === "list" ? "List" : "Map"}
              </button>
            ))}
          </div>

          {/* Weights toggle */}
          <button
            onClick={() => setShowWeights((p) => !p)}
            className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg bg-white text-slate-600 hover:bg-slate-50 transition-colors"
          >
            {showWeights ? "Hide weights" : "Adjust weights"}
          </button>
        </div>

        {/* Level 1: Continent tabs */}
        {hierarchy.continents.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setContinent(null)}
              className={`rounded-full px-3 py-1 text-sm transition-colors ${
                state.continent === null
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              All
            </button>
            {hierarchy.continents.map((cont) => (
              <button
                key={cont.slug}
                onClick={() => setContinent(cont.slug === state.continent ? null : cont.slug)}
                className={`rounded-full px-3 py-1 text-sm transition-colors ${
                  state.continent === cont.slug
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {cont.label} ({cont.resort_count})
              </button>
            ))}
          </div>
        )}

        {/* Level 2: Browse mode toggle (only when continent selected) */}
        {activeContinentEntry && (
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-slate-500">Browse by:</span>
            <div className="flex rounded-lg border border-slate-200 overflow-hidden">
              {activeContinentEntry.ski_regions.length > 0 && (
                <button
                  onClick={() => dispatch({ type: "SET_FILTER_MODE", payload: "ski_region" })}
                  className={`px-3 py-1 text-xs font-medium transition-colors ${
                    state.filterMode === "ski_region"
                      ? "bg-blue-600 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  Ski Region
                </button>
              )}
              <button
                onClick={() => dispatch({ type: "SET_FILTER_MODE", payload: "country" })}
                className={`px-3 py-1 text-xs font-medium transition-colors ${
                  state.filterMode === "country"
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-600 hover:bg-slate-50"
                }`}
              >
                Country
              </button>
            </div>
            {totalResorts !== undefined && (
              <span className="text-xs text-slate-400 ml-auto">
                Showing {totalResorts} resort{totalResorts !== 1 ? "s" : ""}
              </span>
            )}
          </div>
        )}

        {/* Level 3a: Ski region pills */}
        {activeContinentEntry && state.filterMode === "ski_region" && activeContinentEntry.ski_regions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => dispatch({ type: "SET_SKI_REGIONS", payload: [] })}
              className={`rounded-full px-3 py-1 text-sm transition-colors border ${
                allSkiRegionsSelected
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
              }`}
            >
              All
            </button>
            {activeContinentEntry.ski_regions.map((sr) => {
              const active = state.skiRegions.includes(sr.slug);
              return (
                <button
                  key={sr.slug}
                  onClick={() => toggleSkiRegion(sr.slug)}
                  className={`rounded-full px-3 py-1 text-sm transition-colors border ${
                    active
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
                  }`}
                >
                  {sr.label} ({sr.resort_count})
                </button>
              );
            })}
          </div>
        )}

        {/* Level 3b: Country pills */}
        {activeContinentEntry && state.filterMode === "country" && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => dispatch({ type: "SET_COUNTRIES", payload: [] })}
              className={`rounded-full px-3 py-1 text-sm transition-colors border ${
                allCountriesSelected
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
              }`}
            >
              All
            </button>
            {activeContinentEntry.countries.map((c) => {
              const active = state.countries.includes(c.code);
              return (
                <button
                  key={c.code}
                  onClick={() => toggleCountry(c.code)}
                  className={`rounded-full px-3 py-1 text-sm transition-colors border ${
                    active
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-slate-600 border-slate-300 hover:border-slate-400"
                  }`}
                >
                  {c.flag} {c.label} ({c.resort_count})
                </button>
              );
            })}
          </div>
        )}

        {/* Expandable weights panel */}
        {showWeights && (
          <div className="border border-slate-200 rounded-xl p-4 bg-slate-50">
            <WeightSliders />
          </div>
        )}
      </div>
    </div>
  );
}
