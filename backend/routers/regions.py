from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models.resort import Resort
from backend.schemas.responses import (
    HierarchyResponse,
    ContinentEntry,
    SkiRegionEntry,
    CountryEntry,
)
from backend.cache import cache_get, cache_set

router = APIRouter(prefix="/regions", tags=["regions"])

CONTINENT_ORDER = [
    "North America", "Europe", "Asia", "South America", "Oceania",
]

COUNTRY_FLAG_MAP = {
    "US": "🇺🇸", "CA": "🇨🇦", "FR": "🇫🇷", "AT": "🇦🇹", "CH": "🇨🇭",
    "IT": "🇮🇹", "JP": "🇯🇵", "AU": "🇦🇺", "NZ": "🇳🇿", "NO": "🇳🇴",
    "SE": "🇸🇪", "DE": "🇩🇪", "SK": "🇸🇰", "SI": "🇸🇮", "ES": "🇪🇸",
    "AR": "🇦🇷", "CL": "🇨🇱", "KR": "🇰🇷", "CN": "🇨🇳", "BG": "🇧🇬",
    "AD": "🇦🇩", "RO": "🇷🇴", "FI": "🇫🇮", "GB": "🇬🇧",
}

COUNTRY_LABEL_MAP = {
    "US": "United States", "CA": "Canada", "FR": "France", "AT": "Austria",
    "CH": "Switzerland", "IT": "Italy", "DE": "Germany", "NO": "Norway",
    "SE": "Sweden", "FI": "Finland", "ES": "Spain", "AD": "Andorra",
    "SK": "Slovakia", "SI": "Slovenia", "BG": "Bulgaria", "RO": "Romania",
    "GB": "Great Britain", "JP": "Japan", "KR": "South Korea",
    "AR": "Argentina", "CL": "Chile", "AU": "Australia", "NZ": "New Zealand",
}


def _slugify(s: str) -> str:
    return s.lower().replace(" ", "-").replace("&", "and").replace("/", "-")


@router.get("", response_model=HierarchyResponse)
async def list_regions(db: AsyncSession = Depends(get_db)):
    cached = await cache_get("regions:hierarchy")
    if cached:
        return cached

    stmt = (
        select(
            Resort.continent,
            Resort.ski_region,
            Resort.country,
            func.count(Resort.id).label("cnt"),
        )
        .where(Resort.continent.is_not(None))
        .group_by(Resort.continent, Resort.ski_region, Resort.country)
        .order_by(Resort.continent, Resort.ski_region, Resort.country)
    )
    rows = (await db.execute(stmt)).all()

    # Build continent → ski_region → count and continent → country → count
    from collections import defaultdict
    continent_data: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "ski_regions": defaultdict(int), "countries": defaultdict(int)}
    )

    for continent, ski_region, country, cnt in rows:
        continent_data[continent]["total"] += cnt
        if ski_region:
            continent_data[continent]["ski_regions"][ski_region] += cnt
        if country:
            continent_data[continent]["countries"][country] += cnt

    continents = []
    for cont_label in CONTINENT_ORDER:
        if cont_label not in continent_data:
            continue
        data = continent_data[cont_label]
        ski_regions = [
            SkiRegionEntry(slug=_slugify(sr), label=sr, resort_count=count)
            for sr, count in sorted(data["ski_regions"].items(), key=lambda x: -x[1])
        ]
        countries = [
            CountryEntry(
                code=code,
                label=COUNTRY_LABEL_MAP.get(code, code),
                resort_count=count,
                flag=COUNTRY_FLAG_MAP.get(code, ""),
            )
            for code, count in sorted(data["countries"].items(), key=lambda x: -x[1])
        ]
        continents.append(
            ContinentEntry(
                slug=_slugify(cont_label),
                label=cont_label,
                resort_count=data["total"],
                ski_regions=ski_regions,
                countries=countries,
            )
        )

    response = HierarchyResponse(continents=continents)
    await cache_set("regions:hierarchy", response.model_dump(), ttl_seconds=86400)
    return response
