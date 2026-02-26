"use client";

import React, { createContext, useContext, useReducer, useEffect } from "react";
import type { HorizonDays, RankingsFilters, ClientWeights } from "../lib/types";
import { DEFAULT_CLIENT_WEIGHTS } from "../lib/types";
import type { UnitSystem } from "../lib/units";
import { detectUnitSystem } from "../lib/units";

interface AppState {
  horizon: HorizonDays;
  // Legacy region filters (kept for backward compat)
  regions: string[];
  subregions: string[];
  // Hierarchy filters
  continent: string | null;
  skiRegions: string[];
  countries: string[];
  filterMode: "ski_region" | "country";
  // Ranking preferences (client-side, 0–10)
  clientWeights: ClientWeights;
  // Display
  unitSystem: UnitSystem;
  view: "list" | "map";
  sort: "score" | "predicted_snow";
  hideUncertain: boolean;
}

type Action =
  | { type: "SET_HIDE_UNCERTAIN"; payload: boolean }
  | { type: "SET_HORIZON"; payload: HorizonDays }
  | { type: "TOGGLE_REGION"; payload: string }
  | { type: "CLEAR_REGIONS" }
  | { type: "TOGGLE_SUBREGION"; payload: string }
  | { type: "SET_SUBREGIONS"; payload: string[] }
  | { type: "SET_CONTINENT"; payload: string | null }
  | { type: "TOGGLE_SKI_REGION"; payload: string }
  | { type: "SET_SKI_REGIONS"; payload: string[] }
  | { type: "TOGGLE_COUNTRY"; payload: string }
  | { type: "SET_COUNTRIES"; payload: string[] }
  | { type: "SET_FILTER_MODE"; payload: "ski_region" | "country" }
  | { type: "CLEAR_HIERARCHY" }
  | { type: "SET_CLIENT_WEIGHT"; key: keyof ClientWeights; value: number }
  | { type: "RESET_CLIENT_WEIGHTS" }
  | { type: "SET_UNITS"; payload: UnitSystem }
  | { type: "SET_VIEW"; payload: "list" | "map" }
  | { type: "SET_SORT"; payload: "score" | "predicted_snow" };

const DEFAULT_STATE: AppState = {
  horizon: 0,
  regions: [],
  subregions: [],
  continent: null,
  skiRegions: [],
  countries: [],
  filterMode: "ski_region",
  clientWeights: DEFAULT_CLIENT_WEIGHTS,
  unitSystem: "metric", // overridden on mount by detectUnitSystem()
  view: "list",
  sort: "score",
  hideUncertain: false,
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
    case "SET_SUBREGIONS":
      return { ...state, subregions: action.payload };
    case "SET_CONTINENT":
      return { ...state, continent: action.payload, skiRegions: [], countries: [] };
    case "TOGGLE_SKI_REGION": {
      const already = state.skiRegions.includes(action.payload);
      const skiRegions = already
        ? state.skiRegions.filter((s) => s !== action.payload)
        : [...state.skiRegions, action.payload];
      return { ...state, skiRegions };
    }
    case "SET_SKI_REGIONS":
      return { ...state, skiRegions: action.payload };
    case "TOGGLE_COUNTRY": {
      const already = state.countries.includes(action.payload);
      const countries = already
        ? state.countries.filter((c) => c !== action.payload)
        : [...state.countries, action.payload];
      return { ...state, countries };
    }
    case "SET_COUNTRIES":
      return { ...state, countries: action.payload };
    case "SET_FILTER_MODE":
      return { ...state, filterMode: action.payload, skiRegions: [], countries: [] };
    case "CLEAR_HIERARCHY":
      return { ...state, continent: null, skiRegions: [], countries: [] };
    case "SET_CLIENT_WEIGHT":
      return {
        ...state,
        clientWeights: { ...state.clientWeights, [action.key]: action.value },
      };
    case "RESET_CLIENT_WEIGHTS":
      return { ...state, clientWeights: DEFAULT_CLIENT_WEIGHTS };
    case "SET_UNITS":
      return { ...state, unitSystem: action.payload };
    case "SET_VIEW":
      return { ...state, view: action.payload };
    case "SET_SORT":
      return { ...state, sort: action.payload };
    case "SET_HIDE_UNCERTAIN":
      return { ...state, hideUncertain: action.payload };
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

const STORAGE_KEY = "skirank_prefs_v14";

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

  // Auto-detect unit system on first mount (only if not already persisted)
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      dispatch({ type: "SET_UNITS", payload: detectUnitSystem() });
    }
  }, []);

  // Persist preferences (weights + units + horizon)
  useEffect(() => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          horizon: state.horizon,
          clientWeights: state.clientWeights,
          unitSystem: state.unitSystem,
        })
      );
    } catch {}
  }, [state.horizon, state.clientWeights, state.unitSystem]);

  const filters: RankingsFilters = {
    horizon_days: state.horizon,
    continent: state.continent ?? undefined,
    ski_region: state.skiRegions.length > 0 ? state.skiRegions : undefined,
    country: state.countries.length > 0 ? state.countries : undefined,
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
