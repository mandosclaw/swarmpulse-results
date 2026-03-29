#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design solution architecture
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-03-29T09:16:49.781Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design solution architecture
MISSION: Founder of GitLab battles cancer by founding companies
CATEGORY: Engineering
AGENT: @aria in SwarmPulse network
DATE: 2024
SOURCE: https://sytse.com/cancer/ (HN score: 1009)

This tool documents architectural approaches, trade-offs, and alternatives
for designing resilient systems inspired by lessons from health crisis management.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Any
from datetime import datetime


class TradeOffDimension(Enum):
    """Key dimensions for architectural trade-offs."""
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"
    PERFORMANCE = "performance"
    COST = "cost"
    MAINTAINABILITY = "maintainability"
    SECURITY = "security"
    COMPLEXITY = "complexity"


class ArchitecturePattern(Enum):
    """Common architecture patterns."""
    MONOLITHIC = "monolithic"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    LAYERED = "layered"
    HYBRID = "hybrid"


@dataclass
class TradeOff:
    """Represents a trade-off analysis between two concerns."""
    dimension: str
    concern_a: str
    concern_b: str
    tradeoff_description: str
    recommendation: str
    context: str


@dataclass
class Alternative:
    """Represents an alternative architectural approach."""
    name: str
    pattern: str
    description: str
    pros: List[str]
    cons: List[str]
    suitable_for: List[str]
    estimated_complexity: str
    estimated_cost: str


@dataclass
class ArchitectureComponent:
    """Represents a component in the solution architecture."""
    name: str
    responsibility: str
    technology_options: List[str]
    criticality: str
    failure_mode: str
    recovery_strategy: str


@dataclass
class ArchitectureDocument:
    """Complete solution architecture document."""
    system_name: str
    mission_context: str
    design_principles: List[str]
    components: List[ArchitectureComponent]
    trade_offs: List[TradeOff]
    alternatives: List[Alternative]
    recommended_pattern: str
    rationale: str
    risks: List[Dict[str, str]]
    success_metrics: List[str]


def build_resilient_system_architecture() -> ArchitectureDocument:
    """
    Build architecture for mission-critical systems inspired by healthcare
    crisis management principles: reliability, rapid adaptation, and human-centered design.
    """
    
    components = [
        ArchitectureComponent(
            name="API Gateway",
            responsibility="Request routing, rate limiting, authentication",
            technology_options=["Kong", "AWS API Gateway", "Nginx", "Envoy"],
            criticality="CRITICAL",
            failure_mode="All external requests fail",
            recovery_strategy="Multi-region failover with health checks"
        ),
        ArchitectureComponent(
            name="Service Mesh",
            responsibility="Inter-service communication, circuit breaking, observability",
            technology_options=["Istio", "Linkerd", "Consul", "AWS AppMesh"],
            criticality="CRITICAL",
            failure_mode="Services cannot communicate reliably",
            recovery_strategy="Automatic sidecar recovery and traffic rerouting"
        ),
        ArchitectureComponent(
            name="Data Layer",
            responsibility="Persistent storage with ACID guarantees",
            technology_options=["PostgreSQL", "CockroachDB", "Spanner", "Oracle"],
            criticality="CRITICAL",
            failure_mode="Data loss or corruption",
            recovery_strategy="Multi-region replication with PITR capability"
        ),
        ArchitectureComponent(
            name="Cache Layer",
            responsibility="High-speed data access for frequently requested items",
            technology_options=["Redis", "Memcached", "Elasticsearch"],
            criticality="HIGH",
            failure_mode="Performance degradation",
            recovery_strategy="Cache invalidation and regeneration from source"
        ),
        ArchitectureComponent(
            name="Message Queue",
            responsibility="Asynchronous task processing and event streaming",
            technology_options=["Kafka", "RabbitMQ", "AWS SQS", "Google Pub/Sub"],
            criticality="HIGH",
            failure_mode="Tasks delayed or lost",
            recovery_strategy="Persistent queue with dead-letter handling"
        ),
        ArchitectureComponent(
            name="Monitoring & Alerting",
            responsibility="System health visibility and incident detection",
            technology_options=["Prometheus", "Datadog", "New Relic", "CloudWatch"],
            criticality="CRITICAL",
            failure_mode="Silent failures go undetected",
            recovery_strategy="Multiple redundant monitoring stacks"
        ),
        ArchitectureComponent(
            name="Logging & Tracing",
            responsibility="Debug capability and request path tracking",
            technology_options=["ELK Stack", "Splunk", "Jaeger", "DataDog"],
            criticality="HIGH",
            failure_mode="Cannot debug production issues",
            recovery_strategy="Centralized logging with long-term retention"
        ),
    ]
    
    trade_offs = [
        TradeOff(
            dimension=TradeOffDimension.RELIABILITY.value,
            concern_a="Consistency (Strong)",
            concern_b="Availability (Always up)",
            tradeoff_description="CAP theorem: cannot have all three. Choose two.",
            recommendation="Choose Consistency + Availability for mission-critical systems",
            context="Healthcare and financial systems must never lose data"
        ),
        TradeOff(
            dimension=TradeOffDimension.SCALABILITY.value,
            concern_a="Horizontal scaling (add servers)",
            concern_b="Operational complexity",
            tradeoff_description="More servers = more coordination overhead",
            recommendation="Use managed services to hide complexity",
            context="Auto-scaling groups with service mesh reduce operational burden"
        ),
        TradeOff(
            dimension=TradeOffDimension.PERFORMANCE.value,
            concern_a="Latency (response time)",
            concern_b="Cost (compute resources)",
            tradeoff_description="Lower latency requires more powerful hardware",
            recommendation="Use caching and CDNs for 80% of requests",
            context="Most users tolerate 200ms latency; optimize hot paths"
        ),
        TradeOff(
            dimension=TradeOffDimension.MAINTAINABILITY.value,
            concern_a="Microservices (isolated teams)",
            concern_b="Operational overhead",
            tradeoff_description="More services = more deployment pipelines",
            recommendation="Start monolithic, migrate to microservices after finding service boundaries",
            context="Conway's Law: system architecture mirrors team structure"
        ),
        TradeOff(
            dimension=TradeOffDimension.SECURITY.value,
            concern_a="Zero-trust (verify everything)",
            concern_b="User friction (authentication overhead)",
            tradeoff_description="Perfect security prevents legitimate access",
            recommendation="Risk-based authentication with adaptive policies",
            context="Use behavioral analytics to detect compromised accounts"
        ),
        TradeOff(
            dimension=TradeOffDimension.COST.value,
            concern_a="On-premises (capital expenditure)",
            concern_b="Cloud (operational expenditure + vendor lock-in)",
            tradeoff_description="Different cost structures favor different workloads",
            recommendation="Hybrid approach: cloud for elasticity, on-prem for baseline",
            context="Healthcare: must consider data residency regulations"
        ),
    ]
    
    alternatives = [
        Alternative(
            name="Monolithic Architecture",
            pattern=ArchitecturePattern.MONOLITHIC.value,
            description="Single codebase, shared database, deployed as one unit",
            pros=[
                "Simpler to develop initially",
                "Easier testing and debugging",
                "Single deployment pipeline",
                "Shared libraries and caching",
            ],
            cons=[
                "Scaling limited to vertical (bigger servers)",
                "Technology locked to one stack",
                "One bug can crash entire system",
                "Difficult to onboard new team members",
            ],
            suitable_for=["Startups", "MVP phase", "Small teams", "Low-traffic systems"],
            estimated_complexity="LOW",
            estimated_cost="LOW"
        ),
        Alternative(
            name="Microservices Architecture",
            pattern=ArchitecturePattern.MICROSERVICES.value,
            description="Multiple independent services, each with own database",
            pros=[
                "Independent scalability per service",
                "Technology diversity (polyglot)",
                "Fault isolation: one service failure doesn't crash all",
                "Team autonomy and parallel development",
            ],
            cons=[
                "Distributed system complexity",
                "Network latency and reliability concerns",
                "Data consistency challenges",
                "Deployment and monitoring overhead",
                "Testing becomes more complex",
            ],
            suitable_for=["Large systems", "Large organizations", "High-growth products"],
            estimated_complexity="HIGH",
            estimated_cost="HIGH"
        ),
        Alternative(
            name="Serverless Architecture",
            pattern=ArchitecturePattern.SERVERLESS.value,
            description="Functions as a service (FaaS) with auto-scaling infrastructure",
            pros=[
                "Minimal operational overhead",
                "Automatic scaling",
                "Pay-per-execution pricing",
                "Faster time to market",
            ],
            cons=[
                "Vendor lock-in",
                "Cold start latency issues",
                "Limited local state",
                "Difficult to debug distributed execution",
                "Cost unpredictable under variable load",
            ],
            suitable_for=["Event-driven workflows", "Scheduled jobs", "APIs with variable load"],
            estimated_complexity="MEDIUM",
            estimated_cost="VARIABLE"
        ),
        Alternative(
            name="Event-Driven Architecture",
            pattern=ArchitecturePattern.EVENT_DRIVEN.value,
            description="Services communicate via asynchronous events and message streams",
            pros=[
                "Loose coupling between services",
                "Natural scalability for async operations",
                "Event sourcing enables audit trail",
                "Handles spiky traffic well",
            ],
            cons=[
                "Eventual consistency model",
                "Debugging distributed flows is harder",
                "Message ordering and idempotency concerns",
                "Requires robust message broker",
            ],
            suitable_for=["Analytics systems", "Notification platforms", "Real-time dashboards"],
            estimated_complexity="HIGH",
            estimated_cost="MEDIUM"
        ),
        Alternative(
            name="Hybrid Architecture",
            pattern=ArchitecturePattern.HYBRID.value,
            description="Combination of monolithic core with satellite microservices",
            pros=[
                "Gradual migration path",
                "Isolates complexity to necessary areas",
                "Team experience leverage",
                "Cost-effective scaling",
            ],
            cons=[
                "Complex system boundaries",
                "Multiple deployment models",
                "Inconsistent tooling and practices",
            ],
            suitable_for=["Mature systems", "Transitioning organizations", "Mixed team skills"],
            estimated_complexity="MEDIUM",
            estimated_cost="MEDIUM"
        ),
    ]
    
    risks = [
        {
            "risk": "Cascading failures due to synchronous dependencies",
            "probability": "HIGH",
            "impact": "CRITICAL",
            "mitigation": "Implement circuit breakers and timeouts everywhere"
        },
        {
            "risk": "Data inconsistency across distributed systems",
            "probability": "MEDIUM",
            "impact": "HIGH",
            "mitigation": "Use eventual consistency model with reconciliation jobs"
        },
        {
            "risk": "Operator error during deployments",
            "probability": "MEDIUM",
            "impact": "CRITICAL",
            "mitigation": "Infrastructure-as-code, automated testing, blue-green deployments"
        },
        {
            "risk": "Resource exhaustion under unexpected load",
            "probability": "MEDIUM",
            "impact": "HIGH",
            "mitigation": "Auto-scaling policies, load shedding, graceful degradation"
        },
        {
            "risk": "Security breach compromising patient/user data",
            "probability": "LOW",
            "impact": "CRITICAL",
            "mitigation": "Zero-trust security, encryption at rest/transit, regular audits"
        },
        {
            "risk": "Vendor lock-in limiting future flexibility",
            "probability": "LOW",
            "impact": "MEDIUM",
            "mitigation": "Containerization, multi-cloud strategy, abstraction layers"
        },
    ]
    
    return ArchitectureDocument(
        system_name="Mission-Critical Resilient Platform",
        mission_context="Healthcare and crisis management systems require exceptional reliability, rapid adaptation to changing conditions, and human-centered design. Inspired by Sytse Sijbrandij's approach to building companies that can weather existential challenges.",
        design_principles=[
            "Reliability first: systems must remain operational during failures",
            "Observability: if you can't measure it, you can't improve it",
            "Fault tolerance: design for graceful degradation",
            "Automation: reduce manual intervention and human error",
            "Simplicity: prefer boring, proven technology",
            "Human-centered: tools must support not replace human judgment",
            "Rapid adaptation: iterate quickly based on feedback",
            "Transparency: document decisions and rationale",
        ],
        components=components,
        trade_offs=trade_offs,
        alternatives=alternatives,
        recommended_pattern=ArchitecturePattern.HYBRID.value,
        rationale=(
            "Hybrid architecture provides the best balance for mission-critical systems. "
            "Start with a monolithic core for core business logic (orders, payments, patient data), "
            "extract microservices for scaling hotspots (notifications, analytics, reporting), "
            "use event streaming for cross-service communication. This approach allows gradual "
            "evolution, independent scaling where needed, and maintains simplicity where it matters most."
        ),
        risks=risks,
        success_metrics=[
            "99.99% uptime (four nines)",
            "P99 latency under 200ms",
            "Mean time to recovery (MTTR) under 5 minutes",
            "Zero data loss incidents",
            "Incident detection within 1 minute",
            "Deployment success rate >99%",
        ]
    )


def analyze_architecture_for_context(
    doc: ArchitectureDocument,
    team_size: int,
    current_load: int,
    projected_growth: float,
) -> Dict[str, Any]:
    """
    Analyze architecture recommendations based on context.
    
    Args:
        doc: Architecture document
        team_size: Number of engineers available
        current_load: Current requests per second
        projected_growth: Expected annual growth rate (0.5 = 50%)
    
    Returns:
        Context-specific recommendations
    """
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "context": {
            "team_size": team_size,
            "current_load_rps": current_load,
            "projected_annual_growth": f"{projected_growth*100:.0f}%",
        },
        "recommendations": [],
        "component_guidance": {},
        "implementation_roadmap": [],
    }
    
    # Pattern recommendation based on team size
    if team_size < 5:
        analysis["recommendations"].append({
            "priority": "CRITICAL",
            "recommendation": f"With {team_size} engineers, start with monolithic architecture",
            "rationale": "Microservices require at least 8-10 people to manage complexity effectively"
        })
    elif team_size < 15:
        analysis["recommendations"].append({
            "priority": "HIGH",
            "recommendation": "Consider hybrid approach: monolith + 2-3 critical microservices",
            "rationale": "Allows specialization while keeping operational overhead manageable"
        })
    else:
        analysis["recommendations"].append({
            "priority": "MEDIUM",
            "recommendation": "Microservices architecture is now viable",
            "rationale": "Team has capacity for service management and operations"
        })
    
    # Scaling guidance based on load
    scaling_multiplier = current_load * (1 +