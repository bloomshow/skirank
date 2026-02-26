"use client";

import { useCallback } from "react";
import { useAppContext } from "../context/AppContext";
import type { ClientWeights } from "../lib/types";
import { DEFAULT_CLIENT_WEIGHTS } from "../lib/types";

const SLIDERS: { key: keyof ClientWeights; icon: string; label: string }[] = [
  { key: "base_depth", icon: "❄️", label: "Base Depth" },
  { key: "fresh_snow", icon: "🌨️", label: "Fresh Snow" },
  { key: "forecast_snow", icon: "🔮", label: "Forecast Snow" },
  { key: "temperature", icon: "🌡️", label: "Temperature" },
  { key: "wind", icon: "💨", label: "Light Winds" },
];

export default function WeightSliders() {
  const { state, dispatch } = useAppContext();

  const handleChange = useCallback(
    (key: keyof ClientWeights, value: number) => {
      dispatch({ type: "SET_CLIENT_WEIGHT", key, value });
    },
    [dispatch]
  );

  const handleReset = useCallback(() => {
    dispatch({ type: "RESET_CLIENT_WEIGHTS" });
  }, [dispatch]);

  const isDefault =
    JSON.stringify(state.clientWeights) ===
    JSON.stringify(DEFAULT_CLIENT_WEIGHTS);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-slate-800">
            What matters to you?
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            Drag to prioritise — rankings update instantly.
          </p>
        </div>
        {!isDefault && (
          <button
            onClick={handleReset}
            className="text-xs text-blue-500 hover:text-blue-700 underline shrink-0 mt-0.5"
          >
            Reset to defaults
          </button>
        )}
      </div>
      <div className="space-y-3">
        {SLIDERS.map(({ key, icon, label }) => {
          const value = state.clientWeights[key];
          const isZero = value === 0;
          return (
            <div key={key}>
              <div className="flex justify-between items-center mb-1 text-xs">
                <span
                  className={`flex items-center gap-1.5 ${
                    isZero ? "text-slate-400" : "text-slate-700"
                  }`}
                >
                  <span>{icon}</span>
                  <span className={isZero ? "line-through" : ""}>{label}</span>
                  {isZero && (
                    <span className="italic text-slate-400">not counted</span>
                  )}
                </span>
                <span
                  className={`font-mono font-semibold tabular-nums w-4 text-right ${
                    isZero ? "text-slate-400" : "text-slate-700"
                  }`}
                >
                  {value}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={10}
                step={1}
                value={value}
                onChange={(e) => handleChange(key, Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer accent-blue-500"
                style={isZero ? { accentColor: "#cbd5e1" } : undefined}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
