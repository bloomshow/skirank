"use client";

import React, { createContext, useContext, useReducer, useEffect } from "react";
import type { HorizonDays, WeightOverrides, RankingsFilters } from "../lib/types";

interface AppState {
  horizon: HorizonDays;
  regions: string[];
  subregions: string[];
  country: string | undefined;
  weights: WeightOverrides;
  view: "list" | "map";
  sort: "score" | "predicted_snow";
}

type Action =
  | { type: "SET_HORIZON"; payload: HorizonDays }
  | { type: "TOGGLE_REGION"; payload: string }
  | { type: "CLEAR_REGIONS" }
  | { type: "TOGGLE_SUBREGION"; payload: string }
  | { type: "SET_COUNTRY"; payload: string | undefined }
  | { type: "SET_WEIGHTS"; payload: WeightOverrides }
  | { type: "SET_VIEW"; payload: "list" | "map" }
  | { type: "SET_SORT"; payload: "score" | "predicted_snow" }
  | { type: "RESET_WEIGHTS" };

const DEFAULT_STATE: AppState = {
  horizon: 0,
  regions: [],
  subregions: [],
  country: undefined,
  weights: {},
  view: "list",
  sort: "score",
};

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case "SET_HORIZON":
      return { ...state, horizon: action.payload };
    case "TOGGLE_REGION": {
      const already = state.regions.includes(action.payload);
      const regions = already
        ? state.regions.filter((r) => r !== action.payload)
        : [...state.regions, action.payload];
      return { ...state, regions, subregions: [] };
    }
    case "CLEAR_REGIONS":
      return { ...state, regions: [], subregions: [] };
    case "TOGGLE_SUBREGION": {
      const already = state.subregions.includes(action.payload);
      const subregions = already
        ? state.subregions.filter((s) => s !== action.payload)
        : [...state.subregions, action.payload];
      return { ...state, subregions };
    }
    case "SET_COUNTRY":
      return { ...state, country: action.payload };
    case "SET_WEIGHTS":
      return { ...state, weights: { ...state.weights, ...action.payload } };
    case "RESET_WEIGHTS":
      return { ...state, weights: {} };
    case "SET_VIEW":
      return { ...state, view: action.payload };
    case "SET_SORT":
      return { ...state, sort: action.payload };
    default:
      return state;
  }
}

interface AppContextValue {
  state: AppState;
  dispatch: React.Dispatch<Action>;
  filters: RankingsFilters;
}

const AppContext = createContext<AppContextValue | null>(null);

const STORAGE_KEY = "skirank_prefs";

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(reducer, DEFAULT_STATE, (init) => {
    if (typeof window === "undefined") return init;
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<AppState>;
        return { ...init, ...parsed };
      }
    } catch {}
    return init;
  });

  // Persist user preferences on change
  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ horizon: state.horizon, regions: state.regions, weights: state.weights })
      );
    } catch {}
  }, [state.horizon, state.regions, state.weights]);

  const filters: RankingsFilters = {
    horizon_days: state.horizon,
    region: state.regions.length > 0 ? state.regions : undefined,
    subregion: state.subregions.length > 0 ? state.subregions : undefined,
    country: state.country,
    weights: Object.keys(state.weights).length > 0 ? state.weights : undefined,
    sort: state.sort !== "score" ? state.sort : undefined,
  };

  return (
    <AppContext.Provider value={{ state, dispatch, filters }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}
