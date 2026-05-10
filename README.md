# Setup

To create uv environment
```bash
uv sync
```

# Run
Init database, you need to have `.env` for it
```dotenv
DB_NAME=smieciarka_db
DB_USER=<>
DB_PASSWORD=<>
```


```bash
make run-db
```

Run FastAPI server
```bash
make run-server
```

Dev (auto-reload)
```bash
make run-server-dev
```

## Commands (PowerShell / Windows)

### Setup

```powershell
uv sync
docker compose up -d
uv run alembic upgrade head
```

Optional: seed bigger dataset (to force breakpoint sooner):

```powershell
$env:SEED_USERS_COUNT="2000"
$env:SEED_OFFERS_COUNT="20000"
$env:SEED_RES_PER_OFFER="2"
uv run python scripts/seed_offers.py
```

### Run API (production-like)

```powershell
$env:WEB_CONCURRENCY="2"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers $env:WEB_CONCURRENCY
```

### Smoke tests (every endpoint)

```powershell
uv run pytest -q
```

### Breakpoint ramps (writes `*_steps.csv/json` + per-request `*.csv/json`)

Offers (`GET /offers`, multi-user sessions):

```powershell
uv run python scripts/breakpoint_ramp.py `
  --path /offers `
  --method GET `
  --requests-per-step 1500 `
  --concurrency 10,20,40,80,120,160 `
  --users 50 `
  --out-prefix offers_ramp
```

Reservations (`POST /reservations/1`, auth simulated via auto-register):

```powershell
uv run python scripts/breakpoint_ramp.py `
  --path /reservations/1 `
  --method POST `
  --requests-per-step 300 `
  --concurrency 10,20,40,80 `
  --users 50 `
  --auto-register `
  --out-prefix reservations_ramp
```

### Single benchmark (also saves per-request CSV + summary JSON)

```powershell
uv run python scripts/bench_api.py --path /offers --method GET -n 5000 -c 80 --users 50 --out-prefix offers_bench
```

Reservations (auth via auto-register):

```powershell
uv run python scripts/bench_api.py --path /reservations/1 --method POST -n 1000 -c 40 --users 50 --auto-register --out-prefix reservations_bench
```

### Postgres pgstats (`pg_stat_statements`)

Enable extension (once per database):

```powershell
docker ps
# take container name for Postgres (e.g. smieciarka-db-1) and use it below:
docker exec -it <POSTGRES_CONTAINER> psql -U $env:DB_USER -d $env:DB_NAME -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements;"
```

Top statements (run after ramp):

```powershell
docker exec -it <POSTGRES_CONTAINER> psql -U $env:DB_USER -d $env:DB_NAME -c "SELECT calls,total_exec_time,mean_exec_time,rows,left(query,200) AS query FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;"
```

Reset stats (before next run):

```powershell
docker exec -it <POSTGRES_CONTAINER> psql -U $env:DB_USER -d $env:DB_NAME -c "SELECT pg_stat_statements_reset();"
```

### External benchmarks (simple GET load)

Apache Bench:

```powershell
ab -n 20000 -c 100 http://127.0.0.1:8000/offers
```

Siege:

```powershell
siege -c 100 -r 200 http://127.0.0.1:8000/offers
```

## Performance / bottleneck hunting

### Postgres: `pg_stat_statements` (pgstats)

`docker-compose.yml` enables `pg_stat_statements` via `shared_preload_libraries`.

Once DB is up, enable extension (once per database):
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

Example queries to find slow/heavy statements:
```sql
SELECT
  calls,
  total_exec_time,
  mean_exec_time,
  rows,
  query
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Benchmarks (API load)

- Apache Bench (ab):
```bash
ab -n 2000 -c 50 http://127.0.0.1:8000/offers
```

- Siege:
```bash
siege -c 50 -r 40 http://127.0.0.1:8000/offers
```

JMeter: use Thread Group + HTTP Request to hit `/offers` and `/reservations/{offer_id}` (after login cookie).

### Easiest: built-in benchmark script (saves latencies)

Run:
```bash
uv run python scripts/bench_api.py --path /offers -n 2000 -c 50 --out-prefix offers
```

Authenticated endpoint example:
```bash
set BENCH_EMAIL=your@email
set BENCH_PASSWORD=your_password
uv run python scripts/bench_api.py --path /reservations/1 --method POST -n 500 -c 20 --out-prefix reserve
```

Outputs:
- `<prefix>_YYYYmmdd_HHMMSS.csv` per-request latencies
- `<prefix>_YYYYmmdd_HHMMSS.json` summary (p50/p95/p99, RPS, errors)

### Breakpoint procedure

- Start with **every endpoint smoke-tested** (`pytest`).
- Run benchmark; if **no breakpoint** (latency/throughput stable), increase:
  - dataset size (seed more offers/users),
  - request rate/concurrency,
  - and/or **decrease DB resources** (cpu/mem) in compose.
- If bottleneck looks like Uvicorn, keep DB constant and scale app (workers) via `WEB_CONCURRENCY`.
