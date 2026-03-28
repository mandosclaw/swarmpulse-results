#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Distributed trace correlation engine
# Mission: AI Agent Observability Platform
# Agent:   @bolt
# Date:    2026-03-28T22:01:12.137Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Distributed trace correlation engine
MISSION: AI Agent Observability Platform
AGENT: @bolt
DATE: 2024

Build a Python service that correlates traces across multiple microservices using trace IDs,
detecting broken chains and latency hotspots.
"""

import json
import argparse
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import re


@dataclass
class TraceSpan:
    """Represents a single span in a distributed trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_name: str
    operation_name: str
    start_time: float
    end_time: float
    duration_ms: float
    status: str
    tags: Dict[str, str]
    logs: List[Dict]
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TraceChain:
    """Represents a complete trace chain."""
    trace_id: str
    spans: List[TraceSpan]
    total_duration_ms: float
    root_service: str
    is_complete: bool
    broken_links: List[str]
    latency_hotspots: List[Tuple[str, float]]


class DistributedTraceCorrelationEngine:
    """Engine for correlating distributed traces and detecting anomalies."""
    
    def __init__(self, latency_threshold_ms: float = 100.0, min_span_count: int = 1):
        """
        Initialize the trace correlation engine.
        
        Args:
            latency_threshold_ms: Threshold in ms for detecting latency hotspots
            min_span_count: Minimum spans required to consider a trace valid
        """
        self.traces: Dict[str, List[TraceSpan]] = defaultdict(list)
        self.latency_threshold_ms = latency_threshold_ms
        self.min_span_count = min_span_count
        self.correlation_results: List[Dict] = []
        
    def ingest_span(self, span: TraceSpan) -> None:
        """Ingest a single span into the correlation engine."""
        self.traces[span.trace_id].append(span)
        
    def ingest_spans(self, spans: List[TraceSpan]) -> None:
        """Ingest multiple spans."""
        for span in spans:
            self.ingest_span(span)
            
    def _build_span_tree(self, trace_id: str) -> Dict[str, List[TraceSpan]]:
        """Build parent-child relationships for spans."""
        spans = self.traces[trace_id]
        tree = defaultdict(list)
        for span in spans:
            if span.parent_span_id:
                tree[span.parent_span_id].append(span)
            else:
                tree[None].append(span)
        return tree
        
    def _detect_broken_chains(self, trace_id: str) -> List[str]:
        """Detect broken parent-child relationships in a trace."""
        spans = self.traces[trace_id]
        span_ids = {span.span_id for span in spans}
        broken_links = []
        
        for span in spans:
            if span.parent_span_id and span.parent_span_id not in span_ids:
                broken_links.append(
                    f"Span {span.span_id} in {span.service_name} "
                    f"references missing parent {span.parent_span_id}"
                )
                
        return broken_links
        
    def _detect_latency_hotspots(self, trace_id: str) -> List[Tuple[str, float]]:
        """Identify spans exceeding latency threshold."""
        spans = self.traces[trace_id]
        hotspots = []
        
        for span in spans:
            if span.duration_ms > self.latency_threshold_ms:
                hotspots.append((f"{span.service_name}:{span.operation_name}", span.duration_ms))
                
        hotspots.sort(key=lambda x: x[1], reverse=True)
        return hotspots
        
    def _calculate_total_duration(self, trace_id: str) -> float:
        """Calculate total trace duration from root to leaf spans."""
        spans = self.traces[trace_id]
        if not spans:
            return 0.0
            
        min_start = min(span.start_time for span in spans)
        max_end = max(span.end_time for span in spans)
        return (max_end - min_start) * 1000
        
    def _find_root_service(self, trace_id: str) -> str:
        """Find the root service that initiated the trace."""
        spans = self.traces[trace_id]
        root_spans = [span for span in spans if span.parent_span_id is None]
        
        if root_spans:
            return root_spans[0].service_name
        return "unknown"
        
    def correlate_trace(self, trace_id: str) -> TraceChain:
        """
        Correlate all spans for a given trace ID.
        
        Returns:
            TraceChain object containing correlation results
        """
        if trace_id not in self.traces or not self.traces[trace_id]:
            return TraceChain(
                trace_id=trace_id,
                spans=[],
                total_duration_ms=0.0,
                root_service="unknown",
                is_complete=False,
                broken_links=[],
                latency_hotspots=[]
            )
            
        spans = sorted(self.traces[trace_id], key=lambda s: s.start_time)
        total_duration = self._calculate_total_duration(trace_id)
        root_service = self._find_root_service(trace_id)
        broken_links = self._detect_broken_chains(trace_id)
        hotspots = self._detect_latency_hotspots(trace_id)
        
        is_complete = (
            len(spans) >= self.min_span_count and
            len(broken_links) == 0 and
            all(span.status == "success" for span in spans)
        )
        
        trace_chain = TraceChain(
            trace_id=trace_id,
            spans=spans,
            total_duration_ms=total_duration,
            root_service=root_service,
            is_complete=is_complete,
            broken_links=broken_links,
            latency_hotspots=hotspots
        )
        
        return trace_chain
        
    def correlate_all_traces(self) -> List[TraceChain]:
        """Correlate all ingested traces."""
        trace_chains = []
        for trace_id in self.traces.keys():
            chain = self.correlate_trace(trace_id)
            trace_chains.append(chain)
            
        return trace_chains
        
    def generate_correlation_report(self) -> Dict:
        """Generate a comprehensive correlation report."""
        trace_chains = self.correlate_all_traces()
        
        complete_traces = [chain for chain in trace_chains if chain.is_complete]
        broken_traces = [chain for chain in trace_chains if chain.broken_links]
        traces_with_hotspots = [chain for chain in trace_chains if chain.latency_hotspots]
        
        total_duration = sum(chain.total_duration_ms for chain in trace_chains)
        avg_duration = total_duration / len(trace_chains) if trace_chains else 0.0
        
        all_hotspots = []
        for chain in traces_with_hotspots:
            all_hotspots.extend(chain.latency_hotspots)
        
        hotspot_summary = {}
        for service_op, duration in all_hot