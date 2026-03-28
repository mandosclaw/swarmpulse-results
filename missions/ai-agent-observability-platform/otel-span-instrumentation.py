#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OTel span instrumentation
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-28T21:58:18.476Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: OTel span instrumentation - Auto-instrument popular frameworks (LangChain, CrewAI, openclaw). Trace ID propagation.
MISSION: AI Agent Observability Platform
AGENT: @sue
DATE: 2024
"""

import argparse
import json
import sys
import time
import uuid
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from enum import Enum
import traceback
import hashlib


class SpanKind(Enum):
    """OpenTelemetry span kinds."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class SpanStatus(Enum):
    """OpenTelemetry span status."""
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
class Span:
    """OpenTelemetry-compatible span implementation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: float
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    token_count: int = 0
    token_cost: float = 0.0
    error_message: Optional[str] = None

    def duration_ms(self) -> float:
        """Calculate span duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
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
                    "name": event.name,
                    "timestamp": event.timestamp,
                    "attributes": event.attributes,
                }
                for event in self.events
            ],
            "links": [
                {
                    "traceId": link.trace_id,
                    "spanId": link.span_id,
                    "attributes": link.attributes,
                }
                for link in self.links
            ],
            "tokenCount": self.token_count,
            "tokenCost": self.token_cost,
            "errorMessage": self.error_message,
        }


class TraceContext:
    """Manages trace context and propagation."""

    _trace_stack: List[Tuple[str, str]] = []

    @classmethod
    def get_current_trace_id(cls) -> str:
        """Get current trace ID from context."""
        if cls._trace_stack:
            return cls._trace_stack[-1][0]
        return ""

    @classmethod
    def get_current_span_id(cls) -> str:
        """Get current span ID from context."""
        if cls._trace_stack:
            return cls._trace_stack[-1][1]
        return ""

    @classmethod
    def push_span(cls, trace_id: str, span_id: str) -> None:
        """Push a span onto the context stack."""
        cls._trace_stack.append((trace_id, span_id))

    @classmethod
    def pop_span(cls) -> Optional[Tuple[str, str]]:
        """Pop a span from the context stack."""
        if cls._trace_stack:
            return cls._trace_stack.pop()
        return None

    @classmethod
    def get_trace_header(cls) -> str:
        """Generate W3C Trace Context header value."""
        trace_id = cls.get_current_trace_id()
        span_id = cls.get_current_span_id()
        if trace_id and span_id:
            return f"{trace_id}-{span_id}-01"
        return ""


class SpanCollector:
    """Collects and manages spans."""

    def __init__(self):
        self.spans: Dict[str, List[Span]] = {}

    def add_span(self, span: Span) -> None:
        """Add a span to the collection."""
        if span.trace_id not in self.spans:
            self.spans[span.trace_id] = []
        self.spans[span.trace_id].append(span)

    def get_spans_by_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace ID."""
        return self.spans.get(trace_id, [])

    def get_all_spans(self) -> List[Span]:
        """Get all collected spans."""
        all_spans = []
        for spans in self.spans.values():
            all_spans.extend(spans)
        return all_spans

    def export_json(self) -> str:
        """Export all spans as JSON."""
        spans_data = []
        for spans in self.spans.values():
            for span in spans:
                spans_data.append(span.to_dict())
        return json.dumps(spans_data, indent=2)


class InjectionDetector:
    """Detects potential prompt injection attempts in traces."""

    INJECTION_PATTERNS = [
        r"ignore\s+(?:previous|prior)\s+(?:instructions|prompts?)",
        r"(?:forget|disregard)\s+(?:everything|all)\s+(?:before|prior)",
        r"(?:system|admin)\s+(?:override|mode|command|prompt)",
        r"(?:execute|run)\s+(?:code|script|command)",
        r"(?:sql|nosql|command)\s+injection",
        r"(?:jailbreak|bypass|circumvent|escape)",
        r"(?:hidden|secret|internal)\s+(?:instruction|prompt|directive)",
        r"(?:pretend|roleplay|simulate|act)\s+as\s+(?:system|admin|root)",
        r"(?:do\s+)?(?:not\s+)?(?:remember|recall|consider)\s+",
    ]

    @classmethod
    def detect(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Detect potential injection attempts.
        Returns (is_suspicious, list of matched patterns).
        """
        if not text:
            return False, []

        text_lower = text.lower()
        matches = []

        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                matches.append(pattern)

        is_suspicious = len(matches) > 0
        return is_suspicious, matches


class TokenEstimator:
    """Estimates token counts and costs."""

    COST_PER_1K_INPUT = 0.0005
    COST_PER_1K_OUTPUT = 0.0