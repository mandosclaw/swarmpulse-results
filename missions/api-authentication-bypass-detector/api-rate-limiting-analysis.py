#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    API Rate Limiting Analysis
# Mission: API Authentication Bypass Detector
# Agent:   @sue
# Date:    2026-03-23T13:09:13.320Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
API Rate Limiting Analysis — detects rate limit thresholds and window behavior.
"""
import argparse
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

@dataclass
class RateLimitResult:
    url: str
    requests_sent: int = 0
    requests_succeeded: int = 0
    requests_blocked: int = 0
    first_block_at: Optional[int] = None
    retry_after: Optional[int] = None
    headers: dict = field(default_factory=dict)
    latencies_ms: list = field(default_factory=list)

    def threshold_estimate(self) -> int:
        return self.first_block_at or self.requests_sent

    def report(self) -> dict:
        avg_lat = sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0
        return {
            "url": self.url,
            "threshold_estimate": self.threshold_estimate(),
            "total_sent": self.requests_sent,
            "blocked": self.requests_blocked,
            "retry_after_seconds": self.retry_after,
            "avg_latency_ms": round(avg_lat, 2),
            "rate_limit_headers": {
                k: v for k, v in self.headers.items()
                if any(x in k.lower() for x in ["ratelimit", "rate-limit", "x-ratelimit", "retry"])
            },
        }

async def probe_endpoint(
    session: aiohttp.ClientSession,
    url: str,
    max_requests: int = 200,
    concurrency: int = 10,
    headers: Optional[dict] = None,
) -> RateLimitResult:
    result = RateLimitResult(url=url)
    sem = asyncio.Semaphore(concurrency)

    async def single_request(n: int):
        async with sem:
            t0 = time.monotonic()
            try:
                async with session.get(url, headers=headers or {}, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    elapsed = (time.monotonic() - t0) * 1000
                    result.requests_sent += 1
                    result.latencies_ms.append(elapsed)
                    if resp.status == 429:
                        result.requests_blocked += 1
                        if result.first_block_at is None:
                            result.first_block_at = n
                        ra = resp.headers.get("Retry-After")
                        if ra and result.retry_after is None:
                            result.retry_after = int(ra)
                        result.headers.update(dict(resp.headers))
                        log.warning("429 on request #%d — rate limited", n)
                    elif resp.status < 400:
                        result.requests_succeeded += 1
                        result.headers.update(dict(resp.headers))
                    else:
                        log.info("HTTP %d on request #%d", resp.status, n)
            except asyncio.TimeoutError:
                log.warning("Timeout on request #%d", n)
            except Exception as exc:
                log.error("Error on request #%d: %s", n, exc)

    tasks = [single_request(i + 1) for i in range(max_requests)]
    await asyncio.gather(*tasks)
    return result

async def run(args: argparse.Namespace):
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        results = []
        for url in args.urls:
            log.info("Probing %s (max=%d, concurrency=%d)", url, args.max_requests, args.concurrency)
            result = await probe_endpoint(
                session, url,
                max_requests=args.max_requests,
                concurrency=args.concurrency,
                headers={"User-Agent": "RateLimitProbe/1.0"},
            )
            report = result.report()
            results.append(report)
            log.info("Result: %s", json.dumps(report, indent=2))

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            log.info("Wrote results to %s", args.output)
        return results

def main():
    parser = argparse.ArgumentParser(description="API Rate Limit Analyzer")
    parser.add_argument("urls", nargs="+", help="Endpoints to probe")
    parser.add_argument("--max-requests", type=int, default=150, help="Max requests per endpoint")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent request workers")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    args = parser.parse_args()
    asyncio.run(run(args))

if __name__ == "__main__":
    main()
