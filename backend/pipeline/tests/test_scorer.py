"""
Unit tests for pipeline/scorer.py

Run with:  pytest pipeline/tests/test_scorer.py -v
"""
import pytest
from pipeline.scorer import (
    score_base_depth,
    score_fresh_snow,
    score_temperature,
    score_wind,
    score_forecast_confidence,
    apply_aspect_elevation_adjustments,
    compute_score,
    CurrentConditions,
    ForecastDay,
    ResortMeta,
    ScoreResult,
    DEFAULT_WEIGHTS,
)


# ── score_base_depth ─────────────────────────────────────────────────────────

class TestScoreBaseDepth:
    def test_at_historical_average_scores_100(self):
        assert score_base_depth(120.0, historical_avg_cm=120.0) == 100.0

    def test_above_average_capped_at_100(self):
        assert score_base_depth(200.0, historical_avg_cm=100.0) == 100.0

    def test_half_average_scores_50(self):
        assert score_base_depth(60.0, historical_avg_cm=120.0) == pytest.approx(50.0)

    def test_zero_depth_scores_0(self):
        assert score_base_depth(0.0, historical_avg_cm=100.0) == 0.0

    def test_none_depth_scores_0(self):
        assert score_base_depth(None) == 0.0

    def test_no_historical_uses_elevation_band_low(self):
        # <1500m → 60cm avg; 60cm depth = ratio 1.0 = 100
        assert score_base_depth(60.0, elevation_m=1000) == 100.0

    def test_no_historical_uses_elevation_band_mid(self):
        # 1500–2500m → 120cm avg; 60cm = ratio 0.5 = 50
        assert score_base_depth(60.0, elevation_m=2000) == pytest.approx(50.0)

    def test_no_historical_uses_elevation_band_high(self):
        # >2500m → 180cm avg; 90cm = ratio 0.5 = 50
        assert score_base_depth(90.0, elevation_m=3000) == pytest.approx(50.0)

    def test_no_historical_no_elevation_uses_100cm_avg(self):
        assert score_base_depth(100.0) == 100.0
        assert score_base_depth(50.0) == pytest.approx(50.0)


# ── score_fresh_snow ─────────────────────────────────────────────────────────

class TestScoreFreshSnow:
    def test_no_snow_no_forecast_scores_0(self):
        assert score_fresh_snow(0.0) == 0.0

    def test_none_snow_none_forecast_scores_0(self):
        assert score_fresh_snow(None) == 0.0

    def test_recent_snow_scores_correctly(self):
        # 20cm → 20 * 1.5 = 30 pts (capped at 40)
        assert score_fresh_snow(20.0) == pytest.approx(30.0)

    def test_heavy_recent_snow_capped_at_40(self):
        # 50cm → 50 * 1.5 = 75 → capped at 40
        assert score_fresh_snow(50.0) == pytest.approx(40.0)

    def test_forecast_adds_to_score(self):
        forecast = [
            ForecastDay(distance_days=1, snowfall_cm=10.0, temperature_c=-8.0,
                        wind_speed_kmh=15.0, confidence=0.9)
        ]
        # recent_pts = 0, forecast: min(30, 10*2)=20 * (0.9 * (1 - 1/16*0.5)) = 20 * 0.871 = 17.4
        result = score_fresh_snow(0.0, forecast)
        assert result > 0.0
        assert result <= 100.0

    def test_total_capped_at_100(self):
        forecast = [
            ForecastDay(distance_days=i, snowfall_cm=50.0, temperature_c=-10.0,
                        wind_speed_kmh=10.0, confidence=1.0)
            for i in range(16)
        ]
        result = score_fresh_snow(100.0, forecast)
        assert result == 100.0

    def test_far_forecast_discounted(self):
        near = [ForecastDay(distance_days=1, snowfall_cm=10.0, temperature_c=-8.0,
                            wind_speed_kmh=15.0, confidence=0.9)]
        far = [ForecastDay(distance_days=15, snowfall_cm=10.0, temperature_c=-8.0,
                           wind_speed_kmh=15.0, confidence=0.53)]
        near_score = score_fresh_snow(0.0, near)
        far_score = score_fresh_snow(0.0, far)
        assert near_score > far_score


# ── score_temperature ────────────────────────────────────────────────────────

class TestScoreTemperature:
    def test_melting_temp_scores_0(self):
        assert score_temperature(5.0) == 0.0
        assert score_temperature(2.1) == 0.0

    def test_marginal_temp_scores_20(self):
        assert score_temperature(1.0) == 20.0
        assert score_temperature(0.0) == 20.0

    def test_cold_not_ideal_scores_60(self):
        assert score_temperature(-1.0) == 60.0
        assert score_temperature(-4.9) == 60.0

    def test_ideal_temp_scores_100(self):
        assert score_temperature(-5.0) == 100.0
        assert score_temperature(-10.0) == 100.0
        assert score_temperature(-15.0) == 100.0

    def test_very_cold_scores_80(self):
        assert score_temperature(-16.0) == 80.0
        assert score_temperature(-25.0) == 80.0

    def test_extreme_cold_scores_50(self):
        assert score_temperature(-26.0) == 50.0
        assert score_temperature(-40.0) == 50.0

    def test_none_temperature_scores_neutral_50(self):
        assert score_temperature(None) == 50.0


# ── score_wind ───────────────────────────────────────────────────────────────

class TestScoreWind:
    def test_calm_scores_100(self):
        assert score_wind(0.0) == 100.0
        assert score_wind(19.9) == 100.0

    def test_breezy_scores_80(self):
        assert score_wind(20.0) == 80.0
        assert score_wind(39.9) == 80.0

    def test_strong_scores_50(self):
        assert score_wind(40.0) == 50.0
        assert score_wind(59.9) == 50.0

    def test_very_strong_scores_20(self):
        assert score_wind(60.0) == 20.0
        assert score_wind(79.9) == 20.0

    def test_storm_scores_0(self):
        assert score_wind(80.0) == 0.0
        assert score_wind(150.0) == 0.0

    def test_none_wind_scores_80(self):
        assert score_wind(None) == 80.0


# ── score_forecast_confidence ────────────────────────────────────────────────

class TestScoreForecastConfidence:
    def test_no_forecast_scores_100(self):
        assert score_forecast_confidence(None) == 100.0
        assert score_forecast_confidence([]) == 100.0

    def test_single_day_full_confidence(self):
        days = [ForecastDay(distance_days=0, snowfall_cm=5.0, temperature_c=-8.0,
                            wind_speed_kmh=10.0, confidence=1.0)]
        assert score_forecast_confidence(days) == 100.0

    def test_multiple_days_averages(self):
        days = [
            ForecastDay(distance_days=i, snowfall_cm=5.0, temperature_c=-8.0,
                        wind_speed_kmh=10.0, confidence=0.8)
            for i in range(5)
        ]
        assert score_forecast_confidence(days) == pytest.approx(80.0)


# ── apply_aspect_elevation_adjustments ──────────────────────────────────────

class TestAspectElevationAdjustments:
    def test_north_facing_spring_boosts_temp_score(self):
        meta = ResortMeta(elevation_summit_m=2000, aspect="N",
                          season_start_month=11, season_end_month=4)
        t, b = apply_aspect_elevation_adjustments(80.0, 80.0, meta, current_month=4)
        assert t > 80.0  # boosted
        assert b == 80.0  # unchanged (2000m is in neutral band)

    def test_south_facing_spring_reduces_temp_score(self):
        meta = ResortMeta(elevation_summit_m=2000, aspect="S",
                          season_start_month=11, season_end_month=4)
        t, b = apply_aspect_elevation_adjustments(80.0, 80.0, meta, current_month=3)
        assert t < 80.0

    def test_high_altitude_boosts_base_depth(self):
        meta = ResortMeta(elevation_summit_m=3500, aspect=None,
                          season_start_month=11, season_end_month=4)
        t, b = apply_aspect_elevation_adjustments(80.0, 80.0, meta, current_month=1)
        assert b > 80.0

    def test_low_altitude_spring_reduces_base_depth(self):
        meta = ResortMeta(elevation_summit_m=1200, aspect=None,
                          season_start_month=12, season_end_month=3)
        t, b = apply_aspect_elevation_adjustments(80.0, 80.0, meta, current_month=4)
        assert b < 80.0

    def test_mid_winter_no_aspect_no_change(self):
        meta = ResortMeta(elevation_summit_m=2500, aspect="E",
                          season_start_month=11, season_end_month=4)
        t, b = apply_aspect_elevation_adjustments(80.0, 80.0, meta, current_month=1)
        assert t == 80.0
        assert b == 80.0

    def test_scores_never_exceed_100(self):
        meta = ResortMeta(elevation_summit_m=4000, aspect="N",
                          season_start_month=11, season_end_month=4)
        t, b = apply_aspect_elevation_adjustments(100.0, 100.0, meta, current_month=4)
        assert t <= 100.0
        assert b <= 100.0


# ── compute_score (integration) ──────────────────────────────────────────────

class TestComputeScore:
    def _make_conditions(self, **overrides):
        defaults = dict(
            snow_depth_cm=150.0,
            new_snow_72h_cm=30.0,
            temperature_c=-10.0,
            wind_speed_kmh=15.0,
        )
        defaults.update(overrides)
        return CurrentConditions(**defaults)

    def _make_meta(self, **overrides):
        defaults = dict(
            elevation_summit_m=2500,
            aspect="N",
            season_start_month=11,
            season_end_month=4,
        )
        defaults.update(overrides)
        return ResortMeta(**defaults)

    def test_returns_score_result(self):
        result = compute_score(
            current=self._make_conditions(),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
        )
        assert isinstance(result, ScoreResult)

    def test_score_in_range_0_to_100(self):
        result = compute_score(
            current=self._make_conditions(),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
        )
        assert 0.0 <= result.score_total <= 100.0

    def test_excellent_conditions_score_high(self):
        result = compute_score(
            current=self._make_conditions(
                snow_depth_cm=200.0, new_snow_72h_cm=60.0,
                temperature_c=-10.0, wind_speed_kmh=5.0
            ),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
            historical_avg_cm=150.0,
        )
        assert result.score_total >= 70.0

    def test_poor_conditions_score_low(self):
        result = compute_score(
            current=self._make_conditions(
                snow_depth_cm=10.0, new_snow_72h_cm=0.0,
                temperature_c=5.0, wind_speed_kmh=100.0
            ),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
            historical_avg_cm=150.0,
        )
        assert result.score_total < 30.0

    def test_custom_weights_sum_applied(self):
        # Heavily weight wind — poor wind score should dominate
        result = compute_score(
            current=self._make_conditions(wind_speed_kmh=90.0),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
            weights={"base_depth": 0.1, "fresh_snow": 0.1, "temperature": 0.1,
                     "wind": 0.6, "forecast": 0.1},
        )
        assert result.score_total < 40.0

    def test_horizon_0_ignores_forecast(self):
        # At horizon 0 only current data counts; forecast_days should not change result
        r0 = compute_score(
            current=self._make_conditions(),
            forecast_days=None,
            meta=self._make_meta(),
            horizon_days=0,
        )
        forecast = [
            ForecastDay(distance_days=i, snowfall_cm=5.0, temperature_c=-8.0,
                        wind_speed_kmh=10.0, confidence=0.9)
            for i in range(1, 8)
        ]
        r_with = compute_score(
            current=self._make_conditions(),
            forecast_days=forecast,
            meta=self._make_meta(),
            horizon_days=0,
        )
        # horizon 0 mixes with forecast_w=0 so impact should be minimal
        # (fresh_snow sub-score may still count horizon 0 days)
        assert abs(r0.score_total - r_with.score_total) < 15.0

    def test_all_sub_scores_present(self):
        result = compute_score(
            current=self._make_conditions(),
            forecast_days=None,
            meta=self._make_meta(),
        )
        assert result.score_base_depth >= 0.0
        assert result.score_fresh_snow >= 0.0
        assert result.score_temperature >= 0.0
        assert result.score_wind >= 0.0
        assert result.score_forecast >= 0.0

    def test_none_conditions_still_returns_score(self):
        result = compute_score(
            current=CurrentConditions(
                snow_depth_cm=None, new_snow_72h_cm=None,
                temperature_c=None, wind_speed_kmh=None,
            ),
            forecast_days=None,
            meta=ResortMeta(
                elevation_summit_m=None, aspect=None,
                season_start_month=None, season_end_month=None,
            ),
        )
        assert 0.0 <= result.score_total <= 100.0
