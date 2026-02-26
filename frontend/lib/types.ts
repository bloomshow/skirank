export interface Resort {
  id: string;
  name: string;
  slug: string;
  country: string | null;
  region: string | null;
  subregion: string | null;
  continent: string | null;
  ski_region: string | null;
  latitude: number;
  longitude: number;
  elevation_base_m: number | null;
  elevation_summit_m: number | null;
  aspect: string | null;
  vertical_drop_m: number | null;
  num_runs: number | null;
  website_url: string | null;
}

export interface SubScores {
  base_depth: number | null;
  fresh_snow: number | null;
  temperature: number | null;
  wind: number | null;
  forecast: number | null;
}

export interface SnapshotSummary {
  snow_depth_cm: number | null;
  new_snow_72h_cm: number | null;
  temperature_c: number | null;
  wind_speed_kmh: number | null;
}

export interface MetricsSnapshot {
  base_depth_cm: number | null;
  new_snow_72h_cm: number | null;
  forecast_snow_cm: number | null;
  temperature_c: number | null;
  wind_kmh: number | null;
}

export interface ForecastSnowDay {
  date: string;
  snowfall_cm: number | null;
}

export interface RankingEntry {
  rank: number;
  resort: Resort;
  score: number | null;
  sub_scores: SubScores;
  snapshot: SnapshotSummary;
  stale_data: boolean;
  predicted_snow_cm: number | null;
  forecast_sparkline: ForecastSnowDay[];
  forecast_source?: string | null;
  depth_source?: string | null;
  metrics?: MetricsSnapshot | null;
  position_delta?: number | null;
}

export interface RankingsMeta {
  total: number;
  page: number;
  per_page: number;
  horizon_days: number;
}

export interface RankingsResponse {
  meta: RankingsMeta;
  generated_at: string;
  results: RankingEntry[];
}

export interface ForecastDay {
  forecast_date: string;
  snowfall_cm: number | null;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  wind_speed_max_kmh: number | null;
  precipitation_prob_pct: number | null;
  weather_code: number | null;
  confidence_score: number | null;
}

export interface ResortDetail {
  resort: Resort;
  current_score: number | null;
  sub_scores: SubScores;
  snapshot: SnapshotSummary;
  forecast: ForecastDay[];
}

export interface RegionEntry {
  region: string;
  subregions: string[];
  subregion_counts: Record<string, number>;
  resort_count: number;
}

export interface SkiRegionEntry {
  slug: string;
  label: string;
  resort_count: number;
}

export interface CountryEntry {
  code: string;
  label: string;
  resort_count: number;
  flag: string;
}

export interface ContinentEntry {
  slug: string;
  label: string;
  resort_count: number;
  ski_regions: SkiRegionEntry[];
  countries: CountryEntry[];
}

export interface HierarchyResponse {
  continents: ContinentEntry[];
}

export type HorizonDays = 0 | 3 | 7 | 14;

export interface ClientWeights {
  base_depth: number;   // 0–10
  fresh_snow: number;
  forecast_snow: number;
  temperature: number;
  wind: number;
}

export const DEFAULT_CLIENT_WEIGHTS: ClientWeights = {
  base_depth: 7,
  fresh_snow: 9,
  forecast_snow: 8,
  temperature: 5,
  wind: 3,
};

export interface RankingsFilters {
  horizon_days: HorizonDays;
  region?: string[];
  subregion?: string[];
  continent?: string;
  ski_region?: string[];
  country?: string[];
  min_elevation_m?: number;
  sort?: "score" | "predicted_snow";
}
