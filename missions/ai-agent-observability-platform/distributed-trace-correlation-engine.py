#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Distributed trace correlation engine
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-23T22:17:50.516Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Distributed trace correlation engine — correlates OTLP spans across services, detects broken chains."""
import argparse, json, logging, sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

@dataclass
class Span:
    trace_id: str; span_id: str; parent_span_id: Optional[str]
    service: str; operation: str
    start_us: int; end_us: int
    status: str = "ok"
    children: list = field(default_factory=list)

    def duration_ms(self) -> float:
        return (self.end_us - self.start_us) / 1000

@dataclass
class Trace:
    trace_id: str
    spans: list[Span] = field(default_factory=list)
    broken_chains: list[str] = field(default_factory=list)
    critical_path_ms: float = 0.0

def parse_otlp_jsonl(path: str) -> list[Span]:
    spans = []
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
                for rs in d.get("resourceSpans", []):
                    svc = rs.get("resource", {}).get("attributes", [{}])[0].get("value", {}).get("stringValue", "unknown")
                    for ss in rs.get("scopeSpans", []):
                        for s in ss.get("spans", []):
                            spans.append(Span(
                                trace_id=s["traceId"], span_id=s["spanId"],
                                parent_span_id=s.get("parentSpanId"),
                                service=svc, operation=s.get("name", ""),
                                start_us=int(s.get("startTimeUnixNano", 0)) // 1000,
                                end_us=int(s.get("endTimeUnixNano", 0)) // 1000,
                                status="error" if s.get("status", {}).get("code") == 2 else "ok",
                            ))
            except Exception as e:
                log.debug("Parse error: %s", e)
    return spans

def correlate(spans: list[Span]) -> list[Trace]:
    by_trace: dict[str, list[Span]] = defaultdict(list)
    for s in spans:
        by_trace[s.trace_id].append(s)
    traces = []
    for trace_id, sps in by_trace.items():
        t = Trace(trace_id=trace_id, spans=sps)
        span_ids = {s.span_id for s in sps}
        for s in sps:
            if s.parent_span_id and s.parent_span_id not in span_ids:
                t.broken_chains.append(f"{s.service}/{s.operation} missing parent {s.parent_span_id[:8]}")
        durations = sorted(s.duration_ms() for s in sps)
        t.critical_path_ms = sum(durations[-3:]) if len(durations) >= 3 else sum(durations)
        traces.append(t)
    return traces

def main():
    parser = argparse.ArgumentParser(description="Distributed Trace Correlation Engine")
    parser.add_argument("spans_file", help="OTLP spans JSONL file")
    parser.add_argument("--output", "-o", help="Write report to file")
    parser.add_argument("--broken-only", action="store_true", help="Only show traces with broken chains")
    args = parser.parse_args()
    spans = parse_otlp_jsonl(args.spans_file)
    log.info("Loaded %d spans", len(spans))
    traces = correlate(spans)
    log.info("Correlated %d traces", len(traces))
    results = [{"trace_id": t.trace_id, "spans": len(t.spans), "broken_chains": t.broken_chains,
                "critical_path_ms": round(t.critical_path_ms, 2)} for t in traces
               if not args.broken_only or t.broken_chains]
    results.sort(key=lambda x: -x["critical_path_ms"])
    report = {"total_traces": len(traces), "broken_traces": sum(1 for t in traces if t.broken_chains), "traces": results}
    print(json.dumps(report, indent=2))
    if args.output:
        with open(args.output, "w") as f: json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
