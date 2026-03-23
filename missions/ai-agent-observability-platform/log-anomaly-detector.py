#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Log anomaly detector
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-23T22:17:51.356Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Log anomaly detector — computes per-field baselines and flags lines exceeding 3-sigma threshold."""
import argparse, json, logging, math, re, sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

@dataclass
class FieldStats:
    values: list = field(default_factory=list)
    def mean(self): return sum(self.values) / len(self.values) if self.values else 0
    def stddev(self):
        if len(self.values) < 2: return 0
        m = self.mean(); return math.sqrt(sum((v - m) ** 2 for v in self.values) / len(self.values))
    def z_score(self, v): s = self.stddev(); return abs(v - self.mean()) / s if s > 0 else 0

NUMERIC = re.compile(r'\b(\d+(?:\.\d+)?)\b')
KV = re.compile(r'(\w+)=(".*?"|\S+)')

def parse_line(line: str) -> dict:
    fields = {}
    for k, v in KV.findall(line):
        try: fields[k] = float(v.strip('"'))
        except ValueError: pass
    nums = NUMERIC.findall(line)
    if nums: fields["_first_num"] = float(nums[0])
    return fields

def detect_anomalies(path: Path, sigma: float = 3.0, train_lines: int = 1000) -> list[dict]:
    stats: dict[str, FieldStats] = defaultdict(FieldStats)
    lines = path.read_text().splitlines()
    for line in lines[:train_lines]:
        for k, v in parse_line(line).items():
            stats[k].values.append(v)
    log.info("Baseline built from %d lines, %d fields", min(len(lines), train_lines), len(stats))
    anomalies = []
    for i, line in enumerate(lines[train_lines:], start=train_lines + 1):
        fields = parse_line(line)
        for k, v in fields.items():
            if k in stats and len(stats[k].values) >= 30:
                z = stats[k].z_score(v)
                if z > sigma:
                    anomalies.append({"line": i, "field": k, "value": v,
                        "z_score": round(z, 2), "mean": round(stats[k].mean(), 4),
                        "stddev": round(stats[k].stddev(), 4), "excerpt": line[:120]})
            stats[k].values.append(v)
    anomalies.sort(key=lambda x: -x["z_score"])
    return anomalies

def main():
    parser = argparse.ArgumentParser(description="Log Anomaly Detector (z-score based)")
    parser.add_argument("logfile", help="Log file to analyze")
    parser.add_argument("--sigma", type=float, default=3.0, help="Z-score threshold (default 3.0)")
    parser.add_argument("--train", type=int, default=1000, help="Lines to use for baseline")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    parser.add_argument("--top", type=int, default=20, help="Top N anomalies to return")
    args = parser.parse_args()
    anomalies = detect_anomalies(Path(args.logfile), args.sigma, args.train)
    report = {"sigma_threshold": args.sigma, "total_anomalies": len(anomalies), "top": anomalies[:args.top]}
    print(json.dumps(report, indent=2))
    if args.output:
        with open(args.output, "w") as f: json.dump(report, f, indent=2)
    log.info("Found %d anomalies above %.1f-sigma", len(anomalies), args.sigma)

if __name__ == "__main__":
    main()
