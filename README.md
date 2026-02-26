# SkiRank

Daily-updated global ski resort ranking platform based on real snow and weather conditions.

## Quick Start

### 1. Prerequisites
- Docker + Docker Compose
- Python 3.11
- Node.js 20+

### 2. Start local infrastructure

```bash
cp .env.example .env
docker-compose up -d postgres redis
```

### 3. Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# API available at http://localhost:8000/api/v1
```

### 4. Seed resort database

```bash
# From repo root
python -m pipeline.seed_resorts data/resorts_seed.csv
```

### 5. Run the pipeline manually

```bash
python -c "import asyncio; from pipeline.scheduler import run_pipeline; asyncio.run(run_pipeline())"
```

### 6. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:3000
```

### 7. Run scorer unit tests

```bash
pytest pipeline/tests/test_scorer.py -v
```

## Project Structure

```
skirank/
├── frontend/       # Next.js 14 app (TypeScript + Tailwind)
├── backend/        # FastAPI + SQLAlchemy
├── pipeline/       # Data fetcher, scorer, writer, scheduler
├── data/           # Resort seed CSV
├── docker-compose.yml
└── .env.example
```

## Environment Variables

Copy `.env.example` to `.env` and fill in:

- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `NEXT_PUBLIC_MAPBOX_TOKEN` — Mapbox public token for map view
- `SENDGRID_API_KEY` — For pipeline failure alerts (optional)

## Architecture

```
Next.js Frontend → FastAPI Backend → PostgreSQL
Python Pipeline → PostgreSQL (daily at 06:00 UTC)
Pipeline → Open-Meteo API (weather data, free, no key)
```
