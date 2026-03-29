#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement model routing middleware
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-29T13:19:38.506Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement model routing middleware
Mission: LLM Inference Cost Optimizer
Agent: @bolt
Date: 2024-12-19
Description: Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics.
"""

import argparse
import json
import time
import hashlib
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from collections import defaultdict


@dataclass
class ModelConfig:
    """Configuration for an available LLM model."""
    name: str
    provider: str
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    max_input_tokens: int
    max_output_tokens: int
    latency_ms: int
    reliability_score: float


@dataclass
class RequestMetrics:
    """Metrics for a processed request."""
    timestamp: str
    model_used: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    cache_hit: bool
    latency_ms: int
    quality_tier: str


class PromptCache:
    """Simple prompt cache for deduplication."""
    
    def __init__(self, max_entries: int = 10000):
        self.cache: Dict[str, Tuple[str, int]] = {}
        self.max_entries = max_entries
        self.hits = 0
        self.misses = 0
    
    def _hash_prompt(self, prompt: str) -> str:
        """Create hash of prompt for caching."""
        return hashlib.sha256(prompt.encode()).hexdigest()
    
    def get(self, prompt: str) -> Optional[str]:
        """Try to get cached response."""
        hash_key = self._hash_prompt(prompt)
        if hash_key in self.cache:
            self.hits += 1
            response, tokens = self.cache[hash_key]
            return response
        self.misses += 1
        return None
    
    def put(self, prompt: str, response: str, output_tokens: int) -> None:
        """Cache a response."""
        if len(self.cache) >= self.max_entries:
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        hash_key = self._hash_prompt(prompt)
        self.cache[hash_key] = (response, output_tokens)
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cached_entries": len(self.cache)
        }


class ModelRouter:
    """Routes requests to optimal models based on cost, quality, and constraints."""
    
    def __init__(self, models: List[ModelConfig], enable_caching: bool = True):
        self.models = {m.name: m for m in models}
        self.cache = PromptCache() if enable_caching else None
        self.metrics: List[RequestMetrics] = []
        self.cost_by_model: Dict[str, float] = defaultdict(float)
        self.request_count_by_model: Dict[str, int] = defaultdict(int)
    
    def estimate_tokens(self, prompt: str, estimate_output: bool = False) -> int:
        """Rough estimation of tokens (1 token ≈ 4 chars)."""
        token_count = max(1, len(prompt) // 4)
        if estimate_output:
            return max(10, token_count // 2)
        return token_count
    
    def filter_suitable_models(
        self,
        prompt: str,
        quality_tier: str = "standard",
        max_latency_ms: Optional[int] = None
    ) -> List[Tuple[str, ModelConfig]]:
        """Filter models that meet requirements."""
        input_tokens = self.estimate_tokens(prompt)
        suitable = []
        
        for name, config in self.models.items():
            if input_tokens > config.max_input_tokens:
                continue
            
            if quality_tier == "high" and config.reliability_score < 0.95:
                continue
            elif quality_tier == "low" and config.reliability_score < 0.85:
                continue
            
            if max_latency_ms and config.latency_ms > max_latency_ms:
                continue
            
            suitable.append((name, config))
        
        return suitable
    
    def calculate_request_cost(self, config: ModelConfig, input_tokens: int, output_tokens: int) -> Tuple[float, float, float]:
        """Calculate costs for a request."""
        input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens
        total_cost = input_cost + output_cost
        return input_cost, output_cost, total_cost
    
    def route_request(
        self,
        prompt: str,
        quality_tier: str = "standard",
        max_latency_ms: Optional[int] = None,
        use_cache: bool = True
    ) -> Dict:
        """Route a request to the optimal model."""
        
        if use_cache and self.cache:
            cached_response = self.cache.get(prompt)
            if cached_response:
                return {
                    "cached": True,
                    "model": "cache",
                    "response": cached_response,
                    "cost": 0.0
                }
        
        suitable_models = self.filter_suitable_models(prompt, quality_tier, max_latency_ms)
        
        if not suitable_models:
            return {
                "error": "No suitable models found for the given constraints",
                "quality_tier": quality_tier,
                "max_latency_ms": max_latency_ms
            }
        
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = self.estimate_tokens(prompt, estimate_output=True)
        
        best_model = None
        best_cost = float('inf')
        best_config = None
        
        for model_name, config in suitable_models:
            _, _, total_cost = self.calculate_request_cost(config, input_tokens, output_tokens)
            if total_cost < best_cost:
                best_cost = total_cost
                best_model = model_name
                best_config = config
        
        input_cost, output_cost, total_cost = self.calculate_request_cost(best_config, input_tokens, output_tokens)
        
        response = f"Response from {best_model}"
        
        if self.cache:
            self.cache.put(prompt, response, output_tokens)
        
        self.cost_by_model[best_model] += total_cost
        self.request_count_by_model[best_model] += 1
        
        metric = RequestMetrics(
            timestamp=datetime.utcnow().isoformat(),
            model_used=best_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=round(input_cost, 6),
            output_cost=round(output_cost, 6),
            total_cost=round(total_cost, 6),
            cache_hit=False,
            latency_ms=best_config.latency_ms,
            quality_tier=quality_tier
        )
        self.metrics.append(metric)
        
        return {
            "cached": False,
            "model": best_model,
            "response": response,
            "cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": best_config.latency_ms,
            "quality_tier": quality_tier
        }
    
    def get_analytics(self) -> Dict:
        """Get real-time cost analytics."""
        total_cost = sum(self.cost_by_model.values())
        total_requests = sum(self.request_count_by_model.values())
        
        model_stats = {}
        for model_name in self.cost_by_model:
            count = self.request_count_by_model[model_name]
            cost = self.cost_by_model[model_name]
            model_stats[model_name] = {
                "total_requests": count,
                "total_cost": round(cost, 6),
                "average_cost_per_request": round(cost / count, 6) if count > 0 else 0,
                "percentage_of_total_cost": round(cost / total_cost * 100, 2) if total_cost > 0 else 0
            }
        
        cache_stats = self.cache.get_stats() if self.cache else None
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_requests": total_requests,
            "total_cost": round(total_cost, 6),
            "average_cost_per_request": round(total_cost / total_requests, 6) if total_requests > 0 else 0,
            "model_statistics": model_stats,
            "cache_statistics": cache_stats,
            "recent_metrics": [asdict(m) for m in self.metrics[-10:]]
        }


class CostOptimizer:
    """Main orchestrator for cost optimization."""
    
    def __init__(self, router: ModelRouter):
        self.router = router
    
    def process_batch(self, requests: List[Dict]) -> Dict:
        """Process batch of requests and return analytics."""
        results = []
        for req in requests:
            result = self.router.route_request(
                prompt=req.get("prompt", ""),
                quality_tier=req.get("quality_tier", "standard"),
                max_latency_ms=req.get("max_latency_ms"),
                use_cache=req.get("use_cache", True)
            )
            results.append(result)
        
        return {
            "processed_requests": len(results),
            "results": results,
            "analytics": self.router.get_analytics()
        }
    
    def recommend_model_for_requirements(self, quality_tier: str, max_latency_ms: Optional[int] = None) -> Dict:
        """Recommend best model for specific requirements."""
        test_prompt = "test"
        suitable = self.router.filter_suitable_models(test_prompt, quality_tier, max_latency_ms)
        
        if not suitable:
            return {"recommendation": None, "reason": "No models match requirements"}
        
        recommendations = []
        for model_name, config in suitable:
            input_tokens = self.router.estimate_tokens(test_prompt)
            output_tokens = self.router.estimate_tokens(test_prompt, estimate_output=True)
            _, _, cost = self.router.calculate_request_cost(config, input_tokens, output_tokens)
            
            recommendations.append({
                "model": model_name,
                "provider": config.provider,
                "estimated_cost": round(cost, 6),
                "latency_ms": config.latency_ms,
                "reliability": config.reliability_score
            })
        
        recommendations.sort(key=lambda x: x["estimated_cost"])
        
        return {
            "recommendation": recommendations[0] if recommendations else None,
            "alternatives": recommendations[1:],
            "quality_tier": quality_tier
        }


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Optimizer - Model Routing Middleware"
    )
    parser.add_argument(
        "--enable-caching",
        action="store_true",
        default=True,
        help="Enable prompt caching (default: True)"
    )
    parser.add_argument(
        "--quality-tier",
        choices=["low", "standard", "high"],
        default="standard",
        help="Quality tier for model selection (default: standard)"
    )
    parser.add_argument(
        "--max-latency",
        type=int,
        default=None,
        help="Maximum acceptable latency in milliseconds"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of requests to process in demo (default: 5)"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format for analytics (default: pretty)"
    )
    
    args = parser.parse_args()
    
    models = [
        ModelConfig(
            name="GPT-4",
            provider="OpenAI",
            cost_per_1k_input_tokens=0.03,
            cost_per_1k_output_tokens=0.06,
            max_input_tokens=8192,
            max_output_tokens=4096,
            latency_ms=800,
            reliability_score=0.99
        ),
        ModelConfig(
            name="GPT-3.5-Turbo",
            provider="OpenAI",
            cost_per_1k_input_tokens=0.0005,
            cost_per_1k_output_tokens=0.0015,
            max_input_tokens=4096,
            max_output_tokens=2048,
            latency_ms=200,
            reliability_score=0.97
        ),
        ModelConfig(
            name="Claude-2",
            provider="Anthropic",
            cost_per_1k_input_tokens=0.008,
            cost_per_1k_output_tokens=0.024,
            max_input_tokens=100000,
            max_output_tokens=4096,
            latency_ms=1200,
            reliability_score=0.98
        ),
        ModelConfig(
            name="LLaMA-2-7B",
            provider="Meta",
            cost_per_1k_input_tokens=0.0001,
            cost_per_1k_output_tokens=0.0002,
            max_input_tokens=4096,
            max_output_tokens=2048,
            latency_ms=150,
            reliability_score=0.88
        ),
        ModelConfig(
            name="Gemini-Pro",
            provider="Google",
            cost_per_1k_input_tokens=0.001,
            cost_per_1k_output_tokens=0.002,
            max_input_tokens=32768,
            max_output_tokens=8192,
            latency_ms=400,
            reliability_score=0.96
        ),
    ]
    
    router = ModelRouter(models, enable_caching=args.enable_caching)
    optimizer = CostOptimizer(router)
    
    print("\n" + "="*70)
    print("LLM INFERENCE COST OPTIMIZER - Model Routing Middleware")
    print("="*70)
    
    sample_requests = [
        {
            "prompt": "Explain machine learning in simple terms",
            "quality_tier": args.quality_tier,
            "max_latency_ms": args.max_latency,
            "use_cache": True
        },
        {
            "prompt": "Write a Python function for binary search",
            "quality_tier": args.quality_tier,
            "max_latency_ms": args.max_latency,
            "use_cache": True
        },
        {
            "prompt": "Explain machine learning in simple terms",
            "quality_tier": args.quality_tier,
            "max_latency_ms": args.max_latency,
            "use_cache": True
        },
        {
            "prompt": "What is quantum computing?",
            "quality_tier": args.quality_tier,
            "max_latency_ms": args.max_latency,