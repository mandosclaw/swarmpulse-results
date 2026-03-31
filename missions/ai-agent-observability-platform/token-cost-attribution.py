#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Token cost attribution
# Mission: AI Agent Observability Platform
# Agent:   @quinn
# Date:    2026-03-31T18:42:49.232Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Token cost attribution
Mission: AI Agent Observability Platform
Agent: @quinn
Date: 2024

Per-span token usage with waterfall view showing which tool calls cost the most.
OpenTelemetry-native observability for LLM/agent workloads.
"""

import json
import argparse
import sys
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import uuid


class TokenModel(Enum):
    """Supported token cost models."""
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"
    CLAUDE_3_OPUS = "claude-3-opus"
    CLAUDE_3_SONNET = "claude-3-sonnet"


TOKEN_COSTS = {
    TokenModel.GPT_4_TURBO: {"input": 0.01, "output": 0.03},
    TokenModel.GPT_35_TURBO: {"input": 0.0005, "output": 0.0015},
    TokenModel.CLAUDE_3_OPUS: {"input": 0.015, "output": 0.075},
    TokenModel.CLAUDE_3_SONNET: {"input": 0.003, "output": 0.015},
}


@dataclass
class TokenMetrics:
    """Token usage metrics for a span."""
    input_tokens: int
    output_tokens: int
    model: TokenModel
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def calculate_cost(self) -> float:
        """Calculate cost in USD for this token usage."""
        costs = TOKEN_COSTS[self.model]
        input_cost = self.input_tokens * costs["input"] / 1000
        output_cost = self.output_tokens * costs["output"] / 1000
        return input_cost + output_cost


@dataclass
class Span:
    """OpenTelemetry-style span with token attribution."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    span_type: str
    start_time: float
    end_time: float
    duration_ms: float
    token_metrics: Optional[TokenMetrics] = None
    attributes: Dict = field(default_factory=dict)
    
    @property
    def cost_usd(self) -> float:
        """Total cost for this span in USD."""
        if self.token_metrics:
            return self.token_metrics.calculate_cost()
        return 0.0
    
    @property
    def tokens_per_ms(self) -> float:
        """Token throughput metric."""
        if self.duration_ms > 0 and self.token_metrics:
            return self.token_metrics.total_tokens / self.duration_ms
        return 0.0


@dataclass
class TraceAnalysis:
    """Analysis results for a complete trace."""
    trace_id: str
    root_span: Span
    all_spans: List[Span]
    total_cost_usd: float
    total_tokens: int
    total_duration_ms: float
    span_tree: Dict
    cost_by_operation: Dict[str, float]
    cost_by_type: Dict[str, float]


class TokenCostAttributor:
    """Attributes token costs to spans in OpenTelemetry traces."""
    
    def __init__(self, default_model: TokenModel = TokenModel.GPT_4_TURBO):
        self.default_model = default_model
        self.spans: Dict[str, Span] = {}
        self.traces: Dict[str, List[Span]] = {}
    
    def add_span(
        self,
        trace_id: str,
        operation_name: str,
        span_type: str,
        input_tokens: int,
        output_tokens: int,
        start_time: float,
        end_time: float,
        parent_span_id: Optional[str] = None,
        model: Optional[TokenModel] = None,
        attributes: Optional[Dict] = None,
    ) -> Span:
        """Add a span with token metrics."""
        span_id = str(uuid.uuid4())
        duration_ms = (end_time - start_time) * 1000
        
        token_metrics = TokenMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or self.default_model,
        )
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            span_type=span_type,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            token_metrics=token_metrics,
            attributes=attributes or {},
        )
        
        self.spans[span_id] = span
        
        if trace_id not in self.traces:
            self.traces[trace_id] = []
        self.traces[trace_id].append(span)
        
        return span
    
    def build_span_tree(self, spans: List[Span]) -> Dict:
        """Build hierarchical tree of spans."""
        spans_by_id = {s.span_id: s for s in spans}
        tree = {}
        
        for span in spans:
            if span.parent_span_id is None:
                tree[span.span_id] = {
                    "span": span,
                    "children": [],
                }
        
        def add_children(parent_id: str, tree_node: Dict):
            for span in spans:
                if span.parent_span_id == parent_id:
                    child_node = {
                        "span": span,
                        "children": [],
                    }
                    tree_node["children"].append(child_node)
                    add_children(span.span_id, child_node)
        
        for parent_id in list(tree.keys()):
            add_children(parent_id, tree[parent_id])
        
        return tree
    
    def analyze_trace(self, trace_id: str) -> TraceAnalysis:
        """Analyze a complete trace."""
        spans = self.traces.get(trace_id, [])
        
        if not spans:
            raise ValueError(f"No spans found for trace {trace_id}")
        
        root_spans = [s for s in spans if s.parent_span_id is None]
        if len(root_spans) != 1:
            raise ValueError(f"Expected exactly one root span, found {len(root_spans)}")
        
        root_span = root_spans[0]
        
        total_cost = sum(s.cost_usd for s in spans)
        total_tokens = sum(
            (s.token_metrics.total_tokens if s.token_metrics else 0)
            for s in spans
        )
        total_duration = max(s.end_time for s in spans) - min(s.start_time for s in spans)
        total_duration_ms = total_duration * 1000
        
        cost_by_operation = {}
        for span in spans:
            key = span.operation_name
            cost_by_operation[key] = cost_by_operation.get(key, 0) + span.cost_usd
        
        cost_by_type = {}
        for span in spans:
            key = span.span_type
            cost_by_type[key] = cost_by_type.get(key, 0) + span.cost_usd
        
        span_tree = self.build_span_tree(spans)
        
        return TraceAnalysis(
            trace_id=trace_id,
            root_span=root_span,
            all_spans=spans,
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_duration_ms=total_duration_ms,
            span_tree=span_tree,
            cost_by_operation=cost_by_operation,
            cost_by_type=cost_by_type,
        )
    
    def waterfall_view(self, trace_id: str) -> str:
        """Generate ASCII waterfall view of spans with costs."""
        spans = self.traces.get(trace_id, [])
        if not spans:
            return f"No spans found for trace {trace_id}"
        
        min_time = min(s.start_time for s in spans)
        spans_sorted = sorted(spans, key=lambda s: s.start_time)
        
        lines = []
        lines.append("=" * 120)
        lines.append(f"WATERFALL VIEW - Trace: {trace_id}")
        lines.append("=" * 120)
        lines.append(
            f"{'Operation':<25} {'Type':<15} {'Duration':<12} {'Tokens':<10} "
            f"{'Cost (USD)':<12} {'Timeline':<40}"
        )
        lines.append("-" * 120)
        
        for span in spans_sorted:
            relative_start = (span.start_time - min_time) * 1000
            bar_length = max(1, int(span.duration_ms / 10))
            bar = "█" * min(bar_length, 20)
            
            tokens = (
                f"{span.token_metrics.total_tokens}"
                if span.token_metrics
                else "0"
            )
            
            line = (
                f"{span.operation_name:<25} "
                f"{span.span_type:<15} "
                f"{span.duration_ms:>10.1f}ms "
                f"{tokens:>8} "
                f"${span.cost_usd:>10.6f} "
                f"{bar:<40}"
            )
            lines.append(line)
        
        lines.append("=" * 120)
        return "\n".join(lines)
    
    def json_report(self, trace_id: str) -> str:
        """Generate JSON report of trace analysis."""
        analysis = self.analyze_trace(trace_id)
        
        report = {
            "trace_id": analysis.trace_id,
            "summary": {
                "total_cost_usd": round(analysis.total_cost_usd, 6),
                "total_tokens": analysis.total_tokens,
                "total_duration_ms": round(analysis.total_duration_ms, 2),
                "span_count": len(analysis.all_spans),
            },
            "cost_breakdown": {
                "by_operation": {
                    k: round(v, 6)
                    for k, v in analysis.cost_by_operation.items()
                },
                "by_type": {
                    k: round(v, 6)
                    for k, v in analysis.cost_by_type.items()
                },
            },
            "spans": [
                {
                    "span_id": s.span_id,
                    "parent_span_id": s.parent_span_id,
                    "operation_name": s.operation_name,
                    "span_type": s.span_type,
                    "duration_ms": round(s.duration_ms, 2),
                    "cost_usd": round(s.cost_usd, 6),
                    "tokens": {
                        "input": s.token_metrics.input_tokens if s.token_metrics else 0,
                        "output": s.token_metrics.output_tokens if s.token_metrics else 0,
                        "total": s.token_metrics.total_tokens if s.token_metrics else 0,
                    } if s.token_metrics else None,
                    "model": s.token_metrics.model.value if s.token_metrics else None,
                }
                for s in sorted(analysis.all_spans, key=lambda s: s.start_time)
            ],
        }
        
        return json.dumps(report, indent=2)


def generate_sample_trace() -> Tuple[str, TokenCostAttributor]:
    """Generate a sample trace with realistic agent tool call pattern."""
    attributor = TokenCostAttributor()
    trace_id = str(uuid.uuid4())
    
    base_time = 1000.0
    
    root_span = attributor.add_span(
        trace_id=trace_id,
        operation_name="agent.run",
        span_type="agent",
        input_tokens=150,
        output_tokens=50,
        start_time=base_time,
        end_time=base_time + 5.0,
        model=TokenModel.GPT_4_TURBO,
    )
    
    search_span = attributor.add_span(
        trace_id=trace_id,
        operation_name="tool.web_search",
        span_type="tool",
        input_tokens=100,
        output_tokens=500,
        start_time=base_time + 0.5,
        end_time=base_time + 1.5,
        parent_span_id=root_span.span_id,
        model=TokenModel.GPT_4_TURBO,
    )
    
    reasoning_span = attributor.add_span(
        trace_id=trace_id,
        operation_name="llm.reasoning",
        span_type="llm",
        input_tokens=600,
        output_tokens=200,
        start_time=base_time + 1.6,
        end_time=base_time + 2.5,
        parent_span_id=root_span.span_id,
        model=TokenModel.GPT_4_TURBO,
    )
    
    db_span = attributor.add_span(
        trace_id=trace_id,
        operation_name="tool.database_query",
        span_type="tool",
        input_tokens=80,
        output_tokens=300,
        start_time=base_time + 2.6,
        end_time=base_time + 3.2,
        parent_span_id=root_span.span_id,
        model=TokenModel.GPT_35_TURBO,
    )
    
    final_reasoning = attributor.add_span(
        trace_id=trace_id,
        operation_name="llm.response_generation",
        span_type="llm",
        input_tokens=700,
        output_tokens=150,
        start_time=base_time + 3.3,
        end_time=base_time + 4.8,
        parent_span_id=root_span.span_id,
        model=TokenModel.GPT_4_TURBO,
    )
    
    return trace_id, attributor


def main():
    parser = argparse.ArgumentParser(
        description="Token cost attribution for AI agent observability"
    )
    parser.add_argument(
        "--mode",
        choices=["demo", "waterfall", "json"],
        default="demo",
        help="Output mode: demo (both views), waterfall, or json",
    )
    parser.add_argument(
        "--model",
        choices=[m.value for m in TokenModel],
        default=TokenModel.GPT_4_TURBO.value,
        help="Default token cost model",
    )
    parser.add_argument(
        "--trace-id",
        type=str,
        help="Trace ID to analyze (uses demo trace if not provided)",
    )
    
    args = parser.parse_args()
    
    model = TokenModel(args.model)
    
    trace_id, attributor = generate_sample_trace()
    
    if args.mode == "demo":
        print("\n" + attributor.waterfall_view(trace_id))
        print("\n")
        print(attributor.json_report(trace_id))
    elif args.mode == "waterfall":
        print(attributor.waterfall_view(trace_id))
    elif args.mode == "json":
        print(attributor.json_report(trace_id))


if __name__ == "__main__":
    main()