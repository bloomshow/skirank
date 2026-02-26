import type {
  RankingsResponse,
  RankingsFilters,
  Resort,
  ResortDetail,
  RegionEntry,
  ForecastDay,
} from "./types";

const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
// Ensure the base URL always includes /api/v1 regardless of how the env var is set
const BASE_URL = rawBase.endsWith("/api/v1")
  ? rawBase
  : rawBase.replace(/\/$/, "") + "/api/v1";

async function apiFetch<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.set(k, String(v));
      }
    });
  }
  const res = await fetch(url.toString(), {
    next: { revalidate: 3600 },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${url.pathname}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchRankings(
  filters: RankingsFilters,
  page = 1,
  per_page = 50
): Promise<RankingsResponse> {
  const { horizon_days, region, subregion, country, min_elevation_m, weights, sort } = filters;
  const params: Record<string, string | number | undefined> = {
    horizon_days,
    page,
    per_page,
    ...(sort && { sort }),
    ...(country && { country }),
    ...(min_elevation_m !== undefined && { min_elevation_m }),
    ...weights,
  };
  const url = new URL(`${BASE_URL}/rankings`);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined) url.searchParams.set(k, String(v));
  });
  region?.forEach((r) => url.searchParams.append("region", r));
  subregion?.forEach((s) => url.searchParams.append("subregion", s));
  const res = await fetch(url.toString(), { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`API error ${res.status}: ${url.pathname}`);
  return res.json() as Promise<RankingsResponse>;
}

export async function fetchResorts(params?: {
  region?: string;
  country?: string;
  search?: string;
}): Promise<Resort[]> {
  return apiFetch<Resort[]>("/resorts", params);
}

export async function fetchResort(slug: string): Promise<ResortDetail> {
  return apiFetch<ResortDetail>(`/resorts/${slug}`);
}

export async function fetchResortForecast(slug: string): Promise<ForecastDay[]> {
  return apiFetch<ForecastDay[]>(`/resorts/${slug}/forecast`);
}

export async function fetchRegions(): Promise<RegionEntry[]> {
  return apiFetch<RegionEntry[]>("/regions");
}

export async function fetchRankingsMap(horizon_days = 0): Promise<
  { slug: string; name: string; latitude: number; longitude: number; region: string; score: number | null }[]
> {
  return apiFetch("/rankings/map", { horizon_days });
}
