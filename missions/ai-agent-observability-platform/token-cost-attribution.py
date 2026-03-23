#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Token cost attribution
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-23T22:16:50.377Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Token cost attribution — parses LLM API logs and attributes token usage/cost per agent/task/project."""
import argparse, json, logging, re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PRICING = {  # USD per 1K tokens (input, output)
    "gpt-4o": (0.005, 0.015), "gpt-4-turbo": (0.01, 0.03),
    "gpt-3.5-turbo": (0.0005, 0.0015), "claude-3-opus": (0.015, 0.075),
    "claude-3-sonnet": (0.003, 0.015), "claude-3-haiku": (0.00025, 0.00125),
}

@dataclass
class UsageRecord:
    agent: str; task: str; project: str; model: str
    input_tokens: int = 0; output_tokens: int = 0

    def cost(self) -> float:
        p = PRICING.get(self.model, (0.01, 0.03))
        return (self.input_tokens * p[0] + self.output_tokens * p[1]) / 1000

@dataclass
class Attribution:
    by_agent: dict = field(default_factory=lambda: defaultdict(float))
    by_project: dict = field(default_factory=lambda: defaultdict(float))
    by_model: dict = field(default_factory=lambda: defaultdict(float))
    total_cost: float = 0.0; total_tokens: int = 0

def parse_log(path: Path) -> list[UsageRecord]:
    records = []
    for line in path.read_text().splitlines():
        try:
            d = json.loads(line)
            r = UsageRecord(
                agent=d.get("agent", "unknown"), task=d.get("task", ""),
                project=d.get("project", ""), model=d.get("model", "gpt-4o"),
                input_tokens=d.get("usage", {}).get("prompt_tokens", 0),
                output_tokens=d.get("usage", {}).get("completion_tokens", 0),
            )
            records.append(r)
        except (json.JSONDecodeError, KeyError):
            pass
    return records

def attribute(records: list[UsageRecord]) -> Attribution:
    attr = Attribution()
    for r in records:
        cost = r.cost()
        attr.by_agent[r.agent] += cost
        attr.by_project[r.project] += cost
        attr.by_model[r.model] += cost
        attr.total_cost += cost
        attr.total_tokens += r.input_tokens + r.output_tokens
    return attr

def main():
    parser = argparse.ArgumentParser(description="LLM Token Cost Attribution")
    parser.add_argument("logs", nargs="+", help="JSONL log files to process")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    parser.add_argument("--top", type=int, default=10, help="Top N agents/projects to show")
    args = parser.parse_args()
    records = []
    for p in args.logs:
        records.extend(parse_log(Path(p)))
    log.info("Parsed %d usage records", len(records))
    attr = attribute(records)
    report = {
        "total_cost_usd": round(attr.total_cost, 4),
        "total_tokens": attr.total_tokens,
        "by_agent": dict(sorted(attr.by_agent.items(), key=lambda x: -x[1])[:args.top]),
        "by_project": dict(sorted(attr.by_project.items(), key=lambda x: -x[1])[:args.top]),
        "by_model": dict(sorted(attr.by_model.items(), key=lambda x: -x[1])[:args.top]),
    }
    print(json.dumps(report, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
