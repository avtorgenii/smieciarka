import argparse
import asyncio
import csv
import json
import os
from datetime import datetime

import sys
from pathlib import Path

# Ensure repo root is on sys.path when running as a script from /scripts on Windows.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.bench_api import benchmark  # noqa: E402


def _detect_breakpoint(steps: list[dict]) -> dict | None:
    """
    Heuristic breakpoint detection:
    - any errors > 0 is immediate breakpoint
    - p95 jump >= 2x compared to previous step
    - p95 increase >= 50% while RPS increase <= 10% (throughput plateau + latency growth)
    """
    prev = None
    for s in steps:
        if s.get("errors", 0) and s["errors"] > 0:
            return {"reason": "errors>0", "step": s}

        p95 = s.get("p95_ms")
        rps = s.get("rps")
        if prev is not None and p95 is not None and prev.get("p95_ms") is not None:
            prev_p95 = prev["p95_ms"]
            if prev_p95 and p95 >= 2.0 * prev_p95:
                return {"reason": "p95_jump>=2x", "prev": prev, "step": s}

            # plateau: little throughput gain + big latency growth
            prev_rps = prev.get("rps")
            if prev_p95 and prev_rps and rps:
                p95_growth = (p95 - prev_p95) / prev_p95
                rps_growth = (rps - prev_rps) / prev_rps
                if p95_growth >= 0.50 and rps_growth <= 0.10:
                    return {
                        "reason": "plateau_rps<=10%_p95>=50%",
                        "prev": prev,
                        "step": s,
                        "p95_growth": p95_growth,
                        "rps_growth": rps_growth,
                    }

        prev = s
    return None


async def run() -> int:
    ap = argparse.ArgumentParser(description="Run a ramp of benchmarks to find breakpoint.")
    ap.add_argument("--base-url", default=os.getenv("BASE_URL", "http://127.0.0.1:8000"))
    ap.add_argument("--path", default="/offers")
    ap.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    ap.add_argument("--requests-per-step", type=int, default=1000)
    ap.add_argument("--concurrency", default="5,10,20,40,80", help="Comma-separated concurrency steps")
    ap.add_argument("--users", type=int, default=1, help="Independent sessions (cookie jars) per step")
    ap.add_argument(
        "--auto-register",
        action="store_true",
        help="Create distinct accounts via /auth/register (one per session) before each step",
    )
    ap.add_argument("--register-password", default=os.getenv("BENCH_REGISTER_PASSWORD", "Password0001!!"))
    ap.add_argument("--out-prefix", default="ramp")
    ap.add_argument("--login-email", default=os.getenv("BENCH_EMAIL"))
    ap.add_argument("--login-password", default=os.getenv("BENCH_PASSWORD"))
    ap.add_argument("--tag", default="", help="Optional tag added to each step summary")
    args = ap.parse_args()

    steps = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_steps_csv = f"{args.out_prefix}_{ts}_steps.csv"
    out_steps_json = f"{args.out_prefix}_{ts}_steps.json"

    step_summaries: list[dict] = []

    for c in steps:
        print(f"Step start: concurrency={c} users={args.users} n={args.requests_per_step}")
        step_prefix = f"{args.out_prefix}_{ts}_c{c}"
        _samples, summary, out_csv, out_json = await benchmark(
            base_url=args.base_url,
            path=args.path,
            method=args.method,
            requests=args.requests_per_step,
            concurrency=c,
            users=args.users,
            auto_register=args.auto_register,
            register_password=args.register_password,
            login_email=args.login_email,
            login_password=args.login_password,
            json_body=None,
            form_body=None,
            out_prefix=step_prefix,
            tag=(f"{args.tag} " if args.tag else "") + f"c={c}",
        )
        print(
            f"Step done: concurrency={c} rps={summary['rps']:.2f} errors={summary['errors']} "
            f"p95_ms={summary['latency_ms']['p95']}"
        )
        step_summaries.append(
            {
                "concurrency": c,
                "rps": summary["rps"],
                "errors": summary["errors"],
                "p50_ms": summary["latency_ms"]["p50"],
                "p95_ms": summary["latency_ms"]["p95"],
                "p99_ms": summary["latency_ms"]["p99"],
                "users": summary.get("users"),
                "out_csv": out_csv,
                "out_json": out_json,
            }
        )

    breakpoint_info = _detect_breakpoint(step_summaries)

    with open(out_steps_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "base_url": args.base_url,
                "path": args.path,
                "method": args.method,
                "requests_per_step": args.requests_per_step,
                "users": args.users,
                "breakpoint": breakpoint_info,
                "steps": step_summaries,
            },
            f,
            indent=2,
        )

    with open(out_steps_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["concurrency", "users", "rps", "errors", "p50_ms", "p95_ms", "p99_ms", "out_csv", "out_json"],
        )
        w.writeheader()
        for s in step_summaries:
            w.writerow(s)

    print(f"Wrote {out_steps_csv} and {out_steps_json}")
    print("Each step also wrote its own per-request CSV + summary JSON from bench_api.")
    if breakpoint_info:
        step = breakpoint_info.get("step", {})
        print(f"Breakpoint detected at concurrency={step.get('concurrency')} reason={breakpoint_info.get('reason')}")
    else:
        print("No breakpoint detected by heuristic (consider higher concurrency / more requests / fewer DB resources).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))

