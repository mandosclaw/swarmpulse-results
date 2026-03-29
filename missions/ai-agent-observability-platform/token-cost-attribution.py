#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Token cost attribution
# Mission: AI Agent Observability Platform
# Agent:   @quinn
# Date:    2026-03-29T13:13:58.466Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Token cost attribution
MISSION: AI Agent Observability Platform
AGENT: @quinn
DATE: 2025-01-17

Per-span token usage tracking with waterfall view showing which tool calls
consumed the most tokens. Integrates with OpenTelemetry-style span data structure.
"""

import json
import argparse
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TokenModel(Enum):
    """Token pricing models for different LLM providers."""
    GPT4_TURBO = {"input": 0.01, "output": 0.03}
    GPT35_TURBO = {"input": 0.0005, "output": 0.0015}
    CLAUDE3_OPUS = {"input": 0.015, "output": 0.075}
    CLAUDE3_SONNET = {"input": 0.003, "output": 0.015}
    LLAMA2_70B = {"input": 0.001, "output": 0.001}


@dataclass
class TokenMetrics:
    """Token usage metrics for a span."""
    input_tokens: int = 0
    output_tokens: int = 0
    model: TokenModel = TokenModel.GPT4_TURBO

    def total_tokens(self) -> int:
        """Total tokens consumed."""
        return self.input_tokens + self.output_tokens

    def cost(self) -> float:
        """Calculate USD cost of tokens."""
        rates = self.model.value
        input_cost = self.input_tokens * (rates["input"] / 1000)
        output_cost = self.output_tokens * (rates["output"] / 1000)
        return round(input_cost + output_cost, 6)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens(),
            "model": self.model.name,
            "cost_usd": self.cost(),
        }


@dataclass
class Span:
    """OpenTelemetry-style span with token cost attribution."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time_ms: float
    end_time_ms: float
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List["Span"] = field(default_factory=list)

    def duration_ms(self) -> float:
        """Duration of span in milliseconds."""
        return self.end_time_ms - self.start_time_ms

    def is_tool_call(self) -> bool:
        """Check if span represents a tool call."""
        return self.attributes.get("span_type") == "tool_call"

    def total_child_cost(self) -> float:
        """Sum cost of all descendant spans."""
        total = self.token_metrics.cost()
        for child in self.children:
            total += child.total_child_cost()
        return total

    def total_child_tokens(self) -> int:
        """Sum tokens of all descendant spans."""
        total = self.token_metrics.total_tokens()
        for child in self.children:
            total += child.total_child_tokens()
        return total

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "duration_ms": self.duration_ms(),
            "start_time_ms": self.start_time_ms,
            "end_time_ms": self.end_time_ms,
            "token_metrics": self.token_metrics.to_dict(),
            "attributes": self.attributes,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class TraceAnalysis:
    """Analysis results for a complete trace."""
    trace_id: str
    root_span: Span
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    span_count: int = 0
    most_expensive_tool: Optional[Dict[str, Any]] = None
    latency_bottlenecks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            "trace_id": self.trace_id,
            "total_cost_usd": self.total_cost_usd,
            "total_tokens": self.total_tokens,
            "span_count": self.span_count,
            "most_expensive_tool": self.most_expensive_tool,
            "latency_bottlenecks": self.latency_bottlenecks,
            "root_span": self.root_span.to_dict(),
        }


class TokenCostAnalyzer:
    """Analyze token costs and attribution across trace spans."""

    def __init__(self, latency_threshold_ms: float = 500.0):
        """Initialize analyzer with latency threshold for bottleneck detection."""
        self.latency_threshold_ms = latency_threshold_ms
        self.traces: Dict[str, Span] = {}

    def add_span(
        self,
        span_id: str,
        trace_id: str,
        operation_name: str,
        start_time_ms: float,
        end_time_ms: float,
        input_tokens: int,
        output_tokens: int,
        parent_span_id: Optional[str] = None,
        model: TokenModel = TokenModel.GPT4_TURBO,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """Add a span to the trace."""
        token_metrics = TokenMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            token_metrics=token_metrics,
            attributes=attributes or {},
        )

        if trace_id not in self.traces:
            if parent_span_id is None:
                self.traces[trace_id] = span
            else:
                self.traces[trace_id] = None

        if parent_span_id is not None:
            parent = self._find_span(trace_id, parent_span_id)
            if parent:
                parent.children.append(span)
        elif trace_id not in self.traces or self.traces[trace_id] is None:
            self.traces[trace_id] = span

        return span

    def _find_span(self, trace_id: str, span_id: str) -> Optional[Span]:
        """Recursively find a span by ID in a trace."""
        if trace_id not in self.traces:
            return None

        root = self.traces[trace_id]
        if root is None:
            return None

        return self._search_span_tree(root, span_id)

    def _search_span_tree(self, span: Span, span_id: str) -> Optional[Span]:
        """Recursively search for span in tree."""
        if span.span_id == span_id:
            return span

        for child in span.children:
            result = self._search_span_tree(child, span_id)
            if result:
                return result

        return None

    def _collect_all_spans(self, span: Span) -> List[Span]:
        """Recursively collect all spans in tree."""
        spans = [span]
        for child in span.children:
            spans.extend(self._collect_all_spans(child))
        return spans

    def _find_bottlenecks(self, spans: List[Span]) -> List[Dict[str, Any]]:
        """Identify spans exceeding latency threshold."""
        bottlenecks = []
        for span in spans:
            if span.duration_ms() > self.latency_threshold_ms:
                bottlenecks.append({
                    "span_id": span.span_id,
                    "operation_name": span.operation_name,
                    "duration_ms": span.duration_ms(),
                    "threshold_ms": self.latency_threshold_ms,
                    "exceeded_by_ms": span.duration_ms() - self.latency_threshold_ms,
                })
        return sorted(bottlenecks, key=lambda x: x["duration_ms"], reverse=True)

    def _find_most_expensive_tool(
        self, spans: List[Span]
    ) -> Optional[Dict[str, Any]]:
        """Find the tool call with highest token cost."""
        tool_spans = [s for s in spans if s.is_tool_call()]
        if not tool_spans:
            return None

        most_expensive = max(tool_spans, key=lambda s: s.token_metrics.cost())
        return {
            "span_id": most_expensive.span_id,
            "operation_name": most_expensive.operation_name,
            "tool_name": most_expensive.attributes.get("tool_name", "unknown"),
            "input_tokens": most_expensive.token_metrics.input_tokens,
            "output_tokens": most_expensive.token_metrics.output_tokens,
            "total_tokens": most_expensive.token_metrics.total_tokens(),
            "cost_usd": most_expensive.token_metrics.cost(),
        }

    def analyze_trace(self, trace_id: str) -> Optional[TraceAnalysis]:
        """Analyze a complete trace for token costs and bottlenecks."""
        if trace_id not in self.traces:
            return None

        root_span = self.traces[trace_id]
        if root_span is None:
            return None

        all_spans = self._collect_all_spans(root_span)
        total_cost = sum(s.token_metrics.cost() for s in all_spans)
        total_tokens = sum(s.token_metrics.total_tokens() for s in all_spans)
        bottlenecks = self._find_bottlenecks(all_spans)
        most_expensive_tool = self._find_most_expensive_tool(all_spans)

        analysis = TraceAnalysis(
            trace_id=trace_id,
            root_span=root_span,
            total_cost_usd=round(total_cost, 6),
            total_tokens=total_tokens,
            span_count=len(all_spans),
            most_expensive_tool=most_expensive_tool,
            latency_bottlenecks=bottlenecks,
        )

        return analysis

    def generate_waterfall_view(self, trace_id: str) -> str:
        """Generate a text waterfall view of token costs."""
        if trace_id not in self.traces:
            return f"Trace {trace_id} not found"

        root_span = self.traces[trace_id]
        if root_span is None:
            return f"Trace {trace_id} root span not found"

        lines = [
            "Token Cost Waterfall View",
            "=" * 100,
            f"Trace ID: {trace_id}",
            "",
        ]

        self._add_waterfall_lines(root_span, lines, 0)

        return "\n".join(lines)

    def _add_waterfall_lines(
        self, span: Span, lines: List[str], depth: int
    ) -> None:
        """Recursively add waterfall view lines."""
        indent = "  " * depth
        duration = span.duration_ms()
        tokens = span.token_metrics.total_tokens()
        cost = span.token_metrics.cost()
        tool_indicator = " [TOOL]" if span.is_tool_call() else ""

        lines.append(
            f"{indent}├─ {span.operation_name}{tool_indicator}"
            f" | {duration:.1f}ms | {tokens} tokens | ${cost:.6f}"
        )

        if span.attributes:
            attr_str = " | ".join(
                f"{k}={v}" for k, v in span.attributes.items()
                if k != "span_type"
            )
            if attr_str:
                lines.append(f"{indent}│  └─ attrs: {attr_str}")

        for i, child in enumerate(span.children):
            is_last = i == len(span.children) - 1
            self._add_waterfall_lines(child, lines, depth + 1)

    def export_trace_json(self, trace_id: str) -> str:
        """Export trace as JSON."""
        analysis = self.analyze_trace(trace_id)
        if analysis is None:
            return json.dumps({"error": f"Trace {trace_id} not found"})

        return json.dumps(analysis.to_dict(), indent=2)


def create_sample_traces(analyzer: TokenCostAnalyzer) -> None:
    """Create sample trace data for demonstration."""
    trace_id_1 = "trace-001-user-query"

    root_span_id = "span-root-001"
    analyzer.add_span(
        span_id=root_span_id,
        trace_id=trace_id_1,
        operation_name="process_user_query",
        start_time_ms=0.0,
        end_time_ms=2500.0,
        input_tokens=150,
        output_tokens=200,
        parent_span_id=None,
        attributes={"span_type": "agent_step"},
    )

    llm_call_span_id = "span-llm-001"
    analyzer.add_span(
        span_id=llm_call_span_id,
        trace_id=trace_id_1,
        operation_name="llm_generate",
        start_time_ms=50.0,
        end_time_ms=300.0,
        input_tokens=150,
        output_tokens=80,
        parent_span_id=root_span_id,
        model=TokenModel.GPT4_TURBO,
        attributes={"span_type": "llm_call"},
    )

    tool_call_1_span_id = "span-tool-001"
    analyzer.add_span(
        span_id=tool_call_1_span_id,
        trace_id=trace_id_1,
        operation_name="search_web",
        start_time_ms=350.0,
        end_time_ms=1200.0,
        input_tokens=200,
        output_tokens=1500,
        parent_span_id=root_span_id,
        model=TokenModel.GPT4_TURBO,
        attributes={"span_type": "tool_call", "tool_name": "web_search"},
    )

    tool_call_2_span_id = "span-tool-002"
    analyzer.add_span(
        span_id=tool_call_2_span_id,
        trace_id=trace_id_1,
        operation_name="analyze_sentiment",
        start_time_ms=1250.0,
        end_time_ms=1850.0,
        input_tokens=800,
        output_tokens=300,
        parent_span_id=root_span_id,
        model=TokenModel.CLAUDE3_SONNET,
        attributes={"span_type": "tool_call", "tool_name": "sentiment_analyzer"},
    )

    final_llm_span_id = "span-llm-final"
    analyzer.add_span(
        span_id=final_llm_span_id,
        trace_