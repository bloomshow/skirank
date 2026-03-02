"""
AI condition summary generator for SkiRank resort detail pages.

Generates a headline + 4 horizon summaries (today/3d/7d/14d) for each resort
using Claude. Called once daily after the scoring step.

Skips gracefully if ANTHROPIC_API_KEY is not set.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date, datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Max concurrent summarise calls to avoid rate limits
_SEMAPHORE = asyncio.Semaphore(5)

PROMPT_TEMPLATE = """\
You are a ski conditions analyst for SkiRank, writing concise, expert condition summaries for skiers.

Resort: {resort_name} ({country})
Elevation: base {base_m}m / summit {summit_m}m
Aspect: {aspect}
Current base depth: {depth_cm} cm
New snow past 72h: {new_72h} cm
Temperature: {temp_c}°C
Wind: {wind_kmh} km/h
Data quality: {quality}

14-day snowfall forecast (cm per day):
{forecast_lines}

Write 4 summaries (plain prose, no markdown, no bullet points) and a headline:
- headline: One punchy sentence (≤15 words) capturing the key story right now.
- today: Current conditions in 2–3 sentences. What's the snow like? Is it powdery, packed, icy? Any wind or temp concerns?
- next_3d: What to expect in the next 3 days. Focus on snowfall, temperature trend, skiing quality.
- next_7d: Week outlook. Will conditions improve or deteriorate? Key events (storm, warmup, etc.).
- next_14d: Two-week outlook. Big-picture trend — is this a good time to book a trip?

Return ONLY valid JSON with keys: headline, today, next_3d, next_7d, next_14d
Keep each summary to 2–4 sentences. Be specific with numbers where helpful. Write for a skiing audience.\
"""


def _build_forecast_lines(forecast_days: list[dict]) -> str:
    lines = []
    for fc in forecast_days[:14]:
        snow = fc.get("snowfall_cm")
        t_min = fc.get("temperature_min_c")
        t_max = fc.get("temperature_max_c")
        snow_str = f"{snow:.1f}cm snow" if snow else "no snow"
        temp_str = f"{t_min}–{t_max}°C" if t_min is not None and t_max is not None else ""
        lines.append(f"  {fc['forecast_date']}: {snow_str}" + (f", {temp_str}" if temp_str else ""))
    return "\n".join(lines) if lines else "  No forecast data available"


async def generate_resort_summary(
    resort: dict,
    snapshot: dict,
    forecast_days: list[dict],
    quality: str = "good",
) -> Optional[dict]:
    """
    Generate a headline + 4 summaries for a resort.
    Returns dict with keys: headline, today, next_3d, next_7d, next_14d
    Returns None on failure.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed — skipping summaries")
        return None

    prompt = PROMPT_TEMPLATE.format(
        resort_name=resort.get("name", "Unknown"),
        country=resort.get("country", ""),
        base_m=resort.get("elevation_base_m", "?"),
        summit_m=resort.get("elevation_summit_m", "?"),
        aspect=resort.get("aspect") or "unknown",
        depth_cm=snapshot.get("snow_depth_cm") or 0,
        new_72h=snapshot.get("new_snow_72h_cm") or 0,
        temp_c=snapshot.get("temperature_c") or "?",
        wind_kmh=snapshot.get("wind_speed_kmh") or "?",
        quality=quality,
        forecast_lines=_build_forecast_lines(forecast_days),
    )

    async with _SEMAPHORE:
        try:
            client = anthropic.AsyncAnthropic(api_key=api_key)
            message = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
            required = {"headline", "today", "next_3d", "next_7d", "next_14d"}
            if not required.issubset(result.keys()):
                logger.warning("Summary missing keys for %s", resort.get("slug"))
                return None
            return result
        except Exception as exc:
            logger.warning("Summary generation failed for %s: %s", resort.get("slug"), exc)
            return None


async def run_summaries(
    resorts: list[dict],
    weather_results: list,
    today: date,
) -> dict[str, dict]:
    """
    Generate summaries for all resorts. Returns slug → summary dict.
    Skips resorts with no snapshot data.
    """
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.info("ANTHROPIC_API_KEY not set — skipping summary generation")
        return {}

    weather_map = {w.resort_id: w for w in weather_results}
    resort_id_map = {r["id"]: r for r in resorts}

    results: dict[str, dict] = {}

    async def _summarise_one(resort: dict) -> None:
        weather = weather_map.get(resort["id"])
        if not weather:
            return
        snapshot = {
            "snow_depth_cm": weather.snow_depth_cm,
            "new_snow_72h_cm": weather.new_snow_72h_cm,
            "temperature_c": weather.temperature_c,
            "wind_speed_kmh": weather.wind_speed_kmh,
        }
        forecast_days = [
            {
                "forecast_date": str(fc.forecast_date),
                "snowfall_cm": fc.snowfall_cm,
                "temperature_min_c": fc.temperature_min_c,
                "temperature_max_c": fc.temperature_max_c,
            }
            for fc in getattr(weather, "forecasts", [])
        ]
        summary = await generate_resort_summary(
            resort=resort,
            snapshot=snapshot,
            forecast_days=forecast_days,
            quality=getattr(weather, "data_quality", "good") or "good",
        )
        if summary:
            results[resort["id"]] = summary

    await asyncio.gather(*[_summarise_one(r) for r in resorts], return_exceptions=True)
    logger.info("Generated %d/%d summaries", len(results), len(resorts))
    return results
