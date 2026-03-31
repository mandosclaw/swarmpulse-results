#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement model routing middleware
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-31T18:48:17.186Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement model routing middleware
MISSION: LLM Inference Cost Optimizer
AGENT: @bolt
DATE: 2024

Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics.
"""

import argparse
import json
import hashlib
import time
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Tuple
from collections import defaultdict
from enum import Enum


class ModelTier(Enum):
    """Model capability tiers for routing."""
    LITE = "lite"
    STANDARD = "standard"
    ADVANCED = "advanced"
    PREMIUM = "premium"


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    name: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    latency_ms: int
    max_tokens: int
    capabilities: List[str] = field(default_factory=list)


@dataclass
class CacheEntry:
    """Cached prompt response."""
    prompt_hash: str
    response: str
    tokens_saved: int
    cached_at: float
    ttl_seconds: int
    tier_required: ModelTier


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    request_id: str
    prompt: str
    model_selected: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    cache_hit: bool
    tier_required: ModelTier
    timestamp: float


class PromptCache:
    """In-memory prompt cache with TTL support."""

    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get_hash(self, prompt: str) -> str:
        """Generate hash of prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def put(
        self,
        prompt: str,
        response: str,
        tokens_saved: int,
        tier_required: ModelTier,
        ttl_seconds: int = 3600,
    ) -> None:
        """Store prompt and response in cache."""
        if len(self.cache) >= self.max_size:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].cached_at,
            )
            del self.cache[oldest_key]

        prompt_hash = self.get_hash(prompt)
        self.cache[prompt_hash] = CacheEntry(
            prompt_hash=prompt_hash,
            response=response,
            tokens_saved=tokens_saved,
            cached_at=time.time(),
            ttl_seconds=ttl_seconds,
            tier_required=tier_required,
        )

    def get(self, prompt: str, required_tier: ModelTier) -> Optional[str]:
        """Retrieve cached response if available and valid."""
        prompt_hash = self.get_hash(prompt)

        if prompt_hash not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[prompt_hash]

        if time.time() - entry.cached_at > entry.ttl_seconds:
            del self.cache[prompt_hash]
            self.misses += 1
            return None

        if not self._tier_sufficient(entry.tier_required, required_tier):
            self.misses += 1
            return None

        self.hits += 1
        return entry.response

    def _tier_sufficient(self, cached_tier: ModelTier, required_tier: ModelTier) -> bool:
        """Check if cached response is from sufficient tier."""
        tier_rank = {
            ModelTier.LITE: 1,
            ModelTier.STANDARD: 2,
            ModelTier.ADVANCED: 3,
            ModelTier.PREMIUM: 4,
        }
        return tier_rank[cached_tier] >= tier_rank[required_tier]

    def stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "size": len(self.cache),
            "max_size": self.max_size,
        }

    def clear_expired(self) -> int:
        """Remove expired entries and return count removed."""
        now = time.time()
        expired_keys = [
            k
            for k, v in self.cache.items()
            if now - v.cached_at > v.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
        return len(expired_keys)


class ModelRouter:
    """Routes requests to optimal model based on cost and requirements."""

    def __init__(self, models: List[ModelConfig]):
        self.models = {m.name: m for m in models}
        self.cache = PromptCache()
        self.request_log: List[RequestMetrics] = []
        self.cost_by_model: Dict[str, float] = defaultdict(float)
        self.request_count_by_model: Dict[str, int] = defaultdict(int)

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token on average)."""
        return max(1, len(text) // 4)

    def calculate_cost(
        self,
        model: ModelConfig,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for a request."""
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output
        return input_cost + output_cost

    def select_model(
        self,
        required_tier: ModelTier,
        capabilities_needed: Optional[List[str]] = None,
    ) -> Optional[ModelConfig]:
        """Select cheapest model meeting requirements."""
        candidates = []

        for model in self.models.values():
            tier_rank = {
                ModelTier.LITE: 1,
                ModelTier.STANDARD: 2,
                ModelTier.ADVANCED: 3,
                ModelTier.PREMIUM: 4,
            }

            if tier_rank[model.tier] < tier_rank[required_tier]:
                continue

            if capabilities_needed:
                if not all(cap in model.capabilities for cap in capabilities_needed):
                    continue

            candidates.append(model)

        if not candidates:
            return None

        return min(candidates, key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)

    def process_request(
        self,
        request_id: str,
        prompt: str,
        required_tier: ModelTier = ModelTier.STANDARD,
        capabilities_needed: Optional[List[str]] = None,
        expected_output_length: int = 100,
    ) -> Tuple[Optional[str], RequestMetrics]:
        """Process a request with caching and routing."""

        cache_hit = False
        cached_response = self.cache.get(prompt, required_tier)

        if cached_response:
            cache_hit = True
            input_tokens = self.estimate_tokens(prompt)
            output_tokens = self.estimate_tokens(cached_response)
            model = self.select_model(required_tier, capabilities_needed)

            if model:
                cost = self.calculate_cost(model, 0, 0)
                metrics = RequestMetrics(
                    request_id=request_id,
                    prompt=prompt,
                    model_selected=model.name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    latency_ms=1.0,
                    cache_hit=True,
                    tier_required=required_tier,
                    timestamp=time.time(),
                )
                self.request_log.append(metrics)
                return cached_response, metrics

        model = self.select_model(required_tier, capabilities_needed)

        if not model:
            return None, None

        input_tokens = self.estimate_tokens(prompt)
        output_tokens = expected_output_length

        cost = self.calculate_cost(model, input_tokens, output_tokens)

        start_time = time.time()
        response = self._simulate_inference(model, prompt, output_tokens)
        latency_ms = (time.time() - start_time) * 1000

        self.cache.put(
            prompt,
            response,
            input_tokens,
            required_tier,
            ttl_seconds=3600,
        )

        metrics = RequestMetrics(
            request_id=request_id,
            prompt=prompt,
            model_selected=model.name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            tier_required=required_tier,
            timestamp=time.time(),
        )

        self.request_log.append(metrics)
        self.cost_by_model[model.name] += cost
        self.request_count_by_model[model.name] += 1

        return response, metrics

    def _simulate_inference(
        self,
        model: ModelConfig,
        prompt: str,
        output_tokens: int,
    ) -> str:
        """Simulate LLM inference with realistic latency."""
        time.sleep(model.latency_ms / 1000.0)
        return f"[{model.name}] Response to: {prompt[:50]}..." + " " * output_tokens

    def get_analytics(self, time_window_minutes: int = 60) -> Dict:
        """Generate real-time cost analytics."""
        cutoff_time = time.time() - (time_window_minutes * 60)
        recent_requests = [r for r in self.request_log if r.timestamp >= cutoff_time]

        if not recent_requests:
            return {
                "time_window_minutes": time_window_minutes,
                "requests_processed": 0,
                "total_cost": 0,
                "cache_hit_rate": 0,
                "cost_by_model": {},
                "avg_cost_per_request": 0,
                "cache_stats": self.cache.stats(),
            }

        total_cost = sum(r.cost for r in recent_requests)
        cache_hits = sum(1 for r in recent_requests if r.cache_hit)
        cache_hit_rate = cache_hits / len(recent_requests) if recent_requests else 0

        cost_by_model = defaultdict(float)
        for req in recent_requests:
            cost_by_model[req.model_selected] += req.cost

        avg_latencies = defaultdict(list)
        for req in recent_requests:
            avg_latencies[req.model_selected].append(req.latency_ms)

        model_stats = {}
        for model_name, latencies in avg_latencies.items():
            model_stats[model_name] = {
                "requests": len(latencies),
                "avg_latency_ms": statistics.mean(latencies),
                "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)]
                if latencies
                else 0,
                "total_cost": cost_by_model[model_name],
            }

        return {
            "time_window_minutes": time_window_minutes,
            "requests_processed": len(recent_requests),
            "total_cost": round(total_cost, 6),
            "avg_cost_per_request": round(total_cost / len(recent_requests), 6)
            if recent_requests
            else 0,
            "cache_hit_rate": round(cache_hit_rate, 4),
            "cache_stats": self.cache.stats(),
            "model_stats": model_stats,
        }

    def get_cost_comparison(
        self,
        prompt: str,
        required_tier: ModelTier = ModelTier.STANDARD,
        expected_output_length: int = 100,
    ) -> List[Dict]:
        """Compare costs across all suitable models."""
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = expected_output_length

        comparison = []
        for model in self.models.values():
            tier_rank = {
                ModelTier.LITE: 1,
                ModelTier.STANDARD: 2,
                ModelTier.ADVANCED: 3,
                ModelTier.PREMIUM: 4,
            }

            if tier_rank[model.tier] < tier_rank[required_tier]:
                continue

            cost = self.calculate_cost(model, input_tokens, output_tokens)
            comparison.append(
                {
                    "model": model.name,
                    "tier": model.tier.value,
                    "cost": round(cost, 6),
                    "latency_ms": model.latency_ms,
                    "capabilities": model.capabilities,
                }
            )

        return sorted(comparison, key=lambda x: x["cost"])


def setup_default_models() -> List[ModelConfig]:
    """Create default model configurations."""
    return [
        ModelConfig(
            name="gpt-4-turbo",
            tier=ModelTier.PREMIUM,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
            latency_ms=500,
            max_tokens=128000,
            capabilities=[
                "reasoning",
                "code-generation",
                "vision",
                "function-calling",
            ],
        ),
        ModelConfig(
            name="gpt-4",
            tier=ModelTier.ADVANCED,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.006,
            latency_ms=400,
            max_tokens=8192,
            capabilities=["reasoning", "code-generation", "function-calling"],
        ),
        ModelConfig(
            name="gpt-3.5-turbo",
            tier=ModelTier.STANDARD,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            latency_ms=200,
            max_tokens=4096,
            capabilities=["code-generation", "function-calling"],
        ),
        ModelConfig(
            name="claude-instant",
            tier=ModelTier.LITE,
            cost_per_1k_input=0.0008,
            cost_per_1k_output=0.0024,
            latency_ms=150,
            max_tokens=3000,
            capabilities=["code-generation"],
        ),
        ModelConfig(
            name="llama-2-7b",
            tier=ModelTier.LITE,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0002,
            latency_ms=300,
            max_tokens=2048,
            capabilities=["text-generation"],
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Optimizer - Model Routing Middleware"
    )
    parser.add_argument(
        "--mode",
        choices=["route", "analytics", "compare", "demo"],
        default="demo",
        help="Operation mode",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="What are the best practices for Python development?",
        help="Prompt to process",
    )
    parser.add_argument(
        "--tier",
        choices=["lite", "standard", "advanced", "premium"],
        default="standard",
        help="Required model tier",
    )
    parser.add_argument(
        "--output-length",
        type=int,
        default=100,
        help="Expected output token length",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10,
        help="Number of demo requests to process",
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=3600,
        help="Cache TTL in seconds",
    )

    args = parser.parse_args()

    models = setup_default_models()
    router = ModelRouter(models)

    tier_map = {
        "lite": ModelTier.LITE,
        "standard": ModelTier.STANDARD,
        "advanced": ModelTier.ADVANCED,
        "premium": ModelTier.PREMIUM,
    }
    required_tier = tier_map[args.tier]

    if args.mode == "route":
        print(f"Processing request with tier: {args.tier}")
        response, metrics = router.process_request(
            request_id="req-001",
            prompt=args.prompt,
            required_tier=required_tier,
            expected_output_length=args.output_length,
        )
        if metrics:
            print(json.dumps(asdict(metrics), indent=2, default=str))
        else:
            print("No suitable model found")

    elif args.mode == "compare":
        print(f"Cost comparison for tier: {args.tier}")
        comparison = router.get_cost_comparison(
            prompt=args.prompt,
            required_tier=required_tier,
            expected_output_length=args.output_length,
        )
        print(json.dumps(comparison, indent=2))

    elif args.mode == "analytics":
        analytics = router.get_analytics(time_window_minutes=60)
        print(json.dumps(analytics, indent=2))

    elif args.mode == "demo":
        print("Starting LLM Inference Cost Optimizer Demo\n")
        print("=" * 70)

        demo_prompts = [
            "Explain quantum computing in simple terms.",
            "Write a Python function for binary search.",
            "What are microservices?",
            "Explain quantum computing in simple terms.",
            "Write a Python function for quicksort.",
        ]

        print(f"\nProcessing {args.requests} demo requests...\n")
        for i in range(args.requests):
            prompt = demo_prompts[i % len(demo_prompts)]
            request_id = f"demo-req-{i+1:03d}"

            response, metrics = router.process_request(
                request_id=request_id,
                prompt=prompt,
                required_tier=required_tier,
                expected_output_length=args.output_length,
            )

            if metrics:
                status = "CACHED" if metrics.cache_hit else "FRESH"
                print(
                    f"[{request_id}] {status:6s} | Model: {metrics.model_selected:20s} | "
                    f"Cost: ${metrics.cost:.6f} | Latency: {metrics.latency_ms:.2f}ms"
                )

        print("\n" + "=" * 70)
        print("\nCost Analytics (Last 60 minutes):\n")
        analytics = router.get_analytics(time_window_minutes=60)
        print(json.dumps(analytics, indent=2))

        print("\n" + "=" * 70)
        print("\nModel Cost Comparison:\n")
        comparison = router.get_cost_comparison(
            prompt=demo_prompts[0],
            required_tier=required_tier,
            expected_output_length=args.output_length,
        )
        for item in comparison:
            print(
                f"  {item['model']:20s} | Tier: {item['tier']:10s} | "
                f"Cost: ${item['cost']:.6f} | Latency: {item['latency_ms']}ms"
            )

        print("\n" + "=" * 70)


if __name__ == "__main__":
    main()