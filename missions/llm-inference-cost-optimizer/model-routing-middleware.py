#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Model routing middleware
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-29T13:12:39.244Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Model routing middleware
Mission: LLM Inference Cost Optimizer
Agent: @sue
Date: 2024-01-15

LiteLLM-compatible proxy that routes LLM queries to optimal models based on
complexity analysis and per-caller cost budgets. Implements prompt caching,
semantic deduplication, and batch optimization.
"""

import argparse
import json
import hashlib
import time
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import re


@dataclass
class ModelConfig:
    """LLM model configuration with pricing and capabilities."""
    name: str
    provider: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    complexity_threshold: float
    latency_ms: int
    capabilities: List[str]


@dataclass
class RoutingDecision:
    """Result of routing decision for a query."""
    original_model: str
    routed_model: str
    complexity_score: float
    estimated_cost: float
    cache_hit: bool
    cached_response: Optional[str]
    reason: str
    timestamp: str


@dataclass
class CallerBudget:
    """Per-caller cost budget tracking."""
    caller_id: str
    monthly_budget: float
    spent_this_month: float
    queries_this_month: int
    last_reset: str


class ComplexityAnalyzer:
    """Analyzes query complexity using multiple heuristics."""
    
    def __init__(self):
        self.keyword_weights = {
            'reason': 0.3,
            'explain': 0.25,
            'analyze': 0.35,
            'compare': 0.3,
            'predict': 0.4,
            'code': 0.5,
            'algorithm': 0.45,
            'architecture': 0.4,
            'design': 0.35,
            'debug': 0.4,
            'optimize': 0.45,
            'research': 0.5,
            'novel': 0.5,
        }
    
    def calculate_complexity(self, prompt: str) -> float:
        """
        Calculate query complexity on scale 0.0 to 1.0.
        Combines multiple signals: length, keywords, structure, depth.
        """
        scores = []
        
        # Length-based complexity
        word_count = len(prompt.split())
        length_score = min(word_count / 500.0, 1.0)
        scores.append(length_score * 0.2)
        
        # Keyword-based complexity
        prompt_lower = prompt.lower()
        keyword_score = 0.0
        keyword_count = 0
        for keyword, weight in self.keyword_weights.items():
            if keyword in prompt_lower:
                keyword_score += weight
                keyword_count += 1
        if keyword_count > 0:
            keyword_score = min(keyword_score / (keyword_count * 0.5), 1.0)
        scores.append(keyword_score * 0.3)
        
        # Code/technical complexity
        code_indicators = ['```', 'def ', 'class ', 'import ', 'function', '<', '>', '{', '}']
        code_count = sum(1 for indicator in code_indicators if indicator in prompt)
        code_score = min(code_count / 5.0, 1.0)
        scores.append(code_score * 0.25)
        
        # Question depth (question marks, multiple queries)
        question_count = prompt.count('?')
        sentence_count = len(re.split(r'[.!?]+', prompt))
        depth_score = min((question_count + sentence_count - 1) / 10.0, 1.0)
        scores.append(depth_score * 0.25)
        
        return sum(scores)


class PromptCache:
    """Semantic prompt caching with hash-based deduplication."""
    
    def __init__(self, max_cache_size: int = 1000):
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.max_cache_size = max_cache_size
        self.hits = 0
        self.misses = 0
    
    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt for semantic comparison."""
        normalized = prompt.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized
    
    def _hash_prompt(self, prompt: str) -> str:
        """Generate hash of normalized prompt."""
        normalized = self._normalize_prompt(prompt)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, prompt: str) -> Optional[str]:
        """Retrieve cached response if available."""
        prompt_hash = self._hash_prompt(prompt)
        if prompt_hash in self.cache:
            response, cached_at = self.cache[prompt_hash]
            self.hits += 1
            return response
        self.misses += 1
        return None
    
    def set(self, prompt: str, response: str) -> None:
        """Cache a prompt-response pair."""
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        prompt_hash = self._hash_prompt(prompt)
        self.cache[prompt_hash] = (response, time.time())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'size': len(self.cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_percent': round(hit_rate, 2),
            'max_size': self.max_cache_size
        }


class ModelRouter:
    """Routes queries to optimal models based on complexity and cost."""
    
    def __init__(self, models: List[ModelConfig]):
        """Initialize router with available models."""
        self.models = sorted(models, key=lambda m: m.cost_per_1k_input)
        self.complexity_analyzer = ComplexityAnalyzer()
        self.prompt_cache = PromptCache(max_cache_size=5000)
        self.caller_budgets: Dict[str, CallerBudget] = {}
        self.routing_history: List[RoutingDecision] = []
        self.batch_queue: List[Tuple[str, str, str]] = []
        self.batch_threshold = 5
    
    def register_caller(self, caller_id: str, monthly_budget: float) -> None:
        """Register a caller with their monthly budget."""
        self.caller_budgets[caller_id] = CallerBudget(
            caller_id=caller_id,
            monthly_budget=monthly_budget,
            spent_this_month=0.0,
            queries_this_month=0,
            last_reset=datetime.now().isoformat()
        )
    
    def _check_budget(self, caller_id: str, estimated_cost: float) -> bool:
        """Check if caller has budget available."""
        if caller_id not in self.caller_budgets:
            return True
        
        budget = self.caller_budgets[caller_id]
        available = budget.monthly_budget - budget.spent_this_month
        return estimated_cost <= available
    
    def _estimate_cost(self, model: ModelConfig, prompt: str, 
                      estimated_output_tokens: int = 500) -> float:
        """Estimate cost for a query on a given model."""
        prompt_tokens = len(prompt.split()) * 1.3
        input_cost = (prompt_tokens / 1000) * model.cost_per_1k_input
        output_cost = (estimated_output_tokens / 1000) * model.cost_per_1k_output
        return input_cost + output_cost
    
    def route(self, prompt: str, caller_id: str = "default",
             requested_model: str = "gpt-4", cost_budget: Optional[float] = None) -> RoutingDecision:
        """
        Route a query to optimal model.
        
        Args:
            prompt: The user's query/prompt
            caller_id: Identifier for the caller/API user
            requested_model: Model caller prefers (may be downgraded)
            cost_budget: Optional override for cost budget
            
        Returns:
            RoutingDecision with routing details
        """
        timestamp = datetime.now().isoformat()
        
        # Check cache first
        cached_response = self.prompt_cache.get(prompt)
        if cached_response:
            decision = RoutingDecision(
                original_model=requested_model,
                routed_model="cache",
                complexity_score=0.0,
                estimated_cost=0.0,
                cache_hit=True,
                cached_response=cached_response,
                reason="Exact match found in prompt cache",
                timestamp=timestamp
            )
            self.routing_history.append(decision)
            return decision
        
        # Analyze complexity
        complexity_score = self.complexity_analyzer.calculate_complexity(prompt)
        
        # Find best model based on complexity and budget
        best_model = self._select_model(
            complexity_score=complexity_score,
            requested_model=requested_model,
            caller_id=caller_id,
            prompt=prompt
        )
        
        estimated_cost = self._estimate_cost(best_model, prompt)
        
        # Check caller budget
        reason = f"Complexity score: {complexity_score:.2f}"
        if not self._check_budget(caller_id, estimated_cost):
            # Fall back to cheapest model
            best_model = self.models[0]
            reason = f"Budget limit exceeded, downgraded to {best_model.name}"
        
        # Update caller budget
        if caller_id in self.caller_budgets:
            budget = self.caller_budgets[caller_id]
            budget.spent_this_month += estimated_cost
            budget.queries_this_month += 1
        
        decision = RoutingDecision(
            original_model=requested_model,
            routed_model=best_model.name,
            complexity_score=complexity_score,
            estimated_cost=estimated_cost,
            cache_hit=False,
            cached_response=None,
            reason=reason,
            timestamp=timestamp
        )
        
        self.routing_history.append(decision)
        return decision
    
    def _select_model(self, complexity_score: float, requested_model: str,
                     caller_id: str, prompt: str) -> ModelConfig:
        """Select optimal model based on multiple criteria."""
        # Find requested model
        requested = next((m for m in self.models if m.name == requested_model), None)
        
        # Determine if we should downgrade based on complexity
        for model in self.models:
            if complexity_score <= model.complexity_threshold:
                return model
        
        # If complexity requires full power, use requested if available
        if requested:
            return requested
        
        # Default to largest model
        return self.models[-1]
    
    def add_to_batch(self, prompt: str, caller_id: str, model: str) -> None:
        """Add prompt to batch queue."""
        self.batch_queue.append((prompt, caller_id, model))
    
    def process_batch(self) -> List[RoutingDecision]:
        """Process batched queries with semantic deduplication."""
        decisions = []
        seen_semantics = set()
        
        for prompt, caller_id, model in self.batch_queue:
            semantic_hash = self.prompt_cache._hash_prompt(prompt)
            
            # Skip semantic duplicates
            if semantic_hash in seen_semantics:
                continue
            seen_semantics.add(semantic_hash)
            
            decision = self.route(prompt, caller_id, model)
            decisions.append(decision)
        
        self.batch_queue = []
        return decisions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            'total_routes': len(self.routing_history),
            'cache_stats': self.prompt_cache.get_stats(),
            'callers_registered': len(self.caller_budgets),
            'recent_routes': [asdict(d) for d in self.routing_history[-10:]],
            'timestamp': datetime.now().isoformat()
        }


class LiteLLMProxy:
    """LiteLLM-compatible proxy with cost optimization."""
    
    def __init__(self, router: ModelRouter):
        self.router = router
        self.request_id_counter = 0
    
    def completion(self, model: str, messages: List[Dict], 
                  caller_id: str = "default", **kwargs) -> Dict[str, Any]:
        """
        LiteLLM-compatible completion endpoint.
        
        Args:
            model: Requested model (may be routed)
            messages: Conversation messages
            caller_id: Caller identifier
            **kwargs: Additional LiteLLM parameters
            
        Returns:
            Completion response with routing metadata
        """
        self.request_id_counter += 1
        request_id = f"req_{self.request_id_counter}_{int(time.time())}"
        
        # Combine messages into prompt
        prompt = "\n".join([m.get("content", "") for m in messages])
        
        # Route to optimal model
        routing_decision = self.router.route(
            prompt=prompt,
            caller_id=caller_id,
            requested_model=model
        )
        
        # Simulate completion
        if routing_decision.cache_hit:
            response_text = routing_decision.cached_response
        else:
            response_text = self._generate_mock_response(routing_decision.routed_model)
            self.router.prompt_cache.set(prompt, response_text)
        
        return {
            "id": request_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": routing_decision.routed_model,
            "choices": [
                {
                    "text": response_text,
                    "index": 0,
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": int(len(prompt.split()) * 1.3),
                "completion_tokens": int(len(response_text.split()) * 1.3),
                "total_tokens": int(len((prompt + response_text).split()) * 1.3)
            },
            "cost": {
                "estimated_usd": routing_decision.estimated_cost,
                "cached": routing_decision.cache_hit
            },
            "routing": asdict(routing_decision)
        }
    
    def _generate_mock_response(self, model: str) -> str:
        """Generate mock completion response."""
        responses = {
            "gpt-4": "This is a comprehensive response requiring full model capability...",
            "gpt-3.5-turbo": "This is a standard response from the turbo model...",
            "claude-3-haiku": "Brief response from Haiku model.",
            "cache": "Cached response retrieved successfully."
        }
        return responses.get(model, "Mock response from routed model.")


def create_default_models() -> List[ModelConfig]:
    """Create default model configuration."""
    return [
        ModelConfig(
            name="claude-3-haiku",
            provider="anthropic",
            cost_per_1k_input=0.08,
            cost_per_1k_output=0.24,
            max_tokens=4096,
            complexity_threshold=0.3,
            latency_ms=