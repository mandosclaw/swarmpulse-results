#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OTel span instrumentation
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-29T13:08:35.850Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: OTel span instrumentation - Auto-instrument popular frameworks
Mission: AI Agent Observability Platform
Agent: @sue
Date: 2024-01-17
"""

import argparse
import json
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
import traceback


@dataclass
class SpanAttribute:
    """OpenTelemetry span attribute"""
    key: str
    value: Any


@dataclass
class SpanEvent:
    """OpenTelemetry span event"""
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """OpenTelemetry span representation"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "UNSET"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert span to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes
                }
                for e in self.events
            ],
            "tags": self.tags
        }


class TraceContext:
    """Thread-safe trace context for ID propagation"""
    
    def __init__(self):
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None
        self.parent_span_id: Optional[str] = None

    def new_trace(self) -> str:
        """Create new trace ID"""
        self.trace_id = str(uuid.uuid4())
        self.span_id = None
        self.parent_span_id = None
        return self.trace_id

    def new_span(self) -> tuple:
        """Create new span with parent tracking"""
        if not self.trace_id:
            self.new_trace()
        
        new_span_id = str(uuid.uuid4())
        parent_id = self.span_id
        self.span_id = new_span_id
        return self.trace_id, new_span_id, parent_id

    def get_context(self) -> Dict[str, str]:
        """Get current trace context"""
        return {
            "trace_id": self.trace_id or "",
            "span_id": self.span_id or "",
            "parent_span_id": self.parent_span_id or ""
        }


class SpanCollector:
    """Collects and stores spans"""
    
    def __init__(self):
        self.spans: List[Span] = []
        self.active_spans: Dict[str, Span] = {}

    def add_span(self, span: Span):
        """Add completed span"""
        self.spans.append(span)
        if span.span_id in self.active_spans:
            del self.active_spans[span.span_id]

    def set_active(self, span: Span):
        """Mark span as active"""
        self.active_spans[span.span_id] = span

    def get_spans_for_trace(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace"""
        return [s for s in self.spans if s.trace_id == trace_id]

    def get_all_spans(self) -> List[Span]:
        """Get all spans"""
        return self.spans.copy()

    def clear(self):
        """Clear all spans"""
        self.spans.clear()
        self.active_spans.clear()


class OpenTelemetryInstrumentor:
    """Base OpenTelemetry instrumentor"""
    
    def __init__(self, trace_context: TraceContext, collector: SpanCollector):
        self.trace_context = trace_context
        self.collector = collector

    @contextmanager
    def trace_span(self, span_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Context manager for creating and managing spans"""
        trace_id, span_id, parent_id = self.trace_context.new_span()
        start_time = time.time()
        
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            name=span_name,
            start_time=start_time,
            attributes=attributes or {}
        )
        
        self.collector.set_active(span)
        
        try:
            yield span
            span.status = "OK"
        except Exception as e:
            span.status = "ERROR"
            span.attributes["error.type"] = type(e).__name__
            span.attributes["error.message"] = str(e)
            span.attributes["error.stack"] = traceback.format_exc()
            raise
        finally:
            span.end_time = time.time()
            span.duration_ms = (span.end_time - span.start_time) * 1000
            self.collector.add_span(span)

    def add_span_event(self, span: Span, event_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add event to span"""
        event = SpanEvent(
            name=event_name,
            timestamp=time.time(),
            attributes=attributes or {}
        )
        span.events.append(event)

    def set_span_attribute(self, span: Span, key: str, value: Any):
        """Set span attribute"""
        span.attributes[key] = value

    def set_span_tag(self, span: Span, key: str, value: str):
        """Set span tag"""
        span.tags[key] = value


class LangChainInstrumentor(OpenTelemetryInstrumentor):
    """Instrument LangChain framework"""
    
    def instrument_llm_call(self, func: Callable) -> Callable:
        """Wrap LLM call with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            model_name = kwargs.get("model", "unknown")
            with self.trace_span(
                "llm.call",
                attributes={
                    "framework": "langchain",
                    "component.type": "llm",
                    "model.name": model_name
                }
            ) as span:
                result = func(*args, **kwargs)
                
                prompt_tokens = kwargs.get("prompt_tokens", 0)
                completion_tokens = kwargs.get("completion_tokens", 0)
                cost_per_prompt = 0.0015 / 1000
                cost_per_completion = 0.002 / 1000
                
                total_cost = (prompt_tokens * cost_per_prompt + 
                            completion_tokens * cost_per_completion)
                
                self.set_span_attribute(span, "llm.prompt_tokens", prompt_tokens)
                self.set_span_attribute(span, "llm.completion_tokens", completion_tokens)
                self.set_span_attribute(span, "llm.total_tokens", prompt_tokens + completion_tokens)
                self.set_span_attribute(span, "llm.cost_usd", total_cost)
                
                return result
        return wrapper

    def instrument_tool_call(self, func: Callable) -> Callable:
        """Wrap tool call with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_name = kwargs.get("tool_name", func.__name__)
            with self.trace_span(
                "tool.call",
                attributes={
                    "framework": "langchain",
                    "component.type": "tool",
                    "tool.name": tool_name
                }
            ) as span:
                result = func(*args, **kwargs)
                self.set_span_attribute(span, "tool.input", kwargs.get("input", ""))
                self.set_span_attribute(span, "tool.output_length", len(str(result)))
                return result
        return wrapper

    def instrument_chain(self, func: Callable) -> Callable:
        """Wrap chain execution with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            chain_name = kwargs.get("chain_name", func.__name__)
            with self.trace_span(
                "chain.execution",
                attributes={
                    "framework": "langchain",
                    "component.type": "chain",
                    "chain.name": chain_name
                }
            ) as span:
                result = func(*args, **kwargs)
                self.set_span_attribute(span, "chain.step_count", kwargs.get("steps", 1))
                return result
        return wrapper


class CrewAIInstrumentor(OpenTelemetryInstrumentor):
    """Instrument CrewAI framework"""
    
    def instrument_agent_task(self, func: Callable) -> Callable:
        """Wrap agent task with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs.get("task_id", str(uuid.uuid4())[:8])
            agent_role = kwargs.get("agent_role", "unknown")
            
            with self.trace_span(
                "agent.task",
                attributes={
                    "framework": "crewai",
                    "component.type": "agent_task",
                    "task.id": task_id,
                    "agent.role": agent_role
                }
            ) as span:
                result = func(*args, **kwargs)
                self.set_span_attribute(span, "task.status", "completed")
                return result
        return wrapper

    def instrument_agent_collaboration(self, func: Callable) -> Callable:
        """Wrap agent collaboration with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            num_agents = kwargs.get("num_agents", 1)
            
            with self.trace_span(
                "agent.collaboration",
                attributes={
                    "framework": "crewai",
                    "component.type": "collaboration",
                    "agent.count": num_agents
                }
            ) as span:
                result = func(*args, **kwargs)
                self.set_span_attribute(span, "collaboration.rounds", kwargs.get("rounds", 1))
                return result
        return wrapper


class OpenClawInstrumentor(OpenTelemetryInstrumentor):
    """Instrument OpenClaw framework"""
    
    def instrument_action(self, func: Callable) -> Callable:
        """Wrap action with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            action_type = kwargs.get("action_type", "unknown")
            
            with self.trace_span(
                "action.execute",
                attributes={
                    "framework": "openclaw",
                    "component.type": "action",
                    "action.type": action_type
                }
            ) as span:
                result = func(*args, **kwargs)
                self.set_span_attribute(span, "action.result", str(result)[:100])
                return result
        return wrapper

    def instrument_state_transition(self, func: Callable) -> Callable:
        """Wrap state transition with span"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            from_state = kwargs.get("from_state", "unknown")
            to_state = kwargs.get("to_state", "unknown")
            
            with self.trace_span(
                "state.transition",
                attributes={
                    "framework": "openclaw",
                    "component.type": "state_machine",
                    "state.from": from_state,
                    "state.to": to_state
                }
            ) as span:
                result = func(*args, **kwargs)
                return result
        return wrapper


class PromptInjectionDetector:
    """Detect prompt injection attempts in trace data"""
    
    INJECTION_PATTERNS = [
        "ignore previous",
        "forget",
        "system override",
        "execute code",
        "system prompt",
        "hidden instructions",
        "jailbreak",
        "bypass",
        "exploit",
        "\/\/ hack",
        "SELECT.*FROM",
        "DROP TABLE",
        "'; DROP",
        "<script>",
        "javascript:",
        "eval(",
        "exec(",
        "__import__"
    ]

    @classmethod
    def detect_injection(cls, trace_data: Dict) -> List[Dict]:
        """Detect injection attempts in trace"""
        detections = []
        
        for span in trace_data.get("spans", []):
            text_content = ""
            
            if "attributes" in span:
                for k, v in span["attributes"].items():
                    text_content += " " + str(v).lower()
            
            for pattern in cls.INJECTION_PATTERNS:
                if pattern.lower() in text_content:
                    detections.append({
                        "span_id": span.get("span_id"),
                        "span_name": span.get("name"),
                        "pattern": pattern,
                        "severity": "HIGH" if pattern in ["SELECT", "DROP", "exec"] else "MEDIUM",
                        "timestamp": span.get("start_time")
                    })
        
        return detections


class LatencyAnalyzer:
    """Analyze and identify latency bottlenecks"""
    
    def __init__(self, threshold_ms: float = 100.0):
        self.threshold_ms = threshold_ms

    def analyze_trace(self, spans: List[Span]) -> Dict:
        """Analyze trace for latency bottlenecks"""
        if not spans:
            return {"bottlenecks": [], "total_duration_ms": 0}
        
        bottlenecks = []
        total_duration = 0
        
        for span in spans:
            if span.duration_ms > self.threshold_ms:
                bottlenecks.append({
                    "span_id": span.span_id,
                    "name": span.name,
                    "duration_ms": span.duration_ms,
                    "percentage_of_max": (span.duration_ms / max([s.duration_ms for s in spans])) * 100
                })
            total_duration = max(total_duration, span.duration_ms)
        
        bottlenecks.sort(key=lambda x: x["duration_ms"], reverse=True)
        
        return {
            "bottlenecks": bottlenecks,
            "total_duration_ms": total_duration,
            "threshold_ms": self.threshold_ms,
            "critical_count": len(bottlenecks)
        }

    def get_span_hierarchy(self, spans: List[Span]) -> Dict:
        """Get span execution hierarchy"""
        hierarchy = {}
        root_spans = [s for s in spans if not s.parent_span_id]
        
        def build_tree(parent: Span):
            children = [s for s in spans if s.parent_span_id == parent.span_id]
            return {
                "span_id": parent.span_id,
                "name": parent.name,
                "duration_ms": parent.duration_ms,
                "children": [build_tree(child) for child in children]