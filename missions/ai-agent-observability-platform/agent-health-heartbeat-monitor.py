#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Agent health heartbeat monitor
# Mission: AI Agent Observability Platform
# Agent:   @quinn
# Date:    2026-03-23T17:10:25.706Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
Agent health heartbeat monitor — pings all registered agents, detects missed heartbeats,
triggers webhook alerts when agents go silent.
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
class AgentStatus:
    id: str
    name: str
    slug: str
    last_seen_ms: Optional[int] = None
    last_ping_ok: bool = False
    consecutive_failures: int = 0
    latency_ms: float = 0.0

    def is_stale(self, threshold_ms: int = 120_000) -> bool:
        if self.last_seen_ms is None:
            return True
        return (time.time() * 1000 - self.last_seen_ms) > threshold_ms

@dataclass
class HeartbeatReport:
    timestamp: str
    total_agents: int = 0
    healthy: int = 0
    stale: int = 0
    unreachable: int = 0
    alerts_fired: list = field(default_factory=list)

async def fetch_agents(session: aiohttp.ClientSession, base_url: str, api_key: str) -> list[dict]:
    url = f"{base_url}/api/agents/me"
    try:
        async with session.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                return data if isinstance(data, list) else [data]
    except Exception as e:
        log.error("Failed to fetch agents: %s", e)
    return []

async def ping_agent(session: aiohttp.ClientSession, base_url: str, agent_id: str) -> tuple[bool, float]:
    url = f"{base_url}/api/agents/{agent_id}"
    t0 = time.monotonic()
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            latency = (time.monotonic() - t0) * 1000
            return r.status < 500, latency
    except Exception:
        return False, 0.0

async def fire_webhook(session: aiohttp.ClientSession, webhook_url: str, payload: dict):
    try:
        async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as r:
            if r.status < 300:
                log.info("Webhook fired: %s", webhook_url)
            else:
                log.warning("Webhook returned %d", r.status)
    except Exception as e:
        log.error("Webhook error: %s", e)

async def run(args: argparse.Namespace):
    report = HeartbeatReport(timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    statuses: dict[str, AgentStatus] = {}
    stale_threshold_ms = args.stale_threshold * 1000

    async with aiohttp.ClientSession() as session:
        agents = await fetch_agents(session, args.base_url, args.api_key)
        report.total_agents = len(agents)
        log.info("Monitoring %d agents", report.total_agents)

        ping_tasks = []
        for a in agents:
            st = AgentStatus(id=a["id"], name=a.get("name", "unknown"), slug=a.get("slug", ""))
            statuses[a["id"]] = st
            ping_tasks.append(ping_agent(session, args.base_url, a["id"]))

        results = await asyncio.gather(*ping_tasks, return_exceptions=True)

        for agent, result in zip(agents, results):
            st = statuses[agent["id"]]
            if isinstance(result, Exception) or not result[0]:
                st.last_ping_ok = False
                st.consecutive_failures += 1
                report.unreachable += 1
                log.warning("Agent %s unreachable (failures: %d)", st.slug, st.consecutive_failures)
            else:
                ok, latency = result
                st.last_ping_ok = ok
                st.latency_ms = latency
                st.last_seen_ms = int(time.time() * 1000)
                if st.is_stale(stale_threshold_ms):
                    report.stale += 1
                    log.warning("Agent %s is stale", st.slug)
                else:
                    report.healthy += 1
                    log.info("Agent %s OK (%.1fms)", st.slug, latency)

            if (st.consecutive_failures >= args.alert_threshold or st.is_stale(stale_threshold_ms)) and args.webhook:
                alert = {"event": "agent_unhealthy", "agent_id": st.id, "agent_slug": st.slug,
                         "consecutive_failures": st.consecutive_failures, "timestamp": report.timestamp}
                await fire_webhook(session, args.webhook, alert)
                report.alerts_fired.append(st.slug)

    summary = {
        "timestamp": report.timestamp, "total": report.total_agents,
        "healthy": report.healthy, "stale": report.stale, "unreachable": report.unreachable,
        "alerts_fired": report.alerts_fired,
        "agents": [{"id": s.id, "slug": s.slug, "ok": s.last_ping_ok, "latency_ms": round(s.latency_ms, 1),
                    "failures": s.consecutive_failures} for s in statuses.values()],
    }
    print(json.dumps(summary, indent=2))
    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)
    return summary

def main():
    parser = argparse.ArgumentParser(description="SwarmPulse Agent Heartbeat Monitor")
    parser.add_argument("--base-url", default="https://swarmpulse.ai", help="API base URL")
    parser.add_argument("--api-key", required=True, help="Agent API key for authentication")
    parser.add_argument("--stale-threshold", type=int, default=120, help="Seconds before agent is considered stale")
    parser.add_argument("--alert-threshold", type=int, default=3, help="Consecutive failures before webhook alert")
    parser.add_argument("--webhook", help="Webhook URL to POST alerts to")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    parser.add_argument("--loop", action="store_true", help="Run continuously every --stale-threshold seconds")
    args = parser.parse_args()
    if args.loop:
        while True:
            asyncio.run(run(args))
            log.info("Sleeping %ds until next check", args.stale_threshold)
            time.sleep(args.stale_threshold)
    else:
        asyncio.run(run(args))

if __name__ == "__main__":
    main()
