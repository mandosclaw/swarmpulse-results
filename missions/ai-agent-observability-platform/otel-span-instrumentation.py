#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OTel span instrumentation
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-28T22:02:22.278Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: OTel span instrumentation
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2024
Description: OpenTelemetry span instrumentation for distributed tracing,
token cost attribution, and anomaly detection in AI agent networks.
"""

import json
import time
import uuid
import argparse
import random
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import threading
import queue


class SpanKind(Enum):
    """OpenTelemetry span kinds."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class SpanStatus(Enum):
    """Span execution status."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanEvent:
    """Represents an event within a span."""
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    """Represents a link to another span."""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OTelSpan:
    """OpenTelemetry span representation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float]
    status: SpanStatus
    attributes: Dict[str, Any]
    events: List[SpanEvent]
    links: List[SpanLink]
    resource_attributes: Dict[str, Any]
    token_count: int = 0
    token_cost: float = 0.0
    
    def duration_ms(self) -> float:
        """Calculate span duration in milliseconds."""
        if self.end_time is None:
            return -1.0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "name": self.name,
            "kind": self.kind.value,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "durationMs": self.duration_ms(),
            "status": self.status.value,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes
                }
                for e in self.events
            ],
            "links": [
                {
                    "traceId": l.trace_id,
                    "spanId": l.span_id,
                    "attributes": l.attributes
                }
                for l in self.links
            ],
            "resourceAttributes": self.resource_attributes,
            "tokenCount": self.token_count,
            "tokenCost": self.token_cost
        }


class SpanContext:
    """Manages span context for distributed tracing."""
    
    def __init__(self):
        self._trace_id = str(uuid.uuid4())
        self._span_id_counter = 0
        self._span_stack: List[OTelSpan] = []
        self._lock = threading.Lock()
    
    def generate_span_id(self) -> str:
        """Generate unique span ID."""
        with self._lock:
            self._span_id_counter += 1
            return f"{self._span_id_counter:016x}"
    
    def get_trace_id(self) -> str:
        """Get current trace ID."""
        return self._trace_id
    
    def get_current_span_id(self) -> Optional[str]:
        """Get current span ID."""
        if self._span_stack:
            return self._span_stack[-1].span_id
        return None
    
    def push_span(self, span: OTelSpan) -> None:
        """Push span onto stack."""
        with self._lock:
            self._span_stack.append(span)
    
    def pop_span(self) -> Optional[OTelSpan]:
        """Pop span from stack."""
        with self._lock:
            if self._span_stack:
                return self._span_stack.pop()
        return None
    
    def reset(self) -> None:
        """Reset context for new trace."""
        with self._lock:
            self._trace_id = str(uuid.uuid4())
            self._span_id_counter = 0
            self._span_stack = []


class TokenCostCalculator:
    """Calculates token costs for LLM operations."""
    
    def __init__(self, input_cost_per_1k: float = 0.0005, output_cost_per_1k: float = 0.0015):
        self.input_cost_per_1k = input_cost_per_1k
        self.output_cost_per_1k = output_cost_per_1k
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough approximation)."""
        return len(text) // 4 + 1
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on input and output tokens."""
        input_cost = (input_tokens / 1000) * self.input_cost_per_1k
        output_cost = (output_tokens / 1000) * self.output_cost_per_1k
        return input_cost + output_cost


class AnomalyDetector:
    """Detects anomalies in span metrics."""
    
    def __init__(self, window_size: int = 100, threshold_sigma: float = 2.0):
        self.window_size = window_size
        self.threshold_sigma = threshold_sigma
        self.metrics: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """Record a metric value."""
        with self._lock:
            self.metrics[metric_name].append(value)
            if len(self.metrics[metric_name]) > self.window_size:
                self.metrics[metric_name].pop(0)
    
    def detect_anomaly(self, metric_name: str, value: float) -> bool:
        """Detect if a value is anomalous."""
        with self._lock:
            if metric_name not in self.metrics or len(self.metrics[metric_name]) < 10:
                return False
            
            values = self.metrics[metric_name]
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            stddev = variance ** 0.5
            
            if stddev == 0:
                return False
            
            z_score = abs(value - mean) / stddev
            return z_score > self.threshold_sigma
    
    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric."""
        with self._lock:
            if metric_name not in self.metrics or not self.metrics[metric_name]:
                return {"count": 0}
            
            values = self.metrics[metric_name]
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            stddev = variance ** 0.5
            
            return {
                "count": len(values),
                "mean": mean,
                "stddev": stddev,
                "min": min(values),
                "max": max(values)
            }


class SpanExporter:
    """Exports spans to various backends."""
    
    def __init__(self, queue_size: int = 1000):
        self.queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self.exported_spans: List[OTelSpan] = []
        self._lock = threading.Lock()
    
    def export(self, span: OTelSpan) -> None:
        """Export a span."""
        try:
            self.queue.put_nowait(span)
        except queue.Full:
            pass
        
        with self._lock:
            self.exported_spans.append(span)
    
    def get_exported_spans(self) -> List[OTelSpan]:
        """Get all exported spans."""
        with self._lock:
            return self.exported_spans.copy()
    
    def flush(self) -> List[Dict[str, Any]]:
        """Flush and return all pending spans as dictionaries."""
        spans = []
        while not self.queue.empty():
            try:
                span = self.queue.get_nowait()
                spans.append(span.to_dict())
            except queue.Empty:
                break
        return spans


class SpanProcessor:
    """Processes and manages spans."""
    
    def __init__(self, exporter: Optional[SpanExporter] = None,
                 cost_calculator: Optional[TokenCostCalculator] = None,
                 anomaly_detector: Optional[AnomalyDetector] = None):
        self.exporter = exporter or SpanExporter()
        self.cost_calculator = cost_calculator or TokenCostCalculator()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()
        self.spans: Dict[str, OTelSpan] = {}
        self._lock = threading.Lock()
    
    def create_span(self,
                    name: str,
                    kind: SpanKind = SpanKind.INTERNAL,
                    context: Optional[SpanContext] = None,
                    attributes: Optional[Dict[str, Any]] = None,
                    resource_attributes: Optional[Dict[str, Any]] = None) -> OTelSpan:
        """Create a new span."""
        if context is None:
            context = SpanContext()
        
        trace_id = context.get_trace_id()
        span_id = context.generate_span_id()
        parent_span_id = context.get_current_span_id()
        
        span = OTelSpan(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            kind=kind,
            start_time=time.time(),
            end_time=None,
            status=SpanStatus.UNSET,
            attributes=attributes or {},
            events=[],
            links=[],
            resource_attributes=resource_attributes or {"service.name": "ai-agent"}
        )
        
        with self._lock:
            self.spans[span_id] = span
        
        context.push_span(span)
        return span
    
    def end_span(self, span: OTelSpan, status: SpanStatus = SpanStatus.OK) -> None:
        """End a span and record metrics."""
        span.end_time = time.time()
        span.status = status
        
        duration = span.duration_ms()
        self.anomaly_detector.record_metric("span_duration_ms", duration)
        
        if span.token_count > 0:
            self.anomaly_detector.record_metric("token_count", span.token_count)
            self.anomaly_detector.record_metric("token_cost", span.token_cost)
        
        self.exporter.export(span)
    
    def add_event(self, span: OTelSpan, event_name: str,
                  attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to a span."""
        event = SpanEvent(
            name=event_name,
            timestamp=time.time(),
            attributes=attributes or {}
        )
        span.events.append(event)
    
    def add_link(self, span: OTelSpan, link_trace_id: str, link_span_id: str,
                 attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add a link to another span."""
        link = SpanLink(
            trace_id=link_trace_id,
            span_id=link_span_id,
            attributes=attributes or {}
        )
        span.links.append(link)
    
    def set_token_cost(self, span: OTelSpan, input_tokens: int, output_tokens: int) -> None:
        """Set token count and cost for a span."""
        span.token_count = input_tokens + output_tokens
        span.token_cost = self.cost_calculator.calculate_cost(input_tokens, output_tokens)
    
    def get_span_metrics(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific span."""
        with self._lock:
            span = self.spans.get(span_id)
        
        if span is None:
            return None
        
        return {
            "span_id": span.span_id,
            "name": span.name,
            "duration_ms": span.duration_ms(),
            "token_count": span.token_count,
            "token_cost": span.token_cost,
            "status": span.status.value
        }
    
    def get_trace_spans(self, trace_id: str) -> List[OTelSpan]:
        """Get all spans in a trace."""
        with self._lock:
            return [span for span in self.spans.values() if span.trace_id == trace_id]


class SpanInstrument:
    """High-level API for span instrumentation."""
    
    def __init__(self, processor: Optional[SpanProcessor] = None):
        self.processor = processor or SpanProcessor()
        self.context = SpanContext()
    
    def start_span(self, name: str, kind: SpanKind = SpanKind.INTERNAL,
                   attributes: Optional[Dict[str, Any]] = None) -> OTelSpan:
        """Start a new span."""
        return self.processor.create_span(
            name=name,
            kind=kind,
            context=self.context,
            attributes=attributes
        )
    
    def end_span(self, span: OTelSpan, status: SpanStatus = SpanStatus.OK,
                 error: Optional[Exception] = None) -> None:
        """End a span with optional error."""
        if error is not None:
            span.status = SpanStatus.ERROR
            span.attributes["error.type"] = type(error).__name__
            span.attributes["error.message"] = str(error)
        else:
            span.status = status
        
        self.processor.end_span(span, span.status)
        self.context.pop_span()
    
    def record_token_usage(self, span: OTelSpan, input_tokens: int, output_tokens: int) -> None:
        """Record token usage for a span."""
        self.processor.set_token_cost(span, input_tokens, output_tokens)
    
    def add_event(self, span: OTelSpan, event_name: str,
                  attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the current span."""
        self.processor