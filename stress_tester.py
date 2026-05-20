#!/usr/bin/env python3
"""Simple stress-testing CLI for web apps, designed for GitHub projects."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Result:
    endpoint: str
    status_code: int | None
    latency_ms: float
    ok: bool
    error: str | None = None


def parse_headers(headers: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for h in headers:
        if ":" not in h:
            raise ValueError(f"Invalid header format: {h}. Use 'Name: Value'.")
        key, value = h.split(":", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def hit_endpoint(
    endpoint: str,
    method: str,
    timeout: float,
    headers: dict[str, str],
    body: bytes | None,
) -> Result:
    start = time.perf_counter()
    req = urllib.request.Request(endpoint, method=method, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency = (time.perf_counter() - start) * 1000
            status = response.getcode()
            return Result(endpoint, status, latency, 200 <= status < 400)
    except urllib.error.HTTPError as exc:
        latency = (time.perf_counter() - start) * 1000
        return Result(endpoint, exc.code, latency, False, str(exc))
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return Result(endpoint, None, latency, False, str(exc))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    values = sorted(values)
    rank = (len(values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return values[int(rank)]
    return values[low] + (values[high] - values[low]) * (rank - low)


def run_stress(
    endpoints: Iterable[str],
    requests: int,
    concurrency: int,
    method: str,
    timeout: float,
    headers: dict[str, str],
    body: bytes | None,
) -> dict:
    endpoint_list = [e.strip() for e in endpoints if e.strip()]
    if not endpoint_list:
        raise ValueError("No valid endpoints provided.")

    scheduled = [endpoint_list[i % len(endpoint_list)] for i in range(requests)]

    started = time.perf_counter()
    results: list[Result] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(hit_endpoint, ep, method, timeout, headers, body) for ep in scheduled]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
    total_seconds = time.perf_counter() - started

    latencies = [r.latency_ms for r in results]
    successes = [r for r in results if r.ok]
    failures = [r for r in results if not r.ok]

    by_status: dict[str, int] = {}
    for r in results:
        key = str(r.status_code) if r.status_code is not None else "error"
        by_status[key] = by_status.get(key, 0) + 1

    return {
        "summary": {
            "total_requests": len(results),
            "successful_requests": len(successes),
            "failed_requests": len(failures),
            "success_rate_percent": round((len(successes) / len(results)) * 100, 2),
            "duration_seconds": round(total_seconds, 3),
            "requests_per_second": round(len(results) / total_seconds, 2) if total_seconds > 0 else 0.0,
        },
        "request_config": {
            "method": method,
            "headers": headers,
            "body_bytes": len(body) if body else 0,
            "concurrency": concurrency,
            "timeout_seconds": timeout,
        },
        "latency_ms": {
            "min": round(min(latencies), 2) if latencies else 0.0,
            "max": round(max(latencies), 2) if latencies else 0.0,
            "avg": round(statistics.mean(latencies), 2) if latencies else 0.0,
            "p50": round(percentile(latencies, 0.50), 2) if latencies else 0.0,
            "p95": round(percentile(latencies, 0.95), 2) if latencies else 0.0,
            "p99": round(percentile(latencies, 0.99), 2) if latencies else 0.0,
        },
        "status_codes": by_status,
        "failures": [
            {"endpoint": f.endpoint, "status_code": f.status_code, "error": f.error}
            for f in failures[:20]
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stress test one or more HTTP endpoints (great for apps hosted from GitHub projects)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single URL to stress test.")
    group.add_argument("--url-file", help="Text file containing one URL per line.")

    parser.add_argument("--requests", type=int, default=200, help="Total requests to send.")
    parser.add_argument("--concurrency", type=int, default=20, help="Parallel workers.")
    parser.add_argument("--method", default="GET", choices=["GET", "HEAD", "POST", "PUT", "PATCH"], help="HTTP method.")
    parser.add_argument("--timeout", type=float, default=10.0, help="Timeout in seconds per request.")
    parser.add_argument("--header", action="append", default=[], help="HTTP header in 'Name: Value' format. Repeatable.")
    parser.add_argument("--body", default="", help="Raw request body for POST/PUT/PATCH.")
    parser.add_argument("--output", default="stress_report.json", help="Path to save JSON report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.requests < 1:
        raise SystemExit("--requests must be >= 1")
    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")

    if args.url:
        endpoints = [args.url]
    else:
        with open(args.url_file, "r", encoding="utf-8") as f:
            endpoints = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    headers = parse_headers(args.header)
    body = args.body.encode("utf-8") if args.body else None

    report = run_stress(
        endpoints=endpoints,
        requests=args.requests,
        concurrency=args.concurrency,
        method=args.method,
        timeout=args.timeout,
        headers=headers,
        body=body,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("Stress test finished.")
    print(json.dumps(report["summary"], indent=2))
    print(f"Full report saved to {args.output}")


if __name__ == "__main__":
    main()
