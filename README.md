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
