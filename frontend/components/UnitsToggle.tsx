"use client";

import { useAppContext } from "../context/AppContext";

export default function UnitsToggle() {
  const { state, dispatch } = useAppContext();
  const isMetric = state.unitSystem === "metric";

  return (
    <button
      onClick={() =>
        dispatch({
          type: "SET_UNITS",
          payload: isMetric ? "imperial" : "metric",
        })
      }
      title="Switch units"
      className="text-xs px-2.5 py-1 rounded-full border border-slate-200 bg-white text-slate-500 hover:border-blue-300 hover:text-blue-600 transition-colors font-mono"
    >
      {isMetric ? "cm · °C" : "in · °F"}
    </button>
  );
}
