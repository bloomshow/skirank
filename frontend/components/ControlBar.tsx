"use client";

import { useState, useEffect } from "react";
import type { HorizonDays, RegionEntry } from "../lib/types";
import { useAppContext } from "../context/AppContext";
import WeightSliders from "./WeightSliders";

const HORIZONS: { value: HorizonDays; label: string }[] = [
  { value: 0, label: "Today" },
  { value: 3, label: "3 Days" },
  { value: 7, label: "7 Days" },
  { value: 14, label: "14 Days" },
];

interface ControlBarProps {
  regions: RegionEntry[];
}

export default function ControlBar({ regions }: ControlBarProps) {
  const { state, dispatch } = useAppContext();
  const [showWeights, setShowWeights] = useState(false);
  // Tracks whether user explicitly deselected all pills (vs default all-selected)
  const [explicitDeselect, setExplicitDeselect] = useState(false);

  // Union of subregions from all selected regions
  const visibleSubregions = [...new Set(
    regions
      .filter((r) => state.regions.includes(r.region))
      .flatMap((r) => r.subregions)
  )];

  // Merged subregion counts across all selected regions
  const subregionCounts: Record<string, number> = {};
  regions
    .filter((r) => state.regions.includes(r.region))
    .forEach((r) => {
      Object.entries(r.subregion_counts ?? {}).forEach(([sub, cnt]) => {
        subregionCounts[sub] = (subregionCounts[sub] ?? 0) + cnt;
      });
    });

  // Reset explicitDeselect when region changes
  useEffect(() => {
    setExplicitDeselect(false);
  }, [state.regions.join(",")]);

  // A pill is visually active if:
  // - not in explicit-deselect-all mode AND (no specific selections OR this sub is selected)
  const allSelected = !explicitDeselect && state.subregions.length === 0;
  function isPillActive(sub: string): boolean {
    if (explicitDeselect && state.subregions.length === 0) return false;
    return state.subregions.length === 0 || state.subregions.includes(sub);
  }

  function toggleSub(sub: string) {
    setExplicitDeselect(false);
    if (allSelected) {
      // Going from "all selected" → deselect this one → include all except this
      const next = visibleSubregions.filter((s) => s !== sub);
      dispatch({ type: "SET_SUBREGIONS", payload: next });
    } else {
      const current = state.subregions;
      const next = current.includes(sub)
        ? current.filter((s) => s !== sub)
        : [...current, sub];
      // If all are now selected, collapse back to "no filter" state
      if (next.length === visibleSubregions.length) {
        dispatch({ type: "SET_SUBREGIONS", payload: [] });
      } else {
        dispatch({ type: "SET_SUBREGIONS", payload: next });
      }
    }
  }

  function selectAll() {
    setExplicitDeselect(false);
    dispatch({ type: "SET_SUBREGIONS", payload: [] });
  }

  function deselectAll() {
    setExplicitDeselect(true);
    dispatch({ type: "SET_SUBREGIONS", payload: [] });
  }

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

        {/* Region pill row */}
        {regions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => dispatch({ type: "CLEAR_REGIONS" })}
              className={`rounded-full px-3 py-1 text-sm transition-colors ${
                state.regions.length === 0
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              All regions
            </button>
            {regions.map((r) => (
              <button
                key={r.region}
                onClick={() => dispatch({ type: "TOGGLE_REGION", payload: r.region })}
                className={`rounded-full px-3 py-1 text-sm transition-colors ${
                  state.regions.includes(r.region)
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {r.region} ({r.resort_count})
              </button>
            ))}
          </div>
        )}

        {/* Subregion pill row */}
        {visibleSubregions.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Subregions:</span>
              <button
                onClick={selectAll}
                className="text-xs text-blue-600 hover:text-blue-800 underline"
              >
                Select all
              </button>
              <span className="text-xs text-slate-300">|</span>
              <button
                onClick={deselectAll}
                className="text-xs text-slate-500 hover:text-slate-700 underline"
              >
                Deselect all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {visibleSubregions.map((sub) => {
                const active = isPillActive(sub);
                const count = subregionCounts[sub];
                return (
                  <button
                    key={sub}
                    onClick={() => toggleSub(sub)}
                    className={`rounded-full px-3 py-1 text-sm transition-colors border ${
                      active
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-white text-slate-500 border-slate-300 hover:border-slate-400"
                    }`}
                  >
                    {sub}{count !== undefined ? ` (${count})` : ""}
                  </button>
                );
              })}
            </div>
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
