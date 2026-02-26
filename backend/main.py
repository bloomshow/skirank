import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db
from backend.routers import rankings, resorts, regions, admin
from backend.schemas.responses import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Start daily pipeline scheduler
    try:
        from pipeline.scheduler import run_pipeline
        from pipeline.config import PIPELINE_CRON_SCHEDULE
        cron_parts = PIPELINE_CRON_SCHEDULE.split()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            run_pipeline,
            CronTrigger(
                minute=cron_parts[0],
                hour=cron_parts[1],
                day=cron_parts[2],
                month=cron_parts[3],
                day_of_week=cron_parts[4],
                timezone="UTC",
            ),
            id="daily_pipeline",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Pipeline scheduler started. Schedule: %s", PIPELINE_CRON_SCHEDULE)
    except Exception as exc:
        logger.warning("Could not start pipeline scheduler: %s", exc)
        scheduler = None

    yield

    if scheduler:
        scheduler.shutdown()


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
app.include_router(admin.router, prefix=API_PREFIX)


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
