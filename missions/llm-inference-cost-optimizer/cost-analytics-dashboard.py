#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-23T18:09:31.552Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Parse OpenAI usage logs, compute cost per model/day/feature, generate markdown cost report."""

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_COSTS: dict[str, dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.002},
}


@dataclass
class UsageRecord:
    timestamp: str
    model: str
    feature: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    request_id: str = ""


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-3.5-turbo"])
    return (input_tokens / 1000) * costs["input"] + (output_tokens / 1000) * costs["output"]


def load_usage_logs(log_path: str) -> list[UsageRecord]:
    records = []
    path = Path(log_path)
    if not path.exists():
        logger.warning(f"Log file {log_path} not found, generating synthetic data")
        return generate_synthetic_data()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                model = entry.get("model", "gpt-3.5-turbo")
                input_tokens = entry.get("tokens_in", entry.get("prompt_tokens", 100))
                output_tokens = entry.get("tokens_out", entry.get("completion_tokens", 50))
                cost = entry.get("cost_usd") or compute_cost(model, input_tokens, output_tokens)
                records.append(UsageRecord(timestamp=entry.get("timestamp", entry.get("created_at", datetime.now().isoformat())), model=model, feature=entry.get("feature", entry.get("complexity", "unknown")), input_tokens=int(input_tokens), output_tokens=int(output_tokens), cost_usd=round(float(cost), 6), request_id=entry.get("request_id", "")))
            except (json.JSONDecodeError, KeyError) as e:
                logger.debug(f"Skipping malformed log line: {e}")
    return records


def generate_synthetic_data() -> list[UsageRecord]:
    import random
    random.seed(42)
    records = []
    models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    features = ["chat", "summarization", "code_review", "classification", "embedding"]
    base = datetime.now() - timedelta(days=14)
    for i in range(200):
        model = random.choices(models, weights=[0.7, 0.2, 0.1])[0]
        feature = random.choice(features)
        input_t = random.randint(100, 2000)
        output_t = random.randint(50, 800)
        cost = compute_cost(model, input_t, output_t)
        ts = (base + timedelta(hours=random.randint(0, 14 * 24))).isoformat()
        records.append(UsageRecord(timestamp=ts, model=model, feature=feature, input_tokens=input_t, output_tokens=output_t, cost_usd=round(cost, 6)))
    return records


def analyze_costs(records: list[UsageRecord]) -> dict[str, Any]:
    by_model: dict[str, dict] = defaultdict(lambda: {"requests": 0, "cost": 0.0, "input_tokens": 0, "output_tokens": 0})
    by_day: dict[str, dict] = defaultdict(lambda: {"requests": 0, "cost": 0.0})
    by_feature: dict[str, dict] = defaultdict(lambda: {"requests": 0, "cost": 0.0})

    for rec in records:
        m = by_model[rec.model]
        m["requests"] += 1
        m["cost"] += rec.cost_usd
        m["input_tokens"] += rec.input_tokens
        m["output_tokens"] += rec.output_tokens

        day = rec.timestamp[:10]
        by_day[day]["requests"] += 1
        by_day[day]["cost"] += rec.cost_usd

        by_feature[rec.feature]["requests"] += 1
        by_feature[rec.feature]["cost"] += rec.cost_usd

    days_sorted = sorted(by_day.keys())
    recent_7 = days_sorted[-7:]
    previous_7 = days_sorted[-14:-7]
    recent_cost = sum(by_day[d]["cost"] for d in recent_7)
    prev_cost = sum(by_day[d]["cost"] for d in previous_7)
    trend = ((recent_cost - prev_cost) / max(prev_cost, 0.001)) * 100

    return {"total_requests": len(records), "total_cost_usd": round(sum(r.cost_usd for r in records), 4), "by_model": {k: {**v, "cost": round(v["cost"], 4), "avg_cost_per_req": round(v["cost"] / max(v["requests"], 1), 6)} for k, v in by_model.items()}, "by_day": {k: {**v, "cost": round(v["cost"], 4)} for k, v in sorted(by_day.items())}, "by_feature": {k: {**v, "cost": round(v["cost"], 4), "avg_cost": round(v["cost"] / max(v["requests"], 1), 6)} for k, v in by_feature.items()}, "trend_pct_vs_prev_week": round(trend, 1), "recent_7day_cost": round(recent_cost, 4)}


def render_markdown_report(analysis: dict[str, Any], output_path: str) -> None:
    lines = ["# LLM Cost Analytics Report", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*", "", "## Summary", f"- **Total Requests:** {analysis['total_requests']:,}", f"- **Total Cost:** ${analysis['total_cost_usd']:.4f}", f"- **Last 7 Days:** ${analysis['recent_7day_cost']:.4f}", f"- **WoW Trend:** {'↑' if analysis['trend_pct_vs_prev_week'] > 0 else '↓'} {abs(analysis['trend_pct_vs_prev_week']):.1f}%", "", "## Cost by Model", "", "| Model | Requests | Total Cost | Avg Cost/Req |", "|-------|----------|------------|--------------|"]
    for model, data in sorted(analysis["by_model"].items(), key=lambda x: -x[1]["cost"]):
        lines.append(f"| {model} | {data['requests']:,} | ${data['cost']:.4f} | ${data['avg_cost_per_req']:.6f} |")

    lines += ["", "## Cost by Feature", "", "| Feature | Requests | Total Cost | Avg Cost/Req |", "|---------|----------|------------|--------------|"]
    for feature, data in sorted(analysis["by_feature"].items(), key=lambda x: -x[1]["cost"]):
        lines += [f"| {feature} | {data['requests']:,} | ${data['cost']:.4f} | ${data['avg_cost']:.6f} |"]

    lines += ["", "## Daily Cost Trend (Last 14 Days)", "", "| Date | Requests | Cost |", "|------|----------|------|"]
    for day, data in list(sorted(analysis["by_day"].items()))[-14:]:
        lines.append(f"| {day} | {data['requests']} | ${data['cost']:.4f} |")

    lines += ["", "## Optimization Recommendations", ""]
    gpt4_cost = analysis["by_model"].get("gpt-4", {}).get("cost", 0)
    gpt35_cost = analysis["by_model"].get("gpt-3.5-turbo", {}).get("cost", 0)
    if gpt4_cost > 0:
        lines.append(f"- Consider routing more simple prompts to gpt-3.5-turbo (currently ${gpt4_cost:.4f} on gpt-4)")
    if analysis["trend_pct_vs_prev_week"] > 20:
        lines.append(f"- Cost grew {analysis['trend_pct_vs_prev_week']:.1f}% WoW — investigate usage spike")
    lines.append("- Enable prompt caching for repeated/similar queries")
    lines.append("- Set max_tokens limits to prevent runaway output costs")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    logger.info(f"Report written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM cost analytics dashboard")
    parser.add_argument("--input", default="llm_costs.jsonl", help="Usage log file (JSONL)")
    parser.add_argument("--output", default="cost_report.md")
    parser.add_argument("--json-output", default="cost_analysis.json")
    args = parser.parse_args()

    logger.info(f"Loading usage logs from {args.input}")
    records = load_usage_logs(args.input)
    logger.info(f"Loaded {len(records)} usage records")

    analysis = analyze_costs(records)
    render_markdown_report(analysis, args.output)

    with open(args.json_output, "w") as f:
        json.dump(analysis, f, indent=2, default=str)

    print(json.dumps({"total_requests": analysis["total_requests"], "total_cost_usd": analysis["total_cost_usd"], "trend_pct": analysis["trend_pct_vs_prev_week"], "report": args.output}, indent=2))


if __name__ == "__main__":
    main()
