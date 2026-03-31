#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Token cost attribution
# Mission: AI Agent Observability Platform
# Agent:   @dex
# Date:    2026-03-31T18:44:47.256Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Token cost attribution
Mission: AI Agent Observability Platform
Agent: @dex
Date: 2024

Implements end-to-end token cost attribution system for AI agents,
including cost calculation, per-agent attribution, cost anomaly detection,
and exportable metrics for Grafana dashboards.
"""

import argparse
import json
import sys
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ModelProvider(Enum):
    """Supported LLM providers with their token costs."""
    OPENAI_GPT4 = {
        "name": "gpt-4",
        "input_cost_per_1k": 0.03,
        "output_cost_per_1k": 0.06
    }
    OPENAI_GPT35 = {
        "name": "gpt-3.5-turbo",
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015
    }
    OPENAI_GPT4_TURBO = {
        "name": "gpt-4-turbo",
        "input_cost_per_1k": 0.01,
        "output_cost_per_1k": 0.03
    }
    ANTHROPIC_CLAUDE3_OPUS = {
        "name": "claude-3-opus",
        "input_cost_per_1k": 0.015,
        "output_cost_per_1k": 0.075
    }
    ANTHROPIC_CLAUDE3_SONNET = {
        "name": "claude-3-sonnet",
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015
    }
    GOOGLE_PALM2 = {
        "name": "palm-2",
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015
    }

    def get_costs(self) -> Dict[str, float]:
        """Returns input and output costs per 1k tokens."""
        return self.value


@dataclass
class TokenUsage:
    """Token usage metrics for a single request."""
    trace_id: str
    agent_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    timestamp: float
    latency_ms: float


@dataclass
class CostAttribution:
    """Cost attribution for a single request."""
    trace_id: str
    agent_id: str
    model: str
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: float


class CostCalculator:
    """Calculates token costs based on model pricing."""

    def __init__(self):
        """Initialize cost calculator with provider pricing."""
        self.provider_costs = {
            provider.value["name"]: provider.value
            for provider in ModelProvider
        }

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> Tuple[float, float, float]:
        """
        Calculate input, output, and total cost for token usage.
        
        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3-opus')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        if model not in self.provider_costs:
            raise ValueError(f"Unknown model: {model}")

        pricing = self.provider_costs[model]
        input_cost = (input_tokens / 1000) * pricing["input_cost_per_1k"]
        output_cost = (output_tokens / 1000) * pricing["output_cost_per_1k"]
        total_cost = input_cost + output_cost

        return input_cost, output_cost, total_cost

    def get_supported_models(self) -> List[str]:
        """Returns list of supported model names."""
        return list(self.provider_costs.keys())


class CostAttributor:
    """Attributes costs to agents and tracks per-agent spending."""

    def __init__(self):
        """Initialize cost attributor."""
        self.calculator = CostCalculator()
        self.attributions: List[CostAttribution] = []
        self.agent_costs: Dict[str, float] = defaultdict(float)
        self.agent_model_costs: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.model_costs: Dict[str, float] = defaultdict(float)

    def attribute_cost(self, usage: TokenUsage) -> CostAttribution:
        """
        Attribute cost for token usage to an agent.
        
        Args:
            usage: TokenUsage object with token metrics
            
        Returns:
            CostAttribution object with calculated costs
        """
        input_cost, output_cost, total_cost = self.calculator.calculate_cost(
            usage.model, usage.input_tokens, usage.output_tokens
        )

        attribution = CostAttribution(
            trace_id=usage.trace_id,
            agent_id=usage.agent_id,
            model=usage.model,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            timestamp=usage.timestamp
        )

        # Track costs
        self.attributions.append(attribution)
        self.agent_costs[usage.agent_id] += total_cost
        self.agent_model_costs[usage.agent_id][usage.model] += total_cost
        self.model_costs[usage.model] += total_cost

        return attribution

    def get_agent_cost(self, agent_id: str) -> float:
        """Get total cost for an agent."""
        return self.agent_costs.get(agent_id, 0.0)

    def get_agent_model_breakdown(self, agent_id: str) -> Dict[str, float]:
        """Get cost breakdown by model for an agent."""
        return dict(self.agent_model_costs.get(agent_id, {}))

    def get_model_cost(self, model: str) -> float:
        """Get total cost for a model."""
        return self.model_costs.get(model, 0.0)

    def get_total_cost(self) -> float:
        """Get total cost across all agents."""
        return sum(self.agent_costs.values())

    def get_summary(self) -> Dict:
        """Get comprehensive cost summary."""
        return {
            "total_cost_usd": self.get_total_cost(),
            "total_requests": len(self.attributions),
            "agent_costs": dict(self.agent_costs),
            "model_costs": dict(self.model_costs),
            "agent_model_breakdown": {
                agent_id: dict(costs)
                for agent_id, costs in self.agent_model_costs.items()
            }
        }

    def filter_by_time_range(self, start_time: float, end_time: float) -> List[CostAttribution]:
        """Get attributions within a time range."""
        return [
            a for a in self.attributions
            if start_time <= a.timestamp <= end_time
        ]

    def filter_by_agent(self, agent_id: str) -> List[CostAttribution]:
        """Get all attributions for an agent."""
        return [a for a in self.attributions if a.agent_id == agent_id]


class AnomalyDetector:
    """Detects cost anomalies using statistical methods."""

    def __init__(self, std_dev_threshold: float = 2.0, window_size: int = 20):
        """
        Initialize anomaly detector.
        
        Args:
            std_dev_threshold: Number of standard deviations for anomaly
            window_size: Number of samples for baseline calculation
        """
        self.std_dev_threshold = std_dev_threshold
        self.window_size = window_size
        self.history: Dict[str, List[float]] = defaultdict(list)
        self.anomalies: List[Dict] = []

    def detect(self, agent_id: str, cost: float, timestamp: float) -> Optional[Dict]:
        """
        Detect if a cost is anomalous for an agent.
        
        Args:
            agent_id: Agent identifier
            cost: Cost in USD
            timestamp: Unix timestamp
            
        Returns:
            Anomaly dict if detected, None otherwise
        """
        self.history[agent_id].append(cost)

        # Need baseline history
        if len(self.history[agent_id]) < self.window_size:
            return None

        recent_costs = self.history[agent_id][-self.window_size:]
        baseline_costs = self.history[agent_id][:-1]

        # Calculate statistics
        avg_cost = sum(baseline_costs) / len(baseline_costs)
        variance = sum((c - avg_cost) ** 2 for c in baseline_costs) / len(baseline_costs)
        std_dev = variance ** 0.5

        # Detect anomaly
        if std_dev == 0:
            return None

        z_score = abs(cost - avg_cost) / std_dev

        if z_score > self.std_dev_threshold:
            anomaly = {
                "agent_id": agent_id,
                "cost": cost,
                "baseline_avg": avg_cost,
                "z_score": z_score,
                "timestamp": timestamp,
                "severity": "critical" if z_score > 3 else "warning"
            }
            self.anomalies.append(anomaly)
            return anomaly

        return None

    def get_anomalies(self, agent_id: Optional[str] = None) -> List[Dict]:
        """Get detected anomalies, optionally filtered by agent."""
        if agent_id:
            return [a for a in self.anomalies if a["agent_id"] == agent_id]
        return self.anomalies


class MetricsExporter:
    """Exports metrics in Prometheus/Grafana compatible format."""

    def __init__(self, attributor: CostAttributor, detector: AnomalyDetector):
        """Initialize exporter with data sources."""
        self.attributor = attributor
        self.detector = detector

    def export_json(self) -> str:
        """Export metrics as JSON."""
        summary = self.attributor.get_summary()
        anomalies = self.detector.get_anomalies()

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cost_summary": summary,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies)
        }

        return json.dumps(metrics, indent=2)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        lines.append("# HELP agent_total_cost Total cost in USD for agent")
        lines.append("# TYPE agent_total_cost gauge")

        for agent_id, cost in self.attributor.agent_costs.items():
            lines.append(f'agent_total_cost{{agent_id="{agent_id}"}} {cost}')

        lines.append("\n# HELP model_total_cost Total cost in USD for model")
        lines.append("# TYPE model_total_cost gauge")

        for model, cost in self.attributor.model_costs.items():
            lines.append(f'model_total_cost{{model="{model}"}} {cost}')

        lines.append("\n# HELP total_cost_usd Total cost in USD")
        lines.append("# TYPE total_cost_usd gauge")
        lines.append(f"total_cost_usd {self.attributor.get_total_cost()}")

        lines.append("\n# HELP request_count Total number of requests")
        lines.append("# TYPE request_count counter")
        lines.append(f"request_count {len(self.attributor.attributions)}")

        lines.append("\n# HELP anomaly_count Total anomalies detected")
        lines.append("# TYPE anomaly_count counter")
        lines.append(f"anomaly_count {len(self.detector.anomalies)}")

        return "\n".join(lines)

    def export_grafana_dashboard(self) -> Dict:
        """Export dashboard definition for Grafana."""
        return {
            "dashboard": {
                "title": "AI Agent Token Cost Attribution",
                "panels": [
                    {
                        "title": "Total Cost by Agent",
                        "targets": [
                            {"expr": 'agent_total_cost'}
                        ]
                    },
                    {
                        "title": "Total Cost by Model",
                        "targets": [
                            {"expr": 'model_total_cost'}
                        ]
                    },
                    {
                        "title": "Cost Anomalies",
                        "targets": [
                            {"expr": 'anomaly_count'}
                        ]
                    },
                    {
                        "title": "Request Rate",
                        "targets": [
                            {"expr": 'request_count'}
                        ]
                    }
                ]
            }
        }


class ObservabilityPlatform:
    """Main platform for AI agent observability."""

    def __init__(self):
        """Initialize the observability platform."""
        self.attributor = CostAttributor()
        self.detector = AnomalyDetector()
        self.exporter = MetricsExporter(self.attributor, self.detector)
        self.traces: Dict[str, Dict] = {}

    def start_trace(self, agent_id: str, model: str) -> str:
        """Start a new trace for an agent request."""
        trace_id = str(uuid.uuid4())
        self.traces[trace_id] = {
            "agent_id": agent_id,
            "model": model,
            "start_time": time.time()
        }
        return trace_id

    def end_trace(
        self,
        trace_id: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict:
        """End a trace and attribute costs."""
        if trace_id not in self.traces:
            raise ValueError(f"Unknown trace: {trace_id}")

        trace = self.traces[trace_id]
        end_time = time.time()
        latency_ms = (end_time - trace["start_time"]) * 1000

        usage = TokenUsage(
            trace_id=trace_id,
            agent_id=trace["agent_id"],
            model=trace["model"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            timestamp=end_time,
            latency_ms=latency_ms
        )

        attribution = self.attributor.attribute_cost(usage)

        # Check for anomalies
        anomaly = self.detector.detect(
            trace["agent_id"],
            attribution.total_cost,
            end_time
        )

        result = {
            "trace_id": trace_id,
            "usage": asdict(usage),
            "attribution": asdict(attribution),
            "anomaly": asdict(anomaly) if anomaly else None
        }

        del self.traces[trace_id]
        return result

    def get_report(self) -> Dict:
        """Get comprehensive observability report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "cost_summary": self.attributor.get_summary(),
            "anomalies": self.detector.get_anomalies(),
            "metrics": {
                "json": json.loads(self.exporter.export_json()),
                "prometheus": self.exporter.export_prometheus()
            }
        }


def generate_sample_traces(platform: ObservabilityPlatform, count: int = 50) -> None:
    """Generate sample traces for demonstration."""
    agents = ["agent-search", "agent-qa", "agent-summarizer", "agent-classifier"]
    models = [
        "gpt-4", "gpt-3.5-turbo", "gpt-4-turbo",
        "claude-3-opus", "claude-3-sonnet", "palm-2"
    ]

    for i in range(count):
        agent = agents[i % len(agents)]
        model = models[i % len(models)]

        trace_id = platform.start_trace(agent, model)

        # Simulate variable token usage
        base_input = 100 + (i * 5) % 500
        base_output = 50 + (i * 3) % 300

        # Add some anomalies
        if i % 15 == 0:
            base_input *= 5
            base_output *= 5

        result = platform.end_trace(trace_id, base_input, base_output)

        if result["anomaly"]:
            print(f"⚠️  ANOMALY DETECTED: {result['anomaly']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Token cost attribution for AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 script.py --mode demo
  python3 script.py --mode report --output json
  python3 script.py --mode report --output prometheus
  python3 script.py --mode report --output grafana
        """
    )

    parser.add_argument(
        "--mode",
        choices=["demo", "report", "interactive"],
        default="demo",
        help="Operation mode"
    )
    parser.add_argument(
        "--output",
        choices=["json", "prometheus", "grafana"],
        default="json",
        help="Output format"
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=50,
        help="Number of sample traces to generate"
    )
    parser.add_argument(
        "--agent",
        help="Filter results by agent ID"
    )
    parser.add_argument(
        "--model",
        help="Filter results by model name"
    )

    args = parser.parse_args()

    platform = ObservabilityPlatform()

    if args.mode == "demo":
        print("🚀 Generating sample traces...")
        generate_sample_traces(platform, args.samples)

        print("\n📊 Cost Summary:")
        summary = platform.attributor.get_summary()
        print(json.dumps(summary, indent=2))

        print("\n🚨 Detected Anomalies:")
        anomalies = platform.detector.get_anomalies()
        if anomalies:
            for anomaly in anomalies:
                print(f"  Agent: {anomaly['agent_id']}, Cost: ${anomaly['cost']:.6f}, Z-Score: {anomaly['z_score']:.2f}, Severity: {anomaly['severity']}")
        else:
            print("  No anomalies detected")

        print("\n✅ Demo complete")

    elif args.mode == "report":
        generate_sample_traces(platform, args.samples)

        if args.output == "json":
            output = platform.exporter.export_json()
        elif args.output == "prometheus":
            output = platform.exporter.export_prometheus()
        elif args.output == "grafana":
            output = json.dumps(
                platform.exporter.export_grafana_dashboard(),
                indent=2
            )

        print(output)

    elif args.mode == "interactive":
        print("📊 Token Cost Attribution System")
        print("Available commands: trace, summary, anomalies, models, help, exit")

        while True:
            cmd = input("\n> ").strip().split()

            if not cmd:
                continue

            if cmd[0] == "trace":
                if len(cmd) < 3:
                    print("Usage: trace <agent_id> <model> [input_tokens] [output_tokens]")
                    continue
                agent_id = cmd[1]
                model = cmd[2]
                input_tokens = int(cmd[3]) if len(cmd) > 3 else 100
                output_tokens = int(cmd[4]) if len(cmd) > 4 else 50

                trace_id = platform.start_trace(agent_id, model)
                result = platform.end_trace(trace_id, input_tokens, output_tokens)
                print(f"Cost: ${result['attribution']['total_cost']:.6f}")

            elif cmd[0] == "summary":
                summary = platform.attributor.get_summary()
                print(json.dumps(summary, indent=2))

            elif cmd[0] == "anomalies":
                anomalies = platform.detector.get_anomalies()
                if anomalies:
                    print(json.dumps(anomalies, indent=2))
                else:
                    print("No anomalies detected")

            elif cmd[0] == "models":
                models = platform.attributor.calculator.get_supported_models()
                print("Supported models:")
                for model in models:
                    print(f"  - {model}")

            elif cmd[0] == "help":
                print("Commands:")
                print("  trace <agent_id> <model> [input_tokens] [output_tokens]")
                print("  summary - Show cost summary")
                print("  anomalies - Show detected anomalies")
                print("  models - List supported models")
                print("  exit - Exit interactive mode")

            elif cmd[0] == "exit":
                break

            else:
                print("Unknown command. Type 'help' for available commands.")


if __name__ == "__main__":
    main()