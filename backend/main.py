import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.routers import rankings, resorts, regions
from backend.schemas.responses import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="SkiRank API",
    description="Daily-updated global ski resort ranking platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(rankings.router, prefix=API_PREFIX)
app.include_router(resorts.router, prefix=API_PREFIX)
app.include_router(regions.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["system"])
async def health():
    from backend.db import AsyncSessionLocal
    from backend.models.resort import Resort
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as db:
        count_result = await db.execute(select(func.count(Resort.id)))
        resort_count = count_result.scalar_one()

    return HealthResponse(
        status="ok",
        last_pipeline_run=None,  # Updated when pipeline writes to DB
        resorts_count=resort_count,
    )
