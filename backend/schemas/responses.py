from __future__ import annotations
import uuid
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel


class ResortBase(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    country: Optional[str]
    region: Optional[str]
    subregion: Optional[str]
    continent: Optional[str] = None
    ski_region: Optional[str] = None
    latitude: float
    longitude: float
    elevation_base_m: Optional[int]
    elevation_summit_m: Optional[int]
    aspect: Optional[str]
    vertical_drop_m: Optional[int]
    num_runs: Optional[int]
    website_url: Optional[str]

    class Config:
        from_attributes = True


class SubScores(BaseModel):
    base_depth: Optional[float]
    fresh_snow: Optional[float]
    temperature: Optional[float]
    wind: Optional[float]
    forecast: Optional[float]


class SnapshotSummary(BaseModel):
    snow_depth_cm: Optional[float]
    new_snow_72h_cm: Optional[float]
    temperature_c: Optional[float]
    wind_speed_kmh: Optional[float]


class ForecastSnowDay(BaseModel):
    date: str  # "YYYY-MM-DD"
    snowfall_cm: Optional[float]


class MetricsSnapshot(BaseModel):
    base_depth_cm: Optional[float] = None
    new_snow_72h_cm: Optional[float] = None
    forecast_snow_cm: Optional[float] = None
    temperature_c: Optional[float] = None
    wind_kmh: Optional[float] = None


class DataQualityInfo(BaseModel):
    overall: str                          # 'verified'|'good'|'suspect'|'unreliable'|'stale'
    depth_source: Optional[str] = None   # 'synoptic_station'|'open_meteo'
    depth_confidence: str = "unknown"    # 'high'|'medium'|'low'|'unknown'
    flags: List[str] = []
    last_updated: Optional[datetime] = None


class RankingEntry(BaseModel):
    rank: int
    resort: ResortBase
    score: Optional[float]
    sub_scores: SubScores
    snapshot: SnapshotSummary
    stale_data: bool = False
    predicted_snow_cm: Optional[float] = None
    forecast_sparkline: list[ForecastSnowDay] = []
    forecast_source: Optional[str] = None   # 'nws_hrrr' | 'open_meteo'
    depth_source: Optional[str] = None      # 'synoptic_station' | 'open_meteo'
    metrics: Optional[MetricsSnapshot] = None
    position_delta: Optional[int] = None
    data_quality: Optional[DataQualityInfo] = None


class RankingsMeta(BaseModel):
    total: int
    page: int
    per_page: int
    horizon_days: int


class RankingsResponse(BaseModel):
    meta: RankingsMeta
    generated_at: datetime
    results: list[RankingEntry]


class ForecastDay(BaseModel):
    forecast_date: date
    snowfall_cm: Optional[float]
    temperature_max_c: Optional[float]
    temperature_min_c: Optional[float]
    wind_speed_max_kmh: Optional[float]
    precipitation_prob_pct: Optional[int]
    weather_code: Optional[int]
    confidence_score: Optional[float]


class ResortDetail(BaseModel):
    resort: ResortBase
    current_score: Optional[float]
    sub_scores: SubScores
    snapshot: SnapshotSummary
    forecast: list[ForecastDay]

    class Config:
        from_attributes = True


class RegionEntry(BaseModel):
    region: str
    subregions: list[str]
    subregion_counts: dict[str, int] = {}
    resort_count: int


class SkiRegionEntry(BaseModel):
    slug: str
    label: str
    resort_count: int


class CountryEntry(BaseModel):
    code: str
    label: str
    resort_count: int
    flag: str


class ContinentEntry(BaseModel):
    slug: str
    label: str
    resort_count: int
    ski_regions: list[SkiRegionEntry]
    countries: list[CountryEntry]


class HierarchyResponse(BaseModel):
    continents: list[ContinentEntry]


class HealthResponse(BaseModel):
    status: str
    last_pipeline_run: Optional[datetime]
    resorts_count: int


# ---------------------------------------------------------------------------
# v1.6 — Resort detail page types
# ---------------------------------------------------------------------------

class SummaryInfo(BaseModel):
    headline: str
    today: str
    next_3d: str
    next_7d: str
    next_14d: str
    generated_at: datetime


class DepthPoint(BaseModel):
    date: str          # "YYYY-MM-DD"
    depth_cm: Optional[float]


class PowderIntelligence(BaseModel):
    powder_days_14d: int           # forecast days >= 10cm snowfall
    best_window_start: Optional[str]  # "YYYY-MM-DD" of best powder window start
    best_window_end: Optional[str]
    total_new_snow_7d: float
    total_new_snow_14d: float


class RankingsInfo(BaseModel):
    global_rank: Optional[int]
    global_total: int
    continental_rank: Optional[int]
    continental_total: Optional[int]
    regional_rank: Optional[int]
    regional_total: Optional[int]


class NearbyResort(BaseModel):
    slug: str
    name: str
    country: Optional[str]
    ski_region: Optional[str]
    distance_km: float
    score: Optional[float]
    snow_depth_cm: Optional[float]


class ResortDetailFull(BaseModel):
    resort: ResortBase
    current_score: Optional[float]
    sub_scores: SubScores
    snapshot: SnapshotSummary
    data_quality: Optional[DataQualityInfo] = None
    forecast: list[ForecastDay]
    depth_history_30d: list[DepthPoint] = []
    powder_intelligence: PowderIntelligence
    rankings: RankingsInfo
    nearby_resorts: list[NearbyResort] = []
    summary: Optional[SummaryInfo] = None

    class Config:
        from_attributes = True
