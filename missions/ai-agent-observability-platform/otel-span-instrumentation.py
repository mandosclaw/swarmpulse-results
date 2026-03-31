#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OTel span instrumentation
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-31T18:44:50.796Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: OTel span instrumentation
MISSION: AI Agent Observability Platform
AGENT: @dex
DATE: 2024-12-19

Complete OpenTelemetry span instrumentation implementation for AI agent observability,
including distributed tracing, token cost attribution, and span collection.
"""

import argparse
import json
import time
import uuid
import random
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import threading
from collections import defaultdict


class SpanKind(Enum):
    """OpenTelemetry span kinds"""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class SpanStatus(Enum):
    """OpenTelemetry span status codes"""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanEvent:
    """Represents a span event"""
    name: str
    timestamp: float
    attributes: Dict[str, Any]


@dataclass
class SpanLink:
    """Represents a span link for correlation"""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any]


@dataclass
class OTelSpan:
    """Complete OpenTelemetry span"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float]
    duration_ms: float
    status: SpanStatus
    status_description: str
    attributes: Dict[str, Any]
    events: List[SpanEvent]
    links: List[SpanLink]
    resource: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "status_description": self.status_description,
            "attributes": self.attributes,
            "events": [
                {
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "attributes": event.attributes
                }
                for event in self.events
            ],
            "links": [
                {
                    "trace_id": link.trace_id,
                    "span_id": link.span_id,
                    "attributes": link.attributes
                }
                for link in self.links
            ],
            "resource": self.resource
        }


class TraceContext:
    """Manages trace context for distributed tracing"""

    def __init__(self, trace_id: Optional[str] = None, parent_span_id: Optional[str] = None):
        self.trace_id = trace_id or str(uuid.uuid4())
        self.parent_span_id = parent_span_id
        self.current_span_id = str(uuid.uuid4())

    def create_child_context(self) -> "TraceContext":
        """Create child trace context"""
        return TraceContext(
            trace_id=self.trace_id,
            parent_span_id=self.current_span_id
        )


class SpanCollector:
    """Collects and manages OTel spans"""

    def __init__(self):
        self.spans: Dict[str, List[OTelSpan]] = defaultdict(list)
        self._lock = threading.Lock()

    def add_span(self, span: OTelSpan) -> None:
        """Add span to collector"""
        with self._lock:
            self.spans[span.trace_id].append(span)

    def get_trace(self, trace_id: str) -> List[OTelSpan]:
        """Get all spans in a trace"""
        with self._lock:
            return list(self.spans.get(trace_id, []))

    def get_all_spans(self) -> List[OTelSpan]:
        """Get all collected spans"""
        with self._lock:
            return [span for spans in self.spans.values() for span in spans]

    def clear(self) -> None:
        """Clear collected spans"""
        with self._lock:
            self.spans.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get collection statistics"""
        with self._lock:
            all_spans = self.get_all_spans()
            if not all_spans:
                return {
                    "total_spans": 0,
                    "total_traces": 0,
                    "average_duration_ms": 0,
                    "error_rate": 0,
                    "total_tokens": 0
                }

            total_spans = len(all_spans)
            total_traces = len(self.spans)
            avg_duration = sum(s.duration_ms for s in all_spans) / total_spans if total_spans > 0 else 0
            error_count = sum(1 for s in all_spans if s.status == SpanStatus.ERROR)
            error_rate = (error_count / total_spans * 100) if total_spans > 0 else 0
            total_tokens = sum(
                s.attributes.get("ai.token_count", 0) for s in all_spans
            )

            return {
                "total_spans": total_spans,
                "total_traces": total_traces,
                "average_duration_ms": round(avg_duration, 2),
                "error_rate": round(error_rate, 2),
                "total_tokens": total_tokens,
                "spans_by_kind": self._get_spans_by_kind(all_spans),
                "top_spans_by_duration": self._get_top_spans(all_spans, "duration"),
                "top_spans_by_tokens": self._get_top_spans(all_spans, "tokens")
            }

    def _get_spans_by_kind(self, spans: List[OTelSpan]) -> Dict[str, int]:
        """Count spans by kind"""
        counts = defaultdict(int)
        for span in spans:
            counts[span.kind.value] += 1
        return dict(counts)

    def _get_top_spans(self, spans: List[OTelSpan], metric: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top spans by metric"""
        if metric == "duration":
            sorted_spans = sorted(spans, key=lambda s: s.duration_ms, reverse=True)
        elif metric == "tokens":
            sorted_spans = sorted(
                spans,
                key=lambda s: s.attributes.get("ai.token_count", 0),
                reverse=True
            )
        else:
            return []

        return [
            {
                "name": s.name,
                "value": s.duration_ms if metric == "duration" else s.attributes.get("ai.token_count", 0),
                "trace_id": s.trace_id
            }
            for s in sorted_spans[:limit]
        ]


class OTelInstrumentor:
    """OpenTelemetry instrumentation for AI agents"""

    def __init__(self, service_name: str, collector: SpanCollector, 
                 enable_token_counting: bool = True):
        self.service_name = service_name
        self.collector = collector
        self.enable_token_counting = enable_token_counting
        self.resource = {
            "service.name": service_name,
            "service.version": "1.0.0",
            "telemetry.sdk.name": "otel-ai-agent",
            "telemetry.sdk.language": "python",
            "telemetry.sdk.version": "0.1.0"
        }

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        trace_context: Optional[TraceContext] = None,
        links: Optional[List[SpanLink]] = None
    ):
        """Context manager for creating and recording spans"""
        if trace_context is None:
            trace_context = TraceContext()

        span_id = str(uuid.uuid4())
        start_time = time.time()
        events: List[SpanEvent] = []
        status = SpanStatus.OK
        status_description = ""
        span_attributes = attributes or {}

        try:
            yield SpanBuilder(
                trace_id=trace_context.trace_id,
                span_id=span_id,
                parent_span_id=trace_context.parent_span_id,
                name=name,
                events=events,
                attributes=span_attributes
            )
        except Exception as e:
            status = SpanStatus.ERROR
            status_description = str(e)
            events.append(SpanEvent(
                name="exception",
                timestamp=time.time(),
                attributes={
                    "exception.type": type(e).__name__,
                    "exception.message": str(e)
                }
            ))
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            # Auto-record token count if enabled
            if self.enable_token_counting and "ai.token_count" not in span_attributes:
                span_attributes["ai.token_count"] = self._estimate_tokens(name, span_attributes)

            otel_span = OTelSpan(
                trace_id=trace_context.trace_id,
                span_id=span_id,
                parent_span_id=trace_context.parent_span_id,
                name=name,
                kind=kind,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status=status,
                status_description=status_description,
                attributes=span_attributes,
                events=events,
                links=links or [],
                resource=self.resource
            )
            self.collector.add_span(otel_span)

    def _estimate_tokens(self, name: str, attributes: Dict[str, Any]) -> int:
        """Estimate token count for span"""
        base_tokens = len(name) // 4
        text_tokens = 0

        if "ai.prompt" in attributes:
            text_tokens += len(str(attributes["ai.prompt"])) // 4

        if "ai.response" in attributes:
            text_tokens += len(str(attributes["ai.response"])) // 4

        return max(1, base_tokens + text_tokens)


class SpanBuilder:
    """Builder for span attributes within a span context"""

    def __init__(self, trace_id: str, span_id: str, parent_span_id: Optional[str],
                 name: str, events: List[SpanEvent], attributes: Dict[str, Any]):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.name = name
        self.events = events
        self.attributes = attributes

    def set_attribute(self, key: str, value: Any) -> "SpanBuilder":
        """Set span attribute"""
        self.attributes[key] = value
        return self

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> "SpanBuilder":
        """Add event to span"""
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {}
        ))
        return self

    def record_token_usage(self, prompt_tokens: int, completion_tokens: int) -> "SpanBuilder":
        """Record token usage"""
        self.attributes["ai.token_count"] = prompt_tokens + completion_tokens
        self.attributes["ai.prompt_tokens"] = prompt_tokens
        self.attributes["ai.completion_tokens"] = completion_tokens
        self.add_event("token_usage", {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        })
        return self

    def record_cost(self, cost_usd: float, model: str) -> "SpanBuilder":
        """Record API cost"""
        self.attributes["ai.cost_usd"] = cost_usd
        self.attributes["ai.model"] = model
        self.add_event("cost_recorded", {
            "cost_usd": cost_usd,
            "model": model
        })
        return self


class TraceExporter:
    """Exports traces in various formats"""

    def __init__(self, collector: SpanCollector):
        self.collector = collector

    def export_json(self, trace_id: Optional[str] = None, pretty: bool = True) -> str:
        """Export traces as JSON"""
        if trace_id:
            spans = self.collector.get_trace(trace_id)
        else:
            spans = self.collector.get_all_spans()

        spans_data = [span.to_dict() for span in spans]

        if pretty:
            return json.dumps(spans_data, indent=2)
        else:
            return json.dumps(spans_data)

    def export_metrics_json(self) -> str:
        """Export metrics as JSON"""
        stats = self.collector.get_statistics()
        return json.dumps(stats, indent=2)

    def export_grafana_format(self) -> Dict[str, Any]:
        """Export in Grafana-compatible format"""
        stats = self.collector.get_statistics()
        spans = self.collector.get_all_spans()

        return {
            "dashboard": {
                "title": "AI Agent Observability",
                "panels": [
                    {
                        "title": "Span Statistics",
                        "metrics": {
                            "total_spans": stats["total_spans"],
                            "total_traces": stats["total_traces"],
                            "average_duration_ms": stats["average_duration_ms"],
                            "error_rate": stats["error_rate"]
                        }
                    },
                    {
                        "title": "Token Usage",
                        "total_tokens": stats["total_tokens"],
                        "average_tokens_per_span": round(
                            stats["total_tokens"] / max(1, stats["total_spans"]), 2
                        )
                    },
                    {
                        "title": "Top Slow Spans",
                        "data": stats["top_spans_by_duration"]
                    },
                    {
                        "title": "Top Token Consumers",
                        "data": stats["top_spans_by_tokens"]
                    }
                ]
            }
        }

    def export_jaeger_format(self, trace_id: str) -> Dict[str, Any]:
        """Export in Jaeger-compatible format"""
        spans = self.collector.get_trace(trace_id)

        return {
            "traceID": trace_id,
            "spans": [
                {
                    "traceID": s.trace_id,
                    "spanID": s.span_id,
                    "parentSpanID": s.parent_span_id or "",
                    "operationName": s.name,
                    "references": [
                        {
                            "refType": "CHILD_OF",
                            "traceID": s.trace_id,
                            "spanID": s.parent_span_id
                        }
                    ] if s.parent_span_id else [],
                    "startTime": int(s.start_time * 1000000),
                    "duration": int(s.duration_ms * 1000),
                    "tags": [
                        {"key": k, "value": v}
                        for k, v in s.attributes.items()
                    ],
                    "logs": [
                        {
                            "timestamp": int(event.timestamp * 1000000),
                            "fields": [
                                {"key": k, "value": v}
                                for k, v in event.attributes.items()
                            ]
                        }
                        for event in s.events
                    ]
                }
                for s in spans
            ]
        }


class AnomalyDetector:
    """Detects anomalies in span data"""

    def __init__(self, duration_threshold_ms: float = 1000.0,
                 error_rate_threshold: float = 0.1,
                 token_spike_threshold: float = 2.0):
        self.duration_threshold_ms = duration_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.token_spike_threshold = token_spike_threshold
        self.baseline_token_count = 0

    def detect(self, collector: SpanCollector) -> Dict[str, Any]:
        """Detect anomalies in collected spans"""
        spans = collector.get_all_spans()
        anomalies = {
            "slow_spans": [],
            "high_error_rate_traces": [],
            "token_spikes": [],
            "timestamp": datetime.now().isoformat()
        }

        if not spans:
            return anomalies

        # Detect slow spans
        for span in spans:
            if span.duration_ms > self.duration_threshold_ms:
                anomalies["slow_spans"].append({
                    "span_name": span.name,
                    "duration_ms": span.duration_ms,
                    "trace_id": span.trace_id,
                    "threshold_ms": self.duration_threshold_ms
                })

        # Detect high error rate traces
        traces = collector.spans
        for trace_id, trace_spans in traces.items():
            error_count = sum(1 for s in trace_spans if s.status == SpanStatus.ERROR)
            error_rate = error_count / len(trace_spans) if trace_spans else 0
            if error_rate > self.error_rate_threshold:
                anomalies["high_error_rate_traces"].append({
                    "trace_id": trace_id,
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "total_spans": len(trace_spans)
                })

        # Detect token spikes
        token_counts = [s.attributes.get("ai.token_count", 0) for s in spans]
        if token_counts:
            avg_tokens = sum(token_counts) / len(token_counts)
            for span in spans:
                tokens = span.attributes.get("ai.token_count", 0)
                if avg_tokens > 0 and tokens > avg_tokens * self.token_spike_threshold:
                    anomalies["token_spikes"].append({
                        "span_name": span.name,
                        "token_count": tokens,
                        "average_tokens": round(avg_tokens, 2),
                        "spike_multiplier": round(tokens / avg_tokens, 2),
                        "trace_id": span.trace_id
                    })

        return anomalies


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="OpenTelemetry Span Instrumentation for AI Agents"
    )
    parser.add_argument(
        "--service-name",
        type=str,
        default="ai-agent",
        help="Service name for OTel resource"
    )
    parser.add_argument(
        "--enable-token-counting",
        action="store_true",
        default=True,
        help="Enable automatic token counting"
    )
    parser.add_argument(
        "--export-format",
        choices=["json", "metrics", "grafana", "jaeger"],
        default="json",
        help="Export format for traces"
    )
    parser.add_argument(
        "--trace-id",
        type=str,
        help="Specific trace ID to export (for jaeger/json formats)"
    )
    parser.add_argument(
        "--detect-anomalies",
        action="store_true",
        help="Run anomaly detection on collected spans"
    )
    parser.add_argument(
        "--duration-threshold-ms",
        type=float,
        default=1000.0,
        help="Threshold in milliseconds for slow span detection"
    )
    parser.add_argument(
        "--error-rate-threshold",
        type=float,
        default=0.1,
        help="Threshold for error rate detection (0-1)"
    )
    parser.add_argument(
        "--simulate-workload",
        action="store_true",
        help="Simulate AI agent workload with multiple traces"
    )
    parser.add_argument(
        "--num-traces",
        type=int,
        default=5,
        help="Number of traces to generate in simulation"
    )

    args = parser.parse_args()

    # Initialize components
    collector = SpanCollector()
    instrumentor = OTelInstrumentor(args.service_name, collector, args.enable_token_counting)
    exporter = TraceExporter(collector)
    anomaly_detector = AnomalyDetector(
        duration_threshold_ms=args.duration_threshold_ms,
        error_rate_threshold=args.error_rate_threshold
    )

    # Simulate workload if requested
    if args.simulate_workload:
        print(f"Simulating {args.num_traces} traces with AI agent operations...\n", file=sys.stderr)
        simulate_ai_workload(instrumentor, args.num_traces)

    # Export based on format
    if args.export_format == "json":
        output = exporter.export_json(trace_id=args.trace_id, pretty=True)
        print(output)
    elif args.export_format == "metrics":
        output = exporter.export_metrics_json()
        print(output)
    elif args.export_format == "grafana":
        output = exporter.export_grafana_format()
        print(json.dumps(output, indent=2))
    elif args.export_format == "jaeger":
        if not args.trace_id and collector.get_all_spans():
            args.trace_id = collector.get_all_spans()[0].trace_id
        if args.trace_id:
            output = exporter.export_jaeger_format(args.trace_id)
            print(json.dumps(output, indent=2))
        else:
            print("No trace ID available for Jaeger export", file=sys.stderr)
            sys.exit(1)

    # Run anomaly detection if requested
    if args.detect_anomalies:
        print("\n" + "="*50, file=sys.stderr)
        print("ANOMALY DETECTION RESULTS", file=sys.stderr)
        print("="*50, file=sys.stderr)
        anomalies = anomaly_detector.detect(collector)
        print(json.dumps(anomalies, indent=2), file=sys.stderr)


def simulate_ai_workload(instrumentor: OTelInstrumentor, num_traces: int):
    """Simulate realistic AI agent workload"""
    models = ["gpt-4", "gpt-3.5-turbo", "claude-2", "palm-2"]
    operations = [
        ("vector_search", 10, 50),
        ("llm_inference", 100, 500),
        ("embedding_generation", 20, 100),
        ("data_retrieval", 5, 30),
        ("response_formatting", 15, 75)
    ]

    for trace_num in range(num_traces):
        trace_context = TraceContext()
        model = random.choice(models)

        # Main agent operation span
        with instrumentor.span(
            "agent_operation",
            kind=SpanKind.INTERNAL,
            attributes={"ai.model": model},
            trace_context=trace_context
        ) as main_span:
            main_span.set_attribute("agent.iteration", trace_num)
            main_span.add_event("agent_started", {"iteration": trace_num})

            # Simulate sub-operations
            for op_name, min_tokens, max_tokens in random.sample(operations, k=random.randint(2, 4)):
                child_context = trace_context.create_child_context()
                tokens = random.randint(min_tokens, max_tokens)
                cost = tokens * 0.0001

                with instrumentor.span(
                    op_name,
                    kind=SpanKind.CLIENT,
                    attributes={"ai.model": model},
                    trace_context=child_context
                ) as op_span:
                    op_span.record_token_usage(
                        prompt_tokens=tokens // 2,
                        completion_tokens=tokens // 2
                    )
                    op_span.record_cost(cost, model)
                    time.sleep(random.uniform(0.01, 0.1))

            main_span.add_event("agent_completed", {"trace_id": trace_context.trace_id})


if __name__ == "__main__":
    main()