#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build prompt cache layer
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-29T13:20:05.688Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build prompt cache layer for LLM Inference Cost Optimizer
MISSION: LLM Inference Cost Optimizer
AGENT: @bolt
DATE: 2024
DESCRIPTION: Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics.
"""

import argparse
import hashlib
import json
import time
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any


class PromptCacheEntry:
    """Represents a cached prompt with metadata."""

    def __init__(self, prompt_hash: str, prompt_text: str, model: str, 
                 response: str, cost: float, tokens: int):
        self.prompt_hash = prompt_hash
        self.prompt_text = prompt_text
        self.model = model
        self.response = response
        self.cost = cost
        self.tokens = tokens
        self.created_at = datetime.now().isoformat()
        self.access_count = 1
        self.last_accessed = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert cache entry to dictionary."""
        return {
            'prompt_hash': self.prompt_hash,
            'prompt_text': self.prompt_text,
            'model': self.model,
            'response': self.response,
            'cost': self.cost,
            'tokens': self.tokens,
            'created_at': self.created_at,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed
        }

    def update_access(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = datetime.now().isoformat()


class PromptCacheLayer:
    """Manages prompt caching with cost tracking and analytics."""

    def __init__(self, max_size: int = 10000, ttl_seconds: Optional[int] = None,
                 enable_semantic_matching: bool = False):
        """
        Initialize the prompt cache layer.
        
        Args:
            max_size: Maximum number of cached prompts
            ttl_seconds: Time to live for cache entries (None = no expiry)
            enable_semantic_matching: Enable fuzzy matching for similar prompts
        """
        self.cache: Dict[str, PromptCacheEntry] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.enable_semantic_matching = enable_semantic_matching
        self.access_stats = defaultdict(int)
        self.cost_savings = 0.0
        self.total_cache_hits = 0
        self.total_cache_misses = 0

    def _hash_prompt(self, prompt: str) -> str:
        """Generate SHA256 hash of prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def _is_expired(self, entry: PromptCacheEntry) -> bool:
        """Check if cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        created_time = datetime.fromisoformat(entry.created_at)
        elapsed = (datetime.now() - created_time).total_seconds()
        return elapsed > self.ttl_seconds

    def _similarity_score(self, prompt1: str, prompt2: str) -> float:
        """
        Calculate similarity between two prompts using simple token overlap.
        Returns score between 0 and 1.
        """
        tokens1 = set(prompt1.lower().split())
        tokens2 = set(prompt2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        return intersection / union if union > 0 else 0.0

    def _evict_oldest(self):
        """Evict oldest least-accessed entry when cache is full."""
        if not self.cache:
            return
        
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: (
                self.cache[k].access_count,
                datetime.fromisoformat(self.cache[k].last_accessed)
            )
        )
        del self.cache[oldest_key]

    def put(self, prompt: str, model: str, response: str, cost: float, 
            tokens: int) -> str:
        """
        Store a prompt and response in cache.
        
        Args:
            prompt: The input prompt
            model: Model used for inference
            response: Model's response
            cost: Cost of the inference
            tokens: Number of tokens used
            
        Returns:
            Hash of the cached prompt
        """
        prompt_hash = self._hash_prompt(prompt)
        
        if prompt_hash in self.cache:
            self.cache[prompt_hash].update_access()
            return prompt_hash
        
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        entry = PromptCacheEntry(prompt_hash, prompt, model, response, cost, tokens)
        self.cache[prompt_hash] = entry
        self.access_stats[model] += 1
        
        return prompt_hash

    def get(self, prompt: str, similarity_threshold: float = 1.0) -> Optional[PromptCacheEntry]:
        """
        Retrieve a cached response for a prompt.
        
        Args:
            prompt: The input prompt
            similarity_threshold: Minimum similarity for fuzzy matching (0.0-1.0)
            
        Returns:
            Cache entry if found and not expired, else None
        """
        prompt_hash = self._hash_prompt(prompt)
        
        if prompt_hash in self.cache:
            entry = self.cache[prompt_hash]
            if not self._is_expired(entry):
                entry.update_access()
                self.total_cache_hits += 1
                self.cost_savings += entry.cost
                return entry
            else:
                del self.cache[prompt_hash]
        
        if self.enable_semantic_matching and similarity_threshold < 1.0:
            best_match = None
            best_score = similarity_threshold
            
            for cached_prompt_hash, entry in self.cache.items():
                if self._is_expired(entry):
                    del self.cache[cached_prompt_hash]
                    continue
                
                score = self._similarity_score(prompt, entry.prompt_text)
                if score > best_score:
                    best_score = score
                    best_match = entry
            
            if best_match:
                best_match.update_access()
                self.total_cache_hits += 1
                self.cost_savings += best_match.cost * (1 - best_score)
                return best_match
        
        self.total_cache_misses += 1
        return None

    def invalidate(self, prompt: str) -> bool:
        """
        Invalidate a cached prompt.
        
        Args:
            prompt: The prompt to invalidate
            
        Returns:
            True if entry was found and removed, False otherwise
        """
        prompt_hash = self._hash_prompt(prompt)
        if prompt_hash in self.cache:
            del self.cache[prompt_hash]
            return True
        return False

    def clear(self):
        """Clear entire cache."""
        self.cache.clear()
        self.cost_savings = 0.0
        self.total_cache_hits = 0
        self.total_cache_misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self.total_cache_hits + self.total_cache_misses
        hit_rate = (self.total_cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        model_distribution = dict(self.access_stats)
        
        cache_size_bytes = sum(
            len(entry.prompt_text.encode()) + len(entry.response.encode())
            for entry in self.cache.values()
        )
        
        expired_count = sum(
            1 for entry in self.cache.values()
            if self._is_expired(entry)
        )
        
        return {
            'timestamp': datetime.now().isoformat(),
            'cache_size': len(self.cache),
            'cache_size_bytes': cache_size_bytes,
            'max_size': self.max_size,
            'total_cache_hits': self.total_cache_hits,
            'total_cache_misses': self.total_cache_misses,
            'hit_rate_percentage': round(hit_rate, 2),
            'total_cost_savings': round(self.cost_savings, 4),
            'model_distribution': model_distribution,
            'expired_entries': expired_count,
            'average_entry_size_bytes': round(
                cache_size_bytes / len(self.cache) if self.cache else 0, 2
            )
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        if self.ttl_seconds is None:
            return 0
        
        expired_hashes = [
            h for h, entry in self.cache.items()
            if self._is_expired(entry)
        ]
        
        for h in expired_hashes:
            del self.cache[h]
        
        return len(expired_hashes)

    def export_cache(self, filepath: str):
        """Export cache to JSON file."""
        data = {
            'metadata': {
                'exported_at': datetime.now().isoformat(),
                'cache_size': len(self.cache),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl_seconds
            },
            'entries': [
                entry.to_dict() for entry in self.cache.values()
            ],
            'statistics': self.get_stats()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def import_cache(self, filepath: str):
        """Import cache from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for entry_data in data.get('entries', []):
            entry = PromptCacheEntry(
                prompt_hash=entry_data['prompt_hash'],
                prompt_text=entry_data['prompt_text'],
                model=entry_data['model'],
                response=entry_data['response'],
                cost=entry_data['cost'],
                tokens=entry_data['tokens']
            )
            entry.created_at = entry_data['created_at']
            entry.access_count = entry_data['access_count']
            entry.last_accessed = entry_data['last_accessed']
            self.cache[entry.prompt_hash] = entry

    def get_expensive_prompts(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get the most expensive cached prompts."""
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda e: e.cost,
            reverse=True
        )
        
        return [
            {
                'prompt': entry.prompt_text[:100] + ('...' if len(entry.prompt_text) > 100 else ''),
                'model': entry.model,
                'cost': entry.cost,
                'tokens': entry.tokens,
                'access_count': entry.access_count
            }
            for entry in sorted_entries[:top_n]
        ]

    def get_most_reused_prompts(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently reused cached prompts."""
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda e: e.access_count,
            reverse=True
        )
        
        return [
            {
                'prompt': entry.prompt_text[:100] + ('...' if len(entry.prompt_text) > 100 else ''),
                'model': entry.model,
                'access_count': entry.access_count,
                'cost': entry.cost,
                'cost_per_access': round(entry.cost / entry.access_count, 4)
            }
            for entry in sorted_entries[:top_n]
        ]


def simulate_inference(prompt: str, model: str) -> Tuple[str, float, int]:
    """Simulate LLM inference with cost calculation."""
    response = f"Simulated response to '{prompt[:50]}...' using {model}"
    
    model_costs = {
        'gpt-4': {'per_token': 0.03},
        'gpt-3.5-turbo': {'per_token': 0.0015},
        'claude-2': {'per_token': 0.01},
        'llama-2': {'per_token': 0.001}
    }
    
    tokens = len(prompt.split()) + len(response.split())
    cost_per_token = model_costs.get(model, {'per_token': 0.01})['per_token']
    cost = tokens * cost_per_token
    
    return response, cost, tokens


def main():
    """Main function with CLI interface."""
    parser = argparse.ArgumentParser(
        description='LLM Inference Cost Optimizer - Prompt Cache Layer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 script.py --mode demo --cache-size 100
  python3 script.py --mode interactive --ttl 3600
  python3 script.py --mode export --export-file cache_backup.json
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['demo', 'interactive', 'export', 'stats'],
        default='demo',
        help='Operation mode (default: demo)'
    )
    parser.add_argument(
        '--cache-size',
        type=int,
        default=1000,
        help='Maximum cache size in entries (default: 1000)'
    )
    parser.add_argument(
        '--ttl',
        type=int,
        default=None,
        help='Cache TTL in seconds (default: None = no expiry)'
    )
    parser.add_argument(
        '--semantic-matching',
        action='store_true',
        help='Enable semantic similarity matching for prompts'
    )
    parser.add_argument(
        '--export-file',
        type=str,
        default='cache_export.json',
        help='File path for cache export (default: cache_export.json)'
    )
    parser.add_argument(
        '--import-file',
        type=str,
        default=None,
        help='File path for cache import'
    )
    
    args = parser.parse_args()
    
    cache = PromptCacheLayer(
        max_size=args.cache_size,
        ttl_seconds=args.ttl,
        enable_semantic_matching=args.semantic_matching
    )
    
    if args.import_file:
        try:
            cache.import_cache(args.import_file)
            print(f"✓ Imported cache from {args.import_file}")
        except FileNotFoundError:
            print(f"✗ Import file not found: {args.import_file}")
    
    if args.mode == 'demo':
        print("=" * 70)
        print("PROMPT CACHE LAYER DEMO")
        print("=" * 70)
        
        test_prompts = [
            ("What is machine learning?", "gpt-4"),
            ("Explain neural networks", "gpt-3.5-turbo"),
            ("What is machine learning?", "gpt-4"),
            ("How do transformers work?", "claude-2"),
            ("Explain neural networks", "gpt-3.5-turbo"),
            ("What is deep learning?", "llama-2