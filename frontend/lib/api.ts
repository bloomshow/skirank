import type {
  RankingsResponse,
  RankingsFilters,
  Resort,
  ResortDetail,
  RegionEntry,
  ForecastDay,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

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
  const url = new URL(`${BASE_URL}/rankings`);
  url.searchParams.set("horizon_days", String(horizon_days));
  url.searchParams.set("page", String(page));
  url.searchParams.set("per_page", String(per_page));
  if (sort) url.searchParams.set("sort", sort);
  if (country) url.searchParams.set("country", country);
  if (min_elevation_m !== undefined) url.searchParams.set("min_elevation_m", String(min_elevation_m));
  region?.forEach((r) => url.searchParams.append("region", r));
  subregion?.forEach((s) => url.searchParams.append("subregion", s));
  if (weights) {
    Object.entries(weights).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString(), { next: { revalidate: 3600 } });
  if (!res.ok) throw new Error(`API error ${res.status}: /rankings`);
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
