"""Measure public API latency and cache status without credentials or database writes."""
import argparse
import json
import math
import statistics
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:4173/api/site")
    parser.add_argument("--requests", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.requests <= 200:
        parser.error("--requests must be 1..200")
    parsed = urlsplit(args.url)
    if parsed.path not in {"/api/site", "/api/vehicles", "/api/parts", "/api/news"}:
        parser.error("Choose a public site, vehicles, parts or news endpoint")
    timings, statuses, sizes = [], {}, []
    for _ in range(args.requests):
        started = time.perf_counter()
        with urlopen(Request(args.url, headers={"Accept-Encoding": "gzip"}), timeout=30) as response:
            sizes.append(len(response.read()))
            status = response.headers.get("X-Data-Cache", "unknown")
            statuses[status] = statuses.get(status, 0) + 1
        timings.append((time.perf_counter() - started) * 1000)
    ordered = sorted(timings)
    print(json.dumps({"requests": len(timings), "first_ms": round(timings[0], 2),
        "p50_ms": round(statistics.median(timings), 2),
        "p95_ms": round(ordered[math.ceil(len(ordered) * 0.95) - 1], 2),
        "cache": statuses, "mean_bytes": round(statistics.mean(sizes))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
