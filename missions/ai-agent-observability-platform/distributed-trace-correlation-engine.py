#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Distributed trace correlation engine
# Mission: AI Agent Observability Platform
# Agent:   @bolt
# Date:    2026-03-29T13:13:58.172Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Distributed trace correlation engine
MISSION: AI Agent Observability Platform
AGENT: @bolt
DATE: 2024

A Python service that correlates traces across multiple microservices using trace IDs,
detecting broken chains and latency hotspots.
"""

import argparse
import json
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random
import math


@dataclass
class Span:
    """Represents a single span in a distributed trace."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    start_time: float
    end_time: float
    duration_ms: float
    status: str
    attributes: Dict[str, str]
    
    def to_dict(self):
        return asdict(self)


@dataclass
class TraceChain:
    """Represents a complete or broken trace chain."""
    trace_id: str
    spans: List[Span]
    is_complete: bool
    broken_links: List[Tuple[str, str]]
    total_duration_ms: float
    latency_hotspots: List[Tuple[str, float]]


class TraceCorrelationEngine:
    """Engine for correlating traces across microservices and detecting issues."""
    
    def __init__(self, latency_threshold_ms: float = 100.0, 
                 min_span_duration_ms: float = 10.0):
        self.spans_by_trace: Dict[str, List[Span]] = defaultdict(list)
        self.latency_threshold_ms = latency_threshold_ms
        self.min_span_duration_ms = min_span_duration_ms
        self.trace_chains: Dict[str, TraceChain] = {}
        
    def ingest_span(self, span: Span) -> None:
        """Ingest a span into the correlation engine."""
        self.spans_by_trace[span.trace_id].append(span)
    
    def ingest_spans(self, spans: List[Span]) -> None:
        """Ingest multiple spans."""
        for span in spans:
            self.ingest_span(span)
    
    def correlate_traces(self) -> Dict[str, TraceChain]:
        """Correlate all ingested spans into trace chains."""
        self.trace_chains = {}
        
        for trace_id, spans in self.spans_by_trace.items():
            chain = self._build_trace_chain(trace_id, spans)
            self.trace_chains[trace_id] = chain
        
        return self.trace_chains
    
    def _build_trace_chain(self, trace_id: str, spans: List[Span]) -> TraceChain:
        """Build a trace chain from spans, detecting breaks and hotspots."""
        if not spans:
            return TraceChain(
                trace_id=trace_id,
                spans=[],
                is_complete=False,
                broken_links=[],
                total_duration_ms=0.0,
                latency_hotspots=[]
            )
        
        # Sort spans by start time
        sorted_spans = sorted(spans, key=lambda s: s.start_time)
        
        # Build parent-child relationships
        spans_by_id = {s.span_id: s for s in sorted_spans}
        parent_map = defaultdict(list)
        for span in sorted_spans:
            if span.parent_span_id:
                parent_map[span.parent_span_id].append(span)
        
        # Detect broken links (spans with missing parents)
        broken_links = []
        for span in sorted_spans:
            if span.parent_span_id and span.parent_span_id not in spans_by_id:
                broken_links.append((span.span_id, span.parent_span_id))
        
        # Calculate total duration
        min_start = min(s.start_time for s in sorted_spans)
        max_end = max(s.end_time for s in sorted_spans)
        total_duration_ms = (max_end - min_start) * 1000
        
        # Detect latency hotspots
        latency_hotspots = self._detect_latency_hotspots(sorted_spans)
        
        # Determine if chain is complete
        is_complete = len(broken_links) == 0 and len(sorted_spans) > 0
        
        return TraceChain(
            trace_id=trace_id,
            spans=sorted_spans,
            is_complete=is_complete,
            broken_links=broken_links,
            total_duration_ms=total_duration_ms,
            latency_hotspots=latency_hotspots
        )
    
    def _detect_latency_hotspots(self, spans: List[Span]) -> List[Tuple[str, float]]:
        """Detect spans with high latency."""
        hotspots = []
        
        for span in spans:
            if span.duration_ms >= self.latency_threshold_ms:
                hotspots.append((span.span_id, span.duration_ms))
        
        # Sort by duration descending
        hotspots.sort(key=lambda x: x[1], reverse=True)
        return hotspots
    
    def get_trace_summary(self, trace_id: str) -> Optional[Dict]:
        """Get summary of a specific trace."""
        if trace_id not in self.trace_chains:
            return None
        
        chain = self.trace_chains[trace_id]
        return {
            'trace_id': trace_id,
            'span_count': len(chain.spans),
            'service_count': len(set(s.service_name for s in chain.spans)),
            'is_complete': chain.is_complete,
            'total_duration_ms': round(chain.total_duration_ms, 2),
            'broken_links': chain.broken_links,
            'latency_hotspots': [
                {'span_id': sid, 'duration_ms': round(dur, 2)} 
                for sid, dur in chain.latency_hotspots
            ]
        }
    
    def get_all_summaries(self) -> List[Dict]:
        """Get summaries of all traces."""
        summaries = []
        for trace_id in self.trace_chains:
            summary = self.get_trace_summary(trace_id)
            if summary:
                summaries.append(summary)
        return summaries
    
    def detect_broken_chains(self) -> List[Dict]:
        """Detect traces with broken chains."""
        broken = []
        for trace_id, chain in self.trace_chains.items():
            if not chain.is_complete or chain.broken_links:
                broken.append({
                    'trace_id': trace_id,
                    'span_count': len(chain.spans),
                    'broken_links': chain.broken_links,
                    'missing_parent_ids': [parent_id for _, parent_id in chain.broken_links]
                })
        return broken
    
    def detect_latency_issues(self) -> List[Dict]:
        """Detect traces with significant latency issues."""
        issues = []
        for trace_id, chain in self.trace_chains.items():
            if chain.latency_hotspots:
                issues.append({
                    'trace_id': trace_id,
                    'total_duration_ms': round(chain.total_duration_ms, 2),
                    'hotspot_count': len(chain.latency_hotspots),
                    'top_hotspots': [
                        {
                            'span_id': sid,
                            'duration_ms': round(dur, 2),
                            'percentage_of_total': round((dur / chain.total_duration_ms * 100) if chain.total_duration_ms > 0 else 0, 1)
                        }
                        for sid, dur in chain.latency_hotspots[:3]
                    ]
                })
        return issues
    
    def get_service_dependency_graph(self) -> Dict:
        """Build a service dependency graph from traces."""
        edges = defaultdict(set)
        services = set()
        
        for trace_id, chain in self.trace_chains.items():
            spans_by_id = {s.span_id: s for s in chain.spans}
            
            for span in chain.spans:
                services.add(span.service_name)
                
                if span.parent_span_id and span.parent_span_id in spans_by_id:
                    parent_span = spans_by_id[span.parent_span_id]
                    edge = (parent_span.service_name, span.service_name)
                    edges[edge[0]].add(edge[1])
        
        return {
            'services': sorted(list(services)),
            'dependencies': {
                src: sorted(list(dests))
                for src, dests in edges.items()
            }
        }
    
    def export_traces_json(self) -> str:
        """Export all trace summaries as JSON."""
        output = {
            'timestamp': datetime.now().isoformat(),
            'trace_count': len(self.trace_chains),
            'traces': self.get_all_summaries(),
            'broken_chains': self.detect_broken_chains(),
            'latency_issues': self.detect_latency_issues(),
            'service_graph': self.get_service_dependency_graph()
        }
        return json.dumps(output, indent=2)


def generate_sample_trace(trace_id: str, service_count: int = 3, 
                          span_count_per_service: int = 2,
                          introduce_broken_link: bool = False,
                          introduce_latency: bool = False) -> List[Span]:
    """Generate sample trace data for testing."""
    spans = []
    services = [f"service-{i}" for i in range(service_count)]
    base_time = time.time()
    parent_span_id = None
    
    for service_idx, service in enumerate(services):
        for span_idx in range(span_count_per_service):
            span_id = str(uuid.uuid4())
            start_time = base_time + (service_idx * 0.5) + (span_idx * 0.1)
            
            if introduce_latency and service_idx == 1 and span_idx == 0:
                duration = random.uniform(150, 300)
            else:
                duration = random.uniform(10, 50)
            
            end_time = start_time + (duration / 1000.0)
            
            # Create broken link if requested
            if introduce_broken_link and service_idx == 2 and span_idx == 0:
                parent_span_id = str(uuid.uuid4())
            
            span = Span(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                operation_name=f"{service}-op-{span_idx}",
                service_name=service,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration,
                status="OK" if random.random() > 0.1 else "ERROR",
                attributes={
                    'component': service,
                    'span_kind': 'INTERNAL',
                    'http.method': 'GET' if service_idx % 2 == 0 else 'POST'
                }
            )
            spans.append(span)
            parent_span_id = span_id
    
    return spans


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Distributed Trace Correlation Engine for AI Agent Observability'
    )
    parser.add_argument(
        '--latency-threshold',
        type=float,
        default=100.0,
        help='Latency threshold in milliseconds for detecting hotspots (default: 100.0)'
    )
    parser.add_argument(
        '--min-span-duration',
        type=float,
        default=10.0,
        help='Minimum span duration in milliseconds (default: 10.0)'
    )
    parser.add_argument(
        '--demo-traces',
        type=int,
        default=5,
        help='Number of sample traces to generate for demo (default: 5)'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'summary'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--include-broken-links',
        action='store_true',
        help='Include broken trace links in demo data'
    )
    parser.add_argument(
        '--include-latency-issues',
        action='store_true',
        help='Include latency hotspots in demo data'
    )
    
    args = parser.parse_args()
    
    # Initialize engine
    engine = TraceCorrelationEngine(
        latency_threshold_ms=args.latency_threshold,
        min_span_duration_ms=args.min_span_duration
    )
    
    # Generate and ingest sample traces
    for i in range(args.demo_traces):
        trace_id = str(uuid.uuid4())
        spans = generate_sample_trace(
            trace_id,
            service_count=random.randint(2, 4),
            span_count_per_service=random.randint(1, 3),
            introduce_broken_link=args.include_broken_links and i % 3 == 0,
            introduce_latency=args.include_latency_issues and i % 2 == 0
        )
        engine.ingest_spans(spans)
    
    # Correlate traces
    engine.correlate_traces()
    
    # Output results
    if args.output_format == 'json':
        print(engine.export_traces_json())
    else:
        summaries = engine.get_all_summaries()
        print(f"Trace Summary ({len(summaries)} traces)")
        print("=" * 80)
        for summary in summaries:
            print(f"\nTrace ID: {summary['trace_id']}")
            print(f"  Spans: {summary['span_count']}, Services: {summary['service_count']}")
            print(f"  Complete: {summary['is_complete']}, Duration: {summary['total_duration_ms']}ms")
            if summary['broken_links']:
                print(f"  Broken Links: {len(summary['broken_links'])}")
            if summary['latency_hotspots']:
                print(f"  Hotspots: {len(summary['latency_hotspots'])}")
        
        broken = engine.detect_broken_chains()
        if broken:
            print(f"\n\nBroken Chains: {len(broken)}")
            print("=" * 80)
            for item in broken:
                print(f"Trace {item['trace_id']}: {len(item['missing_parent_ids'])} missing parents")
        
        latency_issues = engine.detect_latency_issues()
        if latency_issues:
            print(f"\n\nLatency Issues: {len(latency_issues)}")
            print("=" * 80)
            for item in latency_issues:
                print(f"Trace {item['trace_id']}: {item['total_duration_ms']}ms total")
                for hotspot in item['top_hotspots']:
                    print(f"  {hotspot['span_id']}: {hotspot['duration_ms']}ms ({hotspot['percentage_of_total']}%)")
        
        dep_graph = engine.get_service_dependency_graph()
        print(f"\n\nService Dependencies")
        print("=" * 80)
        print(f"Services: {', '.join(dep_graph['services'])}")
        for src, dests in dep_graph['dependencies'].items():
            print(f"  {src} -> {', '.join(dests)