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

export interface DataQualityInfo {
  overall: "verified" | "good" | "suspect" | "unreliable" | "stale" | string;
  depth_source: string | null;
  depth_confidence: "high" | "medium" | "low" | "unknown";
  flags: string[];
  last_updated: string | null;
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
  data_quality?: DataQualityInfo | null;
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

// v1.6 — Resort detail page types
export interface SummaryInfo {
  headline: string;
  today: string;
  next_3d: string;
  next_7d: string;
  next_14d: string;
  generated_at: string;
}

export interface DepthPoint {
  date: string;
  depth_cm: number | null;
}

export interface PowderIntelligence {
  powder_days_14d: number;
  best_window_start: string | null;
  best_window_end: string | null;
  total_new_snow_7d: number;
  total_new_snow_14d: number;
}

export interface RankingsInfo {
  global_rank: number | null;
  global_total: number;
  continental_rank: number | null;
  continental_total: number | null;
  regional_rank: number | null;
  regional_total: number | null;
}

export interface NearbyResort {
  slug: string;
  name: string;
  country: string | null;
  ski_region: string | null;
  distance_km: number;
  score: number | null;
  snow_depth_cm: number | null;
}

export interface ResortDetailFull {
  resort: Resort;
  current_score: number | null;
  sub_scores: SubScores;
  snapshot: SnapshotSummary;
  data_quality: DataQualityInfo | null;
  forecast: ForecastDay[];
  depth_history_30d: DepthPoint[];
  powder_intelligence: PowderIntelligence;
  rankings: RankingsInfo;
  nearby_resorts: NearbyResort[];
  summary: SummaryInfo | null;
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
