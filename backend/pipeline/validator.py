"""
Data quality validation for SkiRank pipeline.

Runs after every fetch and before scores are written. Catches implausible
readings, assigns a DataQuality rating, and records flags for debugging.
"""
from __future__ import annotations

import logging
from datetime import date
from enum import Enum

logger = logging.getLogger(__name__)

# Elevation-band depth baseline (Northern Hemisphere, ski season months only).
# Used as fallback when no historical per-resort average is available.
ELEVATION_DEPTH_BASELINE: dict[tuple[int, int], dict[int, float]] = {
    (0,    1500): {12: 40,  1: 60,  2: 70,  3: 50,  4: 20},
    (1500, 2000): {12: 80,  1: 120, 2: 140, 3: 110, 4: 60},
    (2000, 2500): {12: 120, 1: 180, 2: 200, 3: 170, 4: 100},
    (2500, 3000): {12: 160, 1: 230, 2: 260, 3: 220, 4: 140},
    (3000, 9999): {12: 200, 1: 280, 2: 310, 3: 270, 4: 180},
}


class DataQuality(str, Enum):
    VERIFIED   = "verified"    # Station data + all rules pass
    GOOD       = "good"        # Model data + all rules pass
    SUSPECT    = "suspect"     # One rule flagged
    UNRELIABLE = "unreliable"  # Two or more rules flagged
    STALE      = "stale"       # Data not updated in 48+ hours (set by API layer)


# ---------------------------------------------------------------------------
# Validation rules — each returns (is_valid, reason_or_None)
# ---------------------------------------------------------------------------

def validate_depth_seasonal(
    latitude: float | None,
    elevation_m: int | None,
    depth_cm: float | None,
    fetch_date: date,
) -> tuple[bool, str | None]:
    """Flag depth that is implausible for the current month and elevation."""
    if depth_cm is None or depth_cm <= 0:
        return True, None

    month = fetch_date.month
    is_northern = (latitude or 0) > 0
    off_season: list[int] = (
        list(range(5, 11)) if is_northern
        else list(range(11, 13)) + list(range(1, 5))
    )

    if month in off_season and depth_cm > 50:
        return False, "depth_implausible_offseason"

    if elevation_m is not None:
        max_depth_map = [(1500, 250), (2000, 350), (2500, 450), (3000, 550), (9999, 700)]
        for threshold, max_cm in max_depth_map:
            if elevation_m < threshold:
                if depth_cm > max_cm:
                    return False, f"depth_exceeds_elevation_maximum_{max_cm}cm"
                break

    return True, None


def validate_depth_change(
    previous_depth_cm: float | None,
    current_depth_cm: float | None,
    snowfall_24h_cm: float | None,
) -> tuple[bool, str | None]:
    """Flag depth changes not explainable by snowfall or natural settling."""
    if previous_depth_cm is None or current_depth_cm is None:
        return True, None

    change = current_depth_cm - previous_depth_cm
    snowfall = snowfall_24h_cm or 0.0

    if change > 30 and snowfall < change * 0.5:
        return False, "depth_gain_unexplained_by_snowfall"
    if change < -60:
        return False, "depth_loss_implausibly_large"

    return True, None


def validate_cross_source(
    station_depth_cm: float | None,
    openmeteo_depth_cm: float | None,
) -> tuple[bool, str | None]:
    """Flag when station and model disagree by more than 3×."""
    if station_depth_cm is None or openmeteo_depth_cm is None:
        return True, None
    if station_depth_cm == 0 or openmeteo_depth_cm == 0:
        return True, None

    ratio = max(station_depth_cm, openmeteo_depth_cm) / min(station_depth_cm, openmeteo_depth_cm)
    if ratio > 3.0:
        return False, f"cross_source_variance_ratio_{ratio:.1f}x"

    return True, None


def validate_temp_depth_consistency(
    depth_cm: float | None,
    avg_temp_c: float | None,
) -> tuple[bool, str | None]:
    """Flag high base depth paired with sustained above-freezing temperatures."""
    if depth_cm is None or avg_temp_c is None:
        return True, None
    if avg_temp_c > 3 and depth_cm > 150:
        return False, "high_depth_inconsistent_with_warm_temps"
    return True, None


# ---------------------------------------------------------------------------
# Quality scorer
# ---------------------------------------------------------------------------

def score_data_quality(
    validation_results: list[tuple[bool, str | None]],
    depth_source: str,
) -> tuple[DataQuality, list[str]]:
    """Aggregate rule results into a quality rating and list of flags."""
    flags = [reason for ok, reason in validation_results if not ok and reason]
    n = len(flags)
    if n == 0:
        quality = DataQuality.VERIFIED if depth_source == "synoptic_station" else DataQuality.GOOD
    elif n == 1:
        quality = DataQuality.SUSPECT
    else:
        quality = DataQuality.UNRELIABLE
    return quality, flags


# ---------------------------------------------------------------------------
# Elevation-based depth baseline (fallback for historical average)
# ---------------------------------------------------------------------------

def get_elevation_baseline(elevation_m: int | None, month: int) -> float | None:
    """Return an expected base depth from the elevation/month lookup table."""
    if elevation_m is None:
        return None
    # Off season — no meaningful estimate
    if month in range(5, 11):
        return 0.0
    for (min_e, max_e), monthly in ELEVATION_DEPTH_BASELINE.items():
        if min_e <= elevation_m < max_e:
            return float(monthly.get(month, 0))
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_validation(
    resort: dict,
    depth_cm: float | None,
    openmeteo_depth_cm: float | None,
    previous_depth_cm: float | None,
    snowfall_24h_cm: float | None,
    avg_temp_c: float | None,
    depth_source: str,
    fetch_date: date,
) -> tuple[DataQuality, list[str]]:
    """
    Run all applicable validation rules and return (quality, flags).

    Rules 1-5 from the spec, using available data. Cross-source variance
    (Rule 3) only fires when station data is present (depth_source == 'synoptic_station').
    """
    results = [
        validate_depth_seasonal(
            resort.get("latitude"),
            resort.get("elevation_summit_m"),
            depth_cm,
            fetch_date,
        ),
        validate_depth_change(previous_depth_cm, depth_cm, snowfall_24h_cm),
        validate_cross_source(
            depth_cm if depth_source == "synoptic_station" else None,
            openmeteo_depth_cm if depth_source == "synoptic_station" else None,
        ),
        validate_temp_depth_consistency(depth_cm, avg_temp_c),
    ]

    quality, flags = score_data_quality(results, depth_source)
    if flags:
        logger.info(
            "Quality flags for %s: quality=%s flags=%s",
            resort.get("slug", resort.get("id")),
            quality.value,
            flags,
        )
    return quality, flags
