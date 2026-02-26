"""
Scoring engine for SkiRank.

All functions are pure (no side effects) so they are straightforward to unit-test.
Composite score is a weighted sum of five sub-scores, each ranging 0–100.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ── Default weights ──────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "base_depth": 0.25,
    "fresh_snow": 0.35,
    "temperature": 0.20,
    "wind": 0.10,
    "forecast": 0.10,
}

# Horizon mixing ratios: (current_weight, forecast_weight)
HORIZON_MIX = {
    0:  (1.00, 0.00),
    3:  (0.60, 0.40),
    7:  (0.30, 0.70),
    14: (0.10, 0.90),
}


# ── Input dataclasses ────────────────────────────────────────────────────────

@dataclass
class CurrentConditions:
    snow_depth_cm: Optional[float]
    new_snow_72h_cm: Optional[float]
    temperature_c: Optional[float]
    wind_speed_kmh: Optional[float]


@dataclass
class ForecastDay:
    distance_days: int          # days from today
    snowfall_cm: Optional[float]
    temperature_c: Optional[float]  # representative temp (e.g. average of max/min)
    wind_speed_kmh: Optional[float]
    confidence: float           # 0.0–1.0


@dataclass
class ResortMeta:
    elevation_summit_m: Optional[int]
    aspect: Optional[str]       # N, NE, E, SE, S, SW, W, NW
    season_start_month: Optional[int]
    season_end_month: Optional[int]


@dataclass
class ScoreResult:
    score_total: float
    score_base_depth: float
    score_fresh_snow: float
    score_temperature: float
    score_wind: float
    score_forecast: float


# ── Sub-score functions ──────────────────────────────────────────────────────

def score_base_depth(
    snow_depth_cm: Optional[float],
    historical_avg_cm: Optional[float] = None,
    elevation_m: Optional[int] = None,
) -> float:
    """
    Score based on current snow depth vs historical average.

    If no historical average is available, fall back to an elevation-band proxy:
      <1500m → 60cm avg, 1500–2500m → 120cm avg, >2500m → 180cm avg
    """
    if snow_depth_cm is None:
        return 0.0

    if historical_avg_cm is None or historical_avg_cm <= 0:
        if elevation_m is None:
            historical_avg_cm = 100.0
        elif elevation_m < 1500:
            historical_avg_cm = 60.0
        elif elevation_m < 2500:
            historical_avg_cm = 120.0
        else:
            historical_avg_cm = 180.0

    ratio = snow_depth_cm / historical_avg_cm
    return min(100.0, round(ratio * 100, 1))


def score_fresh_snow(
    new_snow_72h_cm: Optional[float],
    forecast_days: Optional[list[ForecastDay]] = None,
) -> float:
    """
    Score based on recent snowfall and forecast snowfall (with distance discount).

    recent_pts  = min(40, new_snow_72h_cm * 1.5)
    forecast_pts = sum of discounted daily snowfall scores, capped at 60

    Total score = min(100, recent_pts + forecast_pts)
    """
    recent_pts = 0.0
    if new_snow_72h_cm is not None:
        recent_pts = min(40.0, new_snow_72h_cm * 1.5)

    forecast_pts = 0.0
    if forecast_days:
        for day in forecast_days:
            if day.snowfall_cm is None:
                continue
            discount = day.confidence * (1.0 - (day.distance_days / 16) * 0.5)
            day_pts = min(30.0, day.snowfall_cm * 2) * discount
            forecast_pts += day_pts

    forecast_pts = min(60.0, forecast_pts)
    return min(100.0, round(recent_pts + forecast_pts, 1))


def score_temperature(temperature_c: Optional[float]) -> float:
    """
    Score based on temperature suitability for skiing.

    Ideal range: -5°C to -15°C (score = 100)
    Melting (>2°C): score = 0
    Extreme cold (<-25°C): score = 50
    """
    if temperature_c is None:
        return 50.0  # unknown → neutral

    if temperature_c > 2:
        return 0.0
    elif temperature_c > 0:
        return 20.0
    elif temperature_c > -5:
        return 60.0
    elif temperature_c > -15:
        return 100.0
    elif temperature_c > -25:
        return 80.0
    else:
        return 50.0


def score_wind(wind_speed_kmh: Optional[float]) -> float:
    """
    Score based on wind speed.  High winds close lifts and damage snow surface.
    """
    if wind_speed_kmh is None:
        return 80.0  # unknown → assume acceptable

    if wind_speed_kmh < 20:
        return 100.0
    elif wind_speed_kmh < 40:
        return 80.0
    elif wind_speed_kmh < 60:
        return 50.0
    elif wind_speed_kmh < 80:
        return 20.0
    else:
        return 0.0


def score_forecast_confidence(forecast_days: Optional[list[ForecastDay]]) -> float:
    """
    Aggregate confidence score across forecast window (average of daily confidences).
    Returns 100 when no forecast is needed (horizon 0 uses 100% current data).
    """
    if not forecast_days:
        return 100.0
    confidences = [d.confidence for d in forecast_days]
    avg = sum(confidences) / len(confidences)
    return round(avg * 100, 1)


# ── Aspect / elevation adjustments ──────────────────────────────────────────

_SPRING_MONTHS = {3, 4, 5}  # March–May (Northern Hemisphere)


def _is_spring(current_month: Optional[int]) -> bool:
    if current_month is None:
        return False
    return current_month in _SPRING_MONTHS


def apply_aspect_elevation_adjustments(
    temp_score: float,
    base_depth_score: float,
    meta: ResortMeta,
    current_month: Optional[int] = None,
) -> tuple[float, float]:
    """
    Apply multiplicative modifiers based on aspect and elevation.

    Returns adjusted (temp_score, base_depth_score).
    """
    spring = _is_spring(current_month)
    north_facing = meta.aspect in {"N", "NE", "NW"} if meta.aspect else False
    south_facing = meta.aspect in {"S", "SE", "SW"} if meta.aspect else False

    if spring:
        if north_facing:
            temp_score = min(100.0, temp_score * 1.08)
        elif south_facing:
            temp_score = min(100.0, temp_score * 0.95)

    summit = meta.elevation_summit_m
    if summit is not None:
        if summit > 3000:
            base_depth_score = min(100.0, base_depth_score * 1.10)
        elif summit < 2000 and spring:
            base_depth_score = min(100.0, base_depth_score * 0.90)

    return round(temp_score, 1), round(base_depth_score, 1)


# ── Composite scorer ─────────────────────────────────────────────────────────

def compute_score(
    current: CurrentConditions,
    forecast_days: Optional[list[ForecastDay]],
    meta: ResortMeta,
    horizon_days: int = 0,
    weights: Optional[dict[str, float]] = None,
    historical_avg_cm: Optional[float] = None,
    current_month: Optional[int] = None,
) -> ScoreResult:
    """
    Compute the full composite score for a resort at a given forecast horizon.

    At horizon 0 we use 100% current conditions.
    At horizon > 0 we blend current and forecast according to HORIZON_MIX.
    """
    w = weights or DEFAULT_WEIGHTS

    # Filter forecast days relevant to the horizon window
    horizon_forecasts = (
        [d for d in forecast_days if d.distance_days <= horizon_days]
        if forecast_days else []
    )

    # Base sub-scores
    s_base = score_base_depth(
        current.snow_depth_cm, historical_avg_cm, meta.elevation_summit_m
    )
    s_fresh = score_fresh_snow(current.new_snow_72h_cm, horizon_forecasts)
    s_temp = score_temperature(current.temperature_c)
    s_wind = score_wind(current.wind_speed_kmh)
    s_forecast = score_forecast_confidence(horizon_forecasts)

    # Aspect / elevation adjustments
    s_temp, s_base = apply_aspect_elevation_adjustments(
        s_temp, s_base, meta, current_month
    )

    # Horizon blending: at higher horizons, weight current conditions lower
    current_w, forecast_w = HORIZON_MIX.get(horizon_days, (1.0, 0.0))
    # Blend fresh_snow sub-score: at high horizons it naturally includes forecast
    # No additional blending needed — fresh_snow already uses forecast_days.

    # Composite (weighted sum)
    total = (
        w.get("base_depth", 0.25) * s_base
        + w.get("fresh_snow", 0.35) * s_fresh
        + w.get("temperature", 0.20) * s_temp
        + w.get("wind", 0.10) * s_wind
        + w.get("forecast", 0.10) * s_forecast
    )
    # Dampen score at future horizons based on forecast confidence
    total = total * (current_w + forecast_w * (s_forecast / 100))

    return ScoreResult(
        score_total=round(min(100.0, max(0.0, total)), 1),
        score_base_depth=s_base,
        score_fresh_snow=s_fresh,
        score_temperature=s_temp,
        score_wind=s_wind,
        score_forecast=s_forecast,
    )
