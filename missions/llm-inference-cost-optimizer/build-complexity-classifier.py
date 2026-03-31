#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build complexity classifier
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-31T18:48:18.822Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build complexity classifier
Mission: LLM Inference Cost Optimizer
Agent: @bolt
Date: 2024

Intelligent middleware that classifies LLM request complexity to route to optimal models,
implements prompt caching, and provides real-time cost analytics. This module implements
a sophisticated complexity classifier using linguistic and structural features.
"""

import argparse
import json
import math
import re
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Tuple
import hashlib


class ComplexityLevel(Enum):
    """Classification levels for request complexity."""
    TRIVIAL = 1
    SIMPLE = 2
    MODERATE = 3
    COMPLEX = 4
    EXPERT = 5


@dataclass
class ComplexityFeatures:
    """Extracted features for complexity analysis."""
    token_count: int
    sentence_count: int
    avg_sentence_length: int
    avg_word_length: float
    vocabulary_richness: float
    punctuation_density: float
    technical_term_count: int
    logical_operator_count: int
    question_count: int
    conditional_count: int
    numerical_content_density: float
    structural_depth: int
    code_block_presence: bool
    code_block_count: int
    list_structure_count: int
    nested_structure_depth: int


class ComplexityClassifier:
    """Classifies LLM request complexity for optimal model routing."""

    def __init__(self, cache_enabled: bool = True, verbose: bool = False):
        """
        Initialize complexity classifier.

        Args:
            cache_enabled: Enable result caching based on prompt hash
            verbose: Enable detailed logging
        """
        self.cache_enabled = cache_enabled
        self.verbose = verbose
        self.cache: Dict[str, Tuple[ComplexityLevel, float]] = {}
        self.technical_terms = self._load_technical_terms()
        self.complexity_scores: List[float] = []

    def _load_technical_terms(self) -> set:
        """Load common technical terms for detection."""
        return {
            'algorithm', 'architecture', 'authentication', 'benchmark', 'blockchain',
            'cache', 'circuit', 'cluster', 'compilation', 'concurrency', 'containerization',
            'cryptography', 'database', 'debugging', 'deployment', 'distributed',
            'encryption', 'framework', 'gateway', 'gpu', 'hash', 'hyperparameter',
            'infrastructure', 'integration', 'kernel', 'latency', 'middleware',
            'microservice', 'neural', 'optimization', 'orchestration', 'parallel',
            'pipeline', 'protocol', 'quantum', 'queue', 'recursion', 'regex',
            'repository', 'scheduler', 'serialization', 'simulation', 'synchronization',
            'throughput', 'topology', 'transaction', 'vector', 'virtualization',
            'machine learning', 'deep learning', 'reinforcement learning',
            'natural language', 'computer vision', 'nlp', 'api', 'rest', 'graphql',
            'sql', 'nosql', 'json', 'xml', 'http', 'https', 'tcp', 'udp',
            'javascript', 'python', 'java', 'rust', 'golang', 'typescript',
            'kubernetes', 'docker', 'terraform', 'ansible', 'jenkins',
            'prometheus', 'grafana', 'elasticsearch', 'kafka', 'redis',
        }

    def _get_prompt_hash(self, prompt: str) -> str:
        """Generate hash for prompt caching."""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]

    def classify(self, prompt: str, estimate_tokens: bool = True) -> Dict[str, Any]:
        """
        Classify request complexity and return detailed analysis.

        Args:
            prompt: The LLM request/prompt to classify
            estimate_tokens: Estimate token count (rough approximation)

        Returns:
            Dictionary with classification results and features
        """
        prompt_hash = self._get_prompt_hash(prompt)

        if self.cache_enabled and prompt_hash in self.cache:
            cached_level, cached_score = self.cache[prompt_hash]
            if self.verbose:
                print(f"[CACHE HIT] Hash: {prompt_hash}")
            return {
                'complexity_level': cached_level.name,
                'complexity_score': cached_score,
                'cached': True,
                'prompt_hash': prompt_hash,
                'timestamp': datetime.now().isoformat(),
            }

        features = self._extract_features(prompt, estimate_tokens)
        score = self._calculate_complexity_score(features)
        level = self._determine_level(score)

        if self.cache_enabled:
            self.cache[prompt_hash] = (level, score)

        self.complexity_scores.append(score)

        result = {
            'complexity_level': level.name,
            'complexity_score': round(score, 2),
            'cached': False,
            'prompt_hash': prompt_hash,
            'features': asdict(features),
            'timestamp': datetime.now().isoformat(),
            'recommended_model': self._recommend_model(level),
            'estimated_cost_tier': self._estimate_cost_tier(level),
        }

        if self.verbose:
            print(f"[CLASSIFICATION] Level: {level.name}, Score: {score:.2f}")
            print(f"Features: {json.dumps(asdict(features), indent=2)}")

        return result

    def _extract_features(self, prompt: str, estimate_tokens: bool) -> ComplexityFeatures:
        """Extract linguistic and structural features from prompt."""
        words = prompt.split()
        sentences = self._split_sentences(prompt)
        lines = prompt.split('\n')

        token_count = self._estimate_tokens(prompt) if estimate_tokens else len(words)
        sentence_count = len(sentences)
        avg_sentence_length = int(len(words) / max(sentence_count, 1))
        avg_word_length = statistics.mean(len(w) for w in words) if words else 0

        vocabulary_richness = len(set(w.lower() for w in words)) / max(len(words), 1)
        punctuation_density = sum(
            1 for c in prompt if c in '.,;:!?"\'-'
        ) / max(len(prompt), 1)

        technical_term_count = self._count_technical_terms(prompt)
        logical_operator_count = sum(
            1 for op in ['and', 'or', 'not', 'if', 'else', 'while', 'for']
            if f' {op} ' in f' {prompt.lower()} '
        )
        question_count = prompt.count('?')
        conditional_count = len(re.findall(r'\b(if|unless|when|given|assuming)\b', prompt, re.I))

        numerical_content = re.findall(r'\d+\.?\d*', prompt)
        numerical_content_density = len(numerical_content) / max(len(words), 1)

        code_blocks = re.findall(r'```.*?```', prompt, re.DOTALL)
        code_block_presence = len(code_blocks) > 0
        code_block_count = len(code_blocks)

        list_structure_count = len(re.findall(r'^[\s]*[-*•]\s', prompt, re.MULTILINE))
        list_structure_count += len(re.findall(r'^\s*\d+\.\s', prompt, re.MULTILINE))

        structural_depth = self._calculate_structural_depth(prompt)
        nested_structure_depth = self._calculate_nesting_depth(prompt)

        return ComplexityFeatures(
            token_count=token_count,
            sentence_count=sentence_count,
            avg_sentence_length=avg_sentence_length,
            avg_word_length=round(avg_word_length, 2),
            vocabulary_richness=round(vocabulary_richness, 3),
            punctuation_density=round(punctuation_density, 3),
            technical_term_count=technical_term_count,
            logical_operator_count=logical_operator_count,
            question_count=question_count,
            conditional_count=conditional_count,
            numerical_content_density=round(numerical_content_density, 3),
            structural_depth=structural_depth,
            code_block_presence=code_block_presence,
            code_block_count=code_block_count,
            list_structure_count=list_structure_count,
            nested_structure_depth=nested_structure_depth,
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 chars, plus punctuation)."""
        char_count = len(text)
        word_count = len(text.split())
        return max(int(char_count / 4) + int(word_count / 1.3), word_count)

    def _count_technical_terms(self, text: str) -> int:
        """Count occurrences of technical terms."""
        text_lower = text.lower()
        count = 0
        for term in self.technical_terms:
            count += len(re.findall(rf'\b{re.escape(term)}\b', text_lower))
        return count

    def _calculate_structural_depth(self, text: str) -> int:
        """Calculate structural depth based on indentation and nesting."""
        lines = text.split('\n')
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent // 4)
        return min(max_indent + 1, 10)

    def _calculate_nesting_depth(self, text: str) -> int:
        """Calculate maximum nesting depth from parentheses/brackets."""
        max_depth = 0
        current_depth = 0
        for char in text:
            if char in '([{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ')]}':
                current_depth = max(0, current_depth - 1)
        return max_depth

    def _calculate_complexity_score(self, features: ComplexityFeatures) -> float:
        """Calculate overall complexity score (0-100)."""
        score = 0.0

        score += min(features.token_count / 50, 15)
        score += features.sentence_count
        score += features.avg_sentence_length / 3
        score += features.avg_word_length * 2
        score += features.vocabulary_richness * 20
        score += features.punctuation_density * 30
        score += features.technical_term_count * 3
        score += features.logical_operator_count * 2.5
        score += features.question_count * 5
        score += features.conditional_count * 4
        score += features.numerical_content_density * 15
        score += features.structural_depth * 2
        score += features.code_block_count * 10
        score += features.list_structure_count * 1.5
        score += features.nested_structure_depth * 3

        return min(score, 100.0)

    def _determine_level(self, score: float) -> ComplexityLevel:
        """Map complexity score to level."""
        if score < 10:
            return ComplexityLevel.TRIVIAL
        elif score < 25:
            return ComplexityLevel.SIMPLE
        elif score < 45:
            return ComplexityLevel.MODERATE
        elif score < 70:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.EXPERT

    def _recommend_model(self, level: ComplexityLevel) -> str:
        """Recommend model based on complexity level."""
        recommendations = {
            ComplexityLevel.TRIVIAL: 'gpt-3.5-turbo',
            ComplexityLevel.SIMPLE: 'gpt-3.5-turbo',
            ComplexityLevel.MODERATE: 'gpt-4-turbo',
            ComplexityLevel.COMPLEX: 'gpt-4',
            ComplexityLevel.EXPERT: 'gpt-4-32k',
        }
        return recommendations[level]

    def _estimate_cost_tier(self, level: ComplexityLevel) -> str:
        """Estimate cost tier for the request."""
        tiers = {
            ComplexityLevel.TRIVIAL: 'very-low',
            ComplexityLevel.SIMPLE: 'low',
            ComplexityLevel.MODERATE: 'medium',
            ComplexityLevel.COMPLEX: 'high',
            ComplexityLevel.EXPERT: 'very-high',
        }
        return tiers[level]

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'total_cached_prompts': len(self.cache),
            'cache_enabled': self.cache_enabled,
            'avg_complexity_score': round(statistics.mean(self.complexity_scores), 2)
            if self.complexity_scores else 0,
            'score_distribution': {
                'trivial': sum(1 for s in self.complexity_scores if s < 10),
                'simple': sum(1 for s in self.complexity_scores if 10 <= s < 25),
                'moderate': sum(1 for s in self.complexity_scores if 25 <= s < 45),
                'complex': sum(1 for s in self.complexity_scores if 45 <= s < 70),
                'expert': sum(1 for s in self.complexity_scores if s >= 70),
            },
        }

    def batch_classify(self, prompts: List[str]) -> List[Dict[str, Any]]:
        """Classify multiple prompts."""
        return [self.classify(prompt) for prompt in prompts]


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='LLM Request Complexity Classifier for Cost Optimization',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python solution.py --prompt "What is machine learning?"
  python solution.py --prompt-file prompts.txt --verbose
  python solution.py --batch-test 10 --output results.json
        ''',
    )

    parser.add_argument(
        '--prompt',
        type=str,
        help='Single prompt to classify',
    )
    parser.add_argument(
        '--prompt-file',
        type=str,
        help='File containing prompts (one per line)',
    )
    parser.add_argument(
        '--batch-test',
        type=int,
        metavar='COUNT',
        help='Generate and classify N test prompts',
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output file for results (JSON)',
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output',
    )
    parser.add_argument(
        '--disable-cache',
        action='store_true',
        help='Disable prompt caching',
    )
    parser.add_argument(
        '--show-stats',
        action='store_true',
        help='Show cache statistics at end',
    )

    args = parser.parse_args()

    classifier = ComplexityClassifier(
        cache_enabled=not args.disable_cache,
        verbose=args.verbose,
    )

    results = []

    if args.prompt:
        result = classifier.classify(args.prompt)
        results.append(result)
        print(json.dumps(result, indent=2))

    elif args.prompt_file:
        with open(args.prompt_file, 'r') as f:
            prompts = [line.strip() for line in f if line.strip()]
        results = classifier.batch_classify(prompts)
        for result in results:
            print(json.dumps(result, indent=2))

    elif args.batch_test:
        test_prompts = _generate_test_prompts(args.batch_test)
        results = classifier.batch_classify(test_prompts)
        for result in results:
            print(json.dumps(result, indent=2))

    else:
        parser.print_help()
        return

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

    if args.show_stats:
        stats = classifier.get_cache_stats()
        print("\n" + "=" * 60)
        print("CACHE STATISTICS")
        print("=" * 60)
        print(json.dumps(stats, indent=2))


def _generate_test_prompts(count: int) -> List[str]:
    """Generate diverse test prompts for batch testing."""
    test_prompts = [
        "Hi",
        "What is 2+2?",
        "Explain photosynthesis in simple terms.",
        "How do I make a chocolate cake? List the steps.",
        (
            "Design a microservices architecture for a scalable e-commerce platform. "
            "Consider load balancing, caching strategies, database optimization, "
            "and security. Explain the trade-offs between SQL and NoSQL databases "
            "in this context, and provide pseudocode for a cache invalidation strategy."
        ),
        (
            "Write a Python script that implements a recursive binary search tree "
            "with in-order traversal, including deletion with proper rebalancing. "
            "Handle edge cases and explain time complexity."
        ),
        (
            "Analyze the following quantum computing algorithm:\n"
            "```\nqasm: H q[0]; CNOT q[0], q[1]; Measure q[0] -> c[0];\n```\n"
            "1. Explain the quantum gates\n"
            "2. Calculate probability distribution\n"
            "3. Compare to classical approach"
        ),
        "Create a REST API specification for user authentication with JWT tokens.",
        (
            "Given constraints: low latency (<50ms), high throughput (10k req/s), "
            "and strict consistency. Design a distributed cache system using Redis, "
            "covering: sharding strategy, replication, failover, monitoring."
        ),
        "Summarize the plot of Hamlet.",
    ]

    while len(test_prompts) < count:
        test_prompts.append(
            f"Test prompt {len(test_prompts)}: This is a sample prompt for complexity analysis."
        )

    return test_prompts[:count]


if __name__ == '__main__':
    main()