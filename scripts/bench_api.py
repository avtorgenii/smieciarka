import argparse
import asyncio
import csv
import json
import math
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass(frozen=True)
class Sample:
    i: int
    ok: bool
    status_code: int | None
    latency_ms: float
    started_at_s: float
    error: str | None


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


async def _login(client: httpx.AsyncClient, email: str, password: str) -> None:
    r = await client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
        timeout=30.0,
    )
    if r.status_code not in (302, 303):
        raise RuntimeError(f"Login failed: status={r.status_code} body={r.text[:300]}")


async def _register(client: httpx.AsyncClient, email: str, password: str) -> None:
    r = await client.post(
        "/auth/register",
        data={
            "email": email,
            "password": password,
            "first_name": "Bench",
            "last_name": "User",
            "phone": "+48 600 000 000",
        },
        follow_redirects=False,
        timeout=30.0,
    )
    # register auto-logs in and redirects
    if r.status_code not in (302, 303):
        raise RuntimeError(f"Register failed: status={r.status_code} body={r.text[:300]}")


async def benchmark(
    *,
    base_url: str,
    path: str,
    method: str,
    requests: int,
    concurrency: int,
    users: int,
    auto_register: bool,
    register_password: str,
    login_email: str | None,
    login_password: str | None,
    json_body: dict[str, Any] | None,
    form_body: dict[str, Any] | None,
    out_prefix: str,
    tag: str,
) -> tuple[list[Sample], dict[str, Any], str, str]:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = f"{out_prefix}_{ts}.csv"
    out_json = f"{out_prefix}_{ts}.json"

    if users < 1:
        raise ValueError("--users must be >= 1")
    users = min(users, requests)  # don't create more sessions than requests

    limits = httpx.Limits(
        max_connections=max(concurrency * 2, 20),
        max_keepalive_connections=max(concurrency, 10),
    )
    semaphore = asyncio.Semaphore(concurrency)

    # Create N independent sessions (each has its own cookies). If login is provided,
    # each session logs in (multiple sessions -> multiple "users" from server PoV).
    # IMPORTANT: share one transport across all clients so they share one connection pool.
    # Without this, `users` *per-client* pools can explode the number of TCP connects and cause ConnectError.
    transport = httpx.AsyncHTTPTransport(limits=limits)
    clients: list[httpx.AsyncClient] = [
        httpx.AsyncClient(base_url=base_url, transport=transport) for _ in range(users)
    ]
    try:
        if auto_register:
            # Create distinct accounts per session, then each session is already logged in (cookie set).
            async def _reg_one(c: httpx.AsyncClient) -> None:
                email = f"bench_{uuid.uuid4().hex[:16]}@example.com"
                await _register(c, email, register_password)

            await asyncio.gather(*[_reg_one(c) for c in clients])
        elif login_email and login_password:
            await asyncio.gather(*[_login(c, login_email, login_password) for c in clients])

        t0 = time.perf_counter()
        tasks = []
        for i in range(requests):
            client = clients[i % users]
            tasks.append(
                asyncio.create_task(
                    _one_request(
                        client=client,
                        i=i,
                        method=method,
                        path=path,
                        json_body=json_body,
                        form_body=form_body,
                        semaphore=semaphore,
                    )
                )
            )
        samples = await asyncio.gather(*tasks)
        elapsed_s = time.perf_counter() - t0
    finally:
        await asyncio.gather(*[c.aclose() for c in clients])
        await transport.aclose()

    lat_ok = sorted([s.latency_ms for s in samples if s.ok])
    ok_count = sum(1 for s in samples if s.ok)
    err_count = len(samples) - ok_count
    rps = (len(samples) / elapsed_s) if elapsed_s > 0 else float("inf")

    summary: dict[str, Any] = {
        "tag": tag,
        "base_url": base_url,
        "path": path,
        "method": method,
        "requests": requests,
        "concurrency": concurrency,
        "users": users,
        "auto_register": auto_register,
        "elapsed_s": elapsed_s,
        "rps": rps,
        "ok": ok_count,
        "errors": err_count,
        "latency_ms": {
            "min": lat_ok[0] if lat_ok else None,
            "p50": _percentile(lat_ok, 50.0) if lat_ok else None,
            "p95": _percentile(lat_ok, 95.0) if lat_ok else None,
            "p99": _percentile(lat_ok, 99.0) if lat_ok else None,
            "max": lat_ok[-1] if lat_ok else None,
        },
    }

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["i", "ok", "status_code", "latency_ms", "started_at_s", "error"],
        )
        w.writeheader()
        for s in samples:
            w.writerow(asdict(s))

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return samples, summary, out_csv, out_json


async def _one_request(
    client: httpx.AsyncClient,
    i: int,
    method: str,
    path: str,
    json_body: dict[str, Any] | None,
    form_body: dict[str, Any] | None,
    semaphore: asyncio.Semaphore,
) -> Sample:
    async with semaphore:
        started_at = time.perf_counter()
        wall_started_at = time.time()
        try:
            r = await client.request(
                method=method,
                url=path,
                json=json_body,
                data=form_body,
                timeout=30.0,
            )
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            ok = 200 <= r.status_code < 400
            return Sample(
                i=i,
                ok=ok,
                status_code=r.status_code,
                latency_ms=latency_ms,
                started_at_s=wall_started_at,
                error=None if ok else (r.text[:200].replace("\n", "\\n") if r.text else "non-2xx/3xx"),
            )
        except Exception as e:  # noqa: BLE001 (we want to record any failure)
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            return Sample(
                i=i,
                ok=False,
                status_code=None,
                latency_ms=latency_ms,
                started_at_s=wall_started_at,
                error=repr(e),
            )


async def run() -> int:
    ap = argparse.ArgumentParser(description="Simple API benchmark (saves latencies to CSV + summary to JSON).")
    ap.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--path", default="/offers", help="Endpoint path, e.g. /offers or /reservations/1")
    ap.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    ap.add_argument("-n", "--requests", type=int, default=1000, help="Total number of requests")
    ap.add_argument("-c", "--concurrency", type=int, default=20, help="Concurrent in-flight requests")
    ap.add_argument("--users", type=int, default=1, help="Number of independent sessions (cookie jars) to simulate")
    ap.add_argument(
        "--auto-register",
        action="store_true",
        help="Create distinct accounts via /auth/register (one per session) before benchmarking",
    )
    ap.add_argument("--register-password", default=os.getenv("BENCH_REGISTER_PASSWORD", "Password0001!!"))
    ap.add_argument("--login-email", default=os.getenv("BENCH_EMAIL"))
    ap.add_argument("--login-password", default=os.getenv("BENCH_PASSWORD"))
    ap.add_argument("--json", default=None, help='JSON body as string, e.g. \'{"x":1}\'')
    ap.add_argument("--form", default=None, help='Form body as JSON string, e.g. \'{"email":"a","password":"b"}\'')
    ap.add_argument("--out-prefix", default="bench", help="Output prefix (files: <prefix>.csv and <prefix>.json)")
    ap.add_argument("--tag", default="", help="Optional tag added into summary JSON")
    args = ap.parse_args()

    json_body = json.loads(args.json) if args.json else None
    form_body = json.loads(args.form) if args.form else None

    _samples, summary, out_csv, out_json = await benchmark(
        base_url=args.base_url,
        path=args.path,
        method=args.method,
        requests=args.requests,
        concurrency=args.concurrency,
        users=args.users,
        auto_register=args.auto_register,
        register_password=args.register_password,
        login_email=args.login_email,
        login_password=args.login_password,
        json_body=json_body,
        form_body=form_body,
        out_prefix=args.out_prefix,
        tag=args.tag,
    )

    print(f"Wrote {out_csv} and {out_json}")
    print(json.dumps(summary, indent=2))
    return 0 if summary["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

