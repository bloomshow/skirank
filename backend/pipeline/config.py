import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://skirank:skirank_dev@localhost:5432/skirank"
)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

OPEN_METEO_BASE_URL: str = os.environ.get(
    "OPEN_METEO_BASE_URL", "https://api.open-meteo.com"
)
OPEN_METEO_FORECAST_URL: str = f"{OPEN_METEO_BASE_URL}/v1/forecast"

SNOTEL_API_URL: str = os.environ.get(
    "SNOTEL_API_URL", "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1"
)

SYNOPTIC_API_URL: str = os.environ.get(
    "SYNOPTIC_API_URL", "https://api.synopticdata.com/v2"
)
SYNOPTIC_API_TOKEN: str = os.environ.get("SYNOPTIC_API_TOKEN", "")

PIPELINE_BATCH_SIZE: int = 50
PIPELINE_CRON_SCHEDULE: str = os.environ.get("PIPELINE_CRON_SCHEDULE", "0 6 * * *")

SENDGRID_API_KEY: str = os.environ.get("SENDGRID_API_KEY", "")
ALERT_EMAIL: str = os.environ.get("ALERT_EMAIL", "")
ALERT_FAILURE_THRESHOLD: float = 0.05  # 5%

LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

# Retry settings
HTTP_RETRIES: int = 3
HTTP_BACKOFF_FACTOR: float = 1.0  # 1s, 2s, 4s
HTTP_TIMEOUT: float = 30.0

# Horizon days for scoring
SCORE_HORIZONS: list[int] = [0, 3, 7, 14]
