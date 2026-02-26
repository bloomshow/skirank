"use client";

import { useState } from "react";
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

  // Union of subregions from all selected regions
  const visibleSubregions = [...new Set(
    regions
      .filter((r) => state.regions.includes(r.region))
      .flatMap((r) => r.subregions)
  )];

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
                {r.region}
              </button>
            ))}
          </div>
        )}

        {/* Subregion pill row — union of subregions from all selected regions */}
        {visibleSubregions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {visibleSubregions.map((sub) => (
              <button
                key={sub}
                onClick={() => dispatch({ type: "TOGGLE_SUBREGION", payload: sub })}
                className={`rounded-full px-3 py-1 text-sm transition-colors ${
                  state.subregions.includes(sub)
                    ? "bg-blue-600 text-white"
                    : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
              >
                {sub}
              </button>
            ))}
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
