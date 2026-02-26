"use client";

import { useAppContext } from "../context/AppContext";

const WEIGHT_KEYS = [
  { key: "w_base_depth", label: "Base Depth" },
  { key: "w_fresh_snow", label: "Fresh Snow" },
  { key: "w_temperature", label: "Temperature" },
  { key: "w_wind", label: "Wind" },
] as const;

type WeightKey = (typeof WEIGHT_KEYS)[number]["key"];

export default function WeightSliders() {
  const { state, dispatch } = useAppContext();

  function handleChange(key: WeightKey, value: number) {
    dispatch({ type: "SET_WEIGHTS", payload: { [key]: value / 100 } });
  }

  function handleReset() {
    dispatch({ type: "RESET_WEIGHTS" });
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-slate-700">Score Weights</span>
        <button
          onClick={handleReset}
          className="text-xs text-blue-500 hover:text-blue-700 underline"
        >
          Reset defaults
        </button>
      </div>
      {WEIGHT_KEYS.map(({ key, label }) => {
        const pct = Math.round(((state.weights as Record<string, number>)[key] ?? 0.25) * 100);
        return (
          <div key={key} className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span>{label}</span>
              <span>{pct}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={pct}
              onChange={(e) => handleChange(key, Number(e.target.value))}
              className="w-full accent-blue-500"
            />
          </div>
        );
      })}
    </div>
  );
}
