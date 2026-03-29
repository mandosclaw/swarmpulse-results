#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build complexity classifier
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-29T13:19:41.607Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build complexity classifier for LLM Inference Cost Optimizer
Mission: LLM Inference Cost Optimizer
Agent: @bolt
Date: 2024-01-15

Implements a complexity classifier that analyzes prompts and requests to categorize
their computational difficulty, enabling intelligent routing to cost-appropriate models.
"""

import argparse
import json
import sys
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple
from enum import Enum
import math


class ComplexityLevel(Enum):
    """Enumeration of complexity levels."""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ComplexityMetrics:
    """Metrics computed for complexity classification."""
    token_estimate: int
    semantic_density: float
    reasoning_indicators: int
    computational_markers: int
    structural_complexity: float
    vocabulary_diversity: float
    overall_score: float
    classified_level: ComplexityLevel


class ComplexityClassifier:
    """Classifies LLM request complexity for cost optimization routing."""

    def __init__(
        self,
        min_score: float = 0.0,
        max_score: float = 100.0,
        enable_cache_analysis: bool = True
    ):
        """
        Initialize the complexity classifier.
        
        Args:
            min_score: Minimum complexity score (default 0.0)
            max_score: Maximum complexity score (default 100.0)
            enable_cache_analysis: Whether to analyze cache opportunities
        """
        self.min_score = min_score
        self.max_score = max_score
        self.enable_cache_analysis = enable_cache_analysis
        
        # Reasoning indicators that signal higher complexity
        self.reasoning_keywords = {
            "analyze": 2,
            "evaluate": 2,
            "reasoning": 3,
            "logical": 2,
            "explain": 2,
            "justify": 2,
            "compare": 2,
            "contrast": 2,
            "synthesize": 3,
            "integrate": 3,
            "derive": 3,
            "prove": 3,
            "deduce": 3,
            "infer": 2,
            "abstract": 3,
            "recursive": 4,
            "algorithm": 3,
            "optimize": 3,
            "complex": 2,
        }
        
        # Computational/technical markers
        self.computational_keywords = {
            "code": 2,
            "program": 2,
            "algorithm": 3,
            "data structure": 3,
            "math": 2,
            "calculus": 3,
            "linear algebra": 3,
            "probability": 3,
            "statistics": 2,
            "machine learning": 4,
            "neural network": 4,
            "optimization": 3,
            "sql": 2,
            "database": 2,
            "api": 2,
            "architecture": 3,
            "system design": 4,
        }
        
        # Caching-friendly patterns
        self.cache_patterns = {
            "system prompt": 5,
            "instructions": 4,
            "rules": 4,
            "guidelines": 4,
            "context": 3,
        }

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using simple approximation (4 chars ≈ 1 token).
        
        Args:
            text: Input text to estimate
            
        Returns:
            Estimated token count
        """
        words = len(text.split())
        chars = len(text)
        return max(words // 4 + 1, chars // 4)

    def _calculate_semantic_density(self, text: str) -> float:
        """
        Calculate semantic density based on unique terms and complexity.
        
        Args:
            text: Input text
            
        Returns:
            Semantic density score (0.0-1.0)
        """
        words = text.lower().split()
        if not words:
            return 0.0
        
        unique_words = len(set(words))
        unique_ratio = unique_words / len(words)
        
        # Longer texts with diverse vocabulary have higher semantic density
        avg_word_length = sum(len(w) for w in words) / len(words)
        word_complexity_factor = min(avg_word_length / 10.0, 1.0)
        
        density = (unique_ratio * 0.6) + (word_complexity_factor * 0.4)
        return min(density, 1.0)

    def _count_reasoning_indicators(self, text: str) -> int:
        """
        Count reasoning-related keywords in text.
        
        Args:
            text: Input text
            
        Returns:
            Count of reasoning indicators weighted by importance
        """
        text_lower = text.lower()
        count = 0
        
        for keyword, weight in self.reasoning_keywords.items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            count += matches * weight
        
        return count

    def _count_computational_markers(self, text: str) -> int:
        """
        Count computational/technical keywords in text.
        
        Args:
            text: Input text
            
        Returns:
            Count of computational markers weighted by importance
        """
        text_lower = text.lower()
        count = 0
        
        for keyword, weight in self.computational_keywords.items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = len(re.findall(pattern, text_lower))
            count += matches * weight
        
        return count

    def _calculate_structural_complexity(self, text: str) -> float:
        """
        Calculate structural complexity from formatting and nesting.
        
        Args:
            text: Input text
            
        Returns:
            Structural complexity score (0.0-1.0)
        """
        complexity = 0.0
        
        # Check for lists and structured formatting
        list_markers = len(re.findall(r'^[\s]*([-*•]|\d+\.)', text, re.MULTILINE))
        complexity += min(list_markers / 10.0, 0.2)
        
        # Check for code blocks
        code_blocks = len(re.findall(r'```|<code>|`', text))
        complexity += min(code_blocks / 5.0, 0.2)
        
        # Check for nested structures (parens, brackets)
        nested_depth = 0
        max_depth = 0
        for char in text:
            if char in '([{':
                nested_depth += 1
                max_depth = max(max_depth, nested_depth)
            elif char in ')]}':
                nested_depth = max(0, nested_depth - 1)
        
        complexity += min(max_depth / 10.0, 0.3)
        
        # Check for line breaks and sections
        lines = text.split('\n')
        if len(lines) > 1:
            complexity += min(len(lines) / 100.0, 0.3)
        
        return min(complexity, 1.0)

    def _calculate_vocabulary_diversity(self, text: str) -> float:
        """
        Calculate vocabulary diversity using type-token ratio.
        
        Args:
            text: Input text
            
        Returns:
            Vocabulary diversity score (0.0-1.0)
        """
        words = [w.lower() for w in re.findall(r'\b\w+\b', text)]
        if not words:
            return 0.0
        
        unique_words = len(set(words))
        type_token_ratio = unique_words / len(words)
        
        return min(type_token_ratio, 1.0)

    def _classify_level(self, score: float) -> ComplexityLevel:
        """
        Classify complexity level based on score.
        
        Args:
            score: Complexity score (0.0-100.0)
            
        Returns:
            Classified complexity level
        """
        if score < 15:
            return ComplexityLevel.MINIMAL
        elif score < 30:
            return ComplexityLevel.LOW
        elif score < 55:
            return ComplexityLevel.MEDIUM
        elif score < 80:
            return ComplexityLevel.HIGH
        else:
            return ComplexityLevel.CRITICAL

    def classify(self, prompt: str, system_prompt: str = "") -> ComplexityMetrics:
        """
        Classify the complexity of an LLM request.
        
        Args:
            prompt: Main user prompt/request
            system_prompt: Optional system prompt
            
        Returns:
            ComplexityMetrics with detailed classification
        """
        full_text = f"{system_prompt}\n{prompt}" if system_prompt else prompt
        
        # Calculate individual metrics
        token_estimate = self._estimate_tokens(full_text)
        semantic_density = self._calculate_semantic_density(full_text)
        reasoning_indicators = self._count_reasoning_indicators(full_text)
        computational_markers = self._count_computational_markers(full_text)
        structural_complexity = self._calculate_structural_complexity(full_text)
        vocabulary_diversity = self._calculate_vocabulary_diversity(full_text)
        
        # Compute overall complexity score
        # Normalize indicators to 0-1 range
        reasoning_score = min(reasoning_indicators / 20.0, 1.0)
        computational_score = min(computational_markers / 15.0, 1.0)
        token_score = min(token_estimate / 2000.0, 1.0)
        
        # Weighted combination
        overall_score = (
            semantic_density * 0.15 +
            reasoning_score * 0.25 +
            computational_score * 0.20 +
            token_score * 0.15 +
            structural_complexity * 0.15 +
            vocabulary_diversity * 0.10
        ) * 100
        
        overall_score = max(self.min_score, min(overall_score, self.max_score))
        classified_level = self._classify_level(overall_score)
        
        return ComplexityMetrics(
            token_estimate=token_estimate,
            semantic_density=semantic_density,
            reasoning_indicators=reasoning_indicators,
            computational_markers=computational_markers,
            structural_complexity=structural_complexity,
            vocabulary_diversity=vocabulary_diversity,
            overall_score=overall_score,
            classified_level=classified_level
        )

    def get_recommended_model(self, metrics: ComplexityMetrics) -> Dict[str, str]:
        """
        Recommend a model tier based on complexity metrics.
        
        Args:
            metrics: ComplexityMetrics from classification
            
        Returns:
            Dictionary with model recommendations
        """
        recommendations = {
            ComplexityLevel.MINIMAL: "gpt-3.5-turbo",
            ComplexityLevel.LOW: "gpt-3.5-turbo",
            ComplexityLevel.MEDIUM: "gpt-4-turbo",
            ComplexityLevel.HIGH: "gpt-4",
            ComplexityLevel.CRITICAL: "gpt-4-32k"
        }
        
        return {
            "recommended_model": recommendations[metrics.classified_level],
            "complexity_level": metrics.classified_level.value,
            "reason": f"Complexity score {metrics.overall_score:.1f} classified as {metrics.classified_level.value}"
        }

    def estimate_cost(self, metrics: ComplexityMetrics) -> Dict[str, float]:
        """
        Estimate inference cost based on metrics.
        
        Args:
            metrics: ComplexityMetrics from classification
            
        Returns:
            Dictionary with cost estimates
        """
        # Approximate pricing per 1K tokens (as of reference date)
        pricing = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4-turbo": {"input": 0.001, "output": 0.003},
            "gpt-4": {"input": 0.003, "output": 0.006},
            "gpt-4-32k": {"input": 0.006, "output": 0.012}
        }
        
        recommendation = self.get_recommended_model(metrics)
        model = recommendation["recommended_model"]
        model_pricing = pricing.get(model, pricing["gpt-3.5-turbo"])
        
        # Estimate input and output tokens
        input_tokens = metrics.token_estimate
        output_tokens = int(metrics.token_estimate * 0.5)  # Heuristic
        
        input_cost = (input_tokens / 1000.0) * model_pricing["input"]
        output_cost = (output_tokens / 1000.0) * model_pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "estimated_input_tokens": input_tokens,
            "estimated_output_tokens": output_tokens,
            "estimated_input_cost": round(input_cost, 6),
            "estimated_output_cost": round(output_cost, 6),
            "estimated_total_cost": round(total_cost, 6),
            "currency": "USD"
        }

    def analyze_for_caching(self, system_prompt: str = "", prompt: str = "") -> Dict[str, any]:
        """
        Analyze caching opportunities in the request.
        
        Args:
            system_prompt: Optional system prompt
            prompt: Main prompt
            
        Returns:
            Dictionary with caching analysis
        """
        if not self.enable_cache_analysis:
            return {"caching_enabled": False}
        
        system_text = system_prompt.lower() if system_prompt else ""
        
        cacheable_segments = []
        cache_score = 0
        
        for pattern, weight in self.cache_patterns.items():
            if pattern in system_text:
                cacheable_segments.append(pattern)
                cache_score += weight
        
        system_token_estimate = self._estimate_tokens(system_prompt) if system_prompt else 0
        cacheable_tokens = 0
        
        if system_token_estimate > 100:
            cacheable_tokens = system_token_estimate
            cache_score += 10
        
        cache_potential = min(cache_score / 50.0, 1.0)
        
        return {
            "caching_enabled": True,
            "cacheable_segments": cacheable_segments,
            "cacheable_tokens": cacheable_tokens,
            "cache_potential": round(cache_potential, 2),
            "estimated_savings_percentage": round(cache_potential * 20, 1)
        }

    def to_dict(self, metrics: ComplexityMetrics) -> Dict:
        """
        Convert metrics to dictionary for JSON serialization.
        
        Args:
            metrics: ComplexityMetrics object
            
        Returns:
            Dictionary representation
        """
        return {
            "token_estimate": metrics.token_estimate,
            "semantic_density": round(metrics.semantic_density, 3),
            "reasoning_indicators": metrics.reasoning_indicators,
            "computational_markers": metrics.computational_markers,
            "structural_complexity": round(metrics.structural_complexity, 3),
            "vocabulary_diversity": round(metrics.vocabulary_diversity, 3),
            "overall_score": round(metrics.overall_score, 2),
            "classified_level": metrics.classified_level.value
        }


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Complexity Classifier for LLM Inference Cost Optimizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --prompt "What is 2+2?"
  %(prog)s --prompt "Analyze this code" --system-prompt "You are a code reviewer"
  %(prog)s --prompt "Complex request" --show-cost --show