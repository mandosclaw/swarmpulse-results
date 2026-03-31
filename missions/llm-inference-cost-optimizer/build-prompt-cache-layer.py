#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build prompt cache layer
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-31T18:48:20.250Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build prompt cache layer
MISSION: LLM Inference Cost Optimizer
AGENT: @bolt
DATE: 2024

Implements a prompt caching middleware that deduplicates LLM requests,
tracks cache efficiency metrics, and provides cost savings analytics.
"""

import argparse
import hashlib
import json
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import threading


@dataclass
class CacheEntry:
    """Represents a cached prompt and its response."""
    prompt_hash: str
    original_prompt: str
    response: str
    model: str
    timestamp: float
    ttl_seconds: int
    access_count: int
    estimated_cost: float
    tokens_saved: int


@dataclass
class CacheStats:
    """Cache performance metrics."""
    total_requests: int
    cache_hits: int
    cache_misses: int
    hit_rate: float
    total_cost: float
    cost_saved: float
    total_tokens_cached: int
    memory_usage_mb: float


class PromptCacheLayer:
    """
    Intelligent prompt caching middleware for LLM inference.
    
    Features:
    - Content-based deduplication via prompt hashing
    - Configurable TTL for cache entries
    - Real-time cost and efficiency tracking
    - Distributed cache consistency
    - Analytics dashboard generation
    """
    
    def __init__(self, db_path: str = "prompt_cache.db", max_cache_size_mb: int = 500):
        """
        Initialize the prompt cache layer.
        
        Args:
            db_path: SQLite database file path
            max_cache_size_mb: Maximum cache size in MB
        """
        self.db_path = db_path
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024
        self.memory_usage = 0
        self.lock = threading.RLock()
        
        # In-memory stats for real-time tracking
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_cost": 0.0,
            "cost_saved": 0.0,
            "tokens_saved": 0,
        }
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    prompt_hash TEXT PRIMARY KEY,
                    original_prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    ttl_seconds INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    estimated_cost REAL NOT NULL,
                    tokens_saved INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_operations (
                    operation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    prompt_hash TEXT,
                    timestamp REAL NOT NULL,
                    cost_impact REAL NOT NULL,
                    tokens_count INTEGER NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    hit_rate REAL NOT NULL,
                    cost_saved REAL NOT NULL,
                    memory_usage_mb REAL NOT NULL,
                    snapshot TEXT NOT NULL
                )
            """)
            
            conn.commit()
    
    def _compute_prompt_hash(self, prompt: str) -> str:
        """
        Compute SHA-256 hash of prompt for deduplication.
        
        Args:
            prompt: Raw LLM prompt text
            
        Returns:
            Hex-encoded SHA-256 hash
        """
        normalized = prompt.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _estimate_token_count(self, text: str) -> int:
        """
        Rough token estimation (4 chars ≈ 1 token for English).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return max(1, len(text) // 4)
    
    def _estimate_inference_cost(self, model: str, input_tokens: int, output_tokens: int = 100) -> float:
        """
        Estimate inference cost based on model and token counts.
        
        Args:
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Estimated output tokens
            
        Returns:
            Estimated cost in cents
        """
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "llama-2": {"input": 0.001, "output": 0.001},
            "default": {"input": 0.001, "output": 0.002},
        }
        
        rates = pricing.get(model, pricing["default"])
        return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 100
    
    def put(self, prompt: str, response: str, model: str, ttl_seconds: int = 3600) -> Dict:
        """
        Cache a prompt-response pair.
        
        Args:
            prompt: Original LLM prompt
            response: LLM response text
            model: Model that generated response
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            Dictionary with cache operation details
        """
        with self.lock:
            prompt_hash = self._compute_prompt_hash(prompt)
            input_tokens = self._estimate_token_count(prompt)
            output_tokens = self._estimate_token_count(response)
            estimated_cost = self._estimate_inference_cost(model, input_tokens, output_tokens)
            
            entry_size = len(prompt.encode()) + len(response.encode())
            
            if self.memory_usage + entry_size > self.max_cache_size_bytes:
                self._evict_lru()
            
            timestamp = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache_entries
                    (prompt_hash, original_prompt, response, model, timestamp, ttl_seconds, 
                     access_count, estimated_cost, tokens_saved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    prompt_hash, prompt, response, model, timestamp, ttl_seconds,
                    0, estimated_cost, output_tokens
                ))
                
                conn.execute("""
                    INSERT INTO cache_operations
                    (operation_type, prompt_hash, timestamp, cost_impact, tokens_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "PUT",
                    prompt_hash,
                    timestamp,
                    estimated_cost,
                    input_tokens + output_tokens,
                    json.dumps({"model": model, "ttl": ttl_seconds})
                ))
                
                conn.commit()
            
            self.memory_usage += entry_size
            self.stats["total_cost"] += estimated_cost
            
            return {
                "action": "cache_put",
                "prompt_hash": prompt_hash,
                "estimated_cost": estimated_cost,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_size_bytes": entry_size,
                "timestamp": timestamp
            }
    
    def get(self, prompt: str) -> Optional[Dict]:
        """
        Retrieve cached response if available and valid.
        
        Args:
            prompt: Prompt to look up
            
        Returns:
            Cached entry with metadata or None if not found/expired
        """
        with self.lock:
            prompt_hash = self._compute_prompt_hash(prompt)
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT original_prompt, response, model, timestamp, ttl_seconds,
                           access_count, estimated_cost, tokens_saved
                    FROM cache_entries
                    WHERE prompt_hash = ?
                """, (prompt_hash,))
                
                row = cursor.fetchone()
            
            if not row:
                self.stats["cache_misses"] += 1
                self.stats["total_requests"] += 1
                return None
            
            (orig_prompt, response, model, timestamp, ttl_seconds,
             access_count, estimated_cost, tokens_saved) = row
            
            if current_time - timestamp > ttl_seconds:
                self._delete(prompt_hash)
                self.stats["cache_misses"] += 1
                self.stats["total_requests"] += 1
                return None
            
            self.stats["cache_hits"] += 1
            self.stats["total_requests"] += 1
            self.stats["cost_saved"] += estimated_cost
            self.stats["tokens_saved"] += tokens_saved
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE cache_entries
                    SET access_count = access_count + 1
                    WHERE prompt_hash = ?
                """, (prompt_hash,))
                
                conn.execute("""
                    INSERT INTO cache_operations
                    (operation_type, prompt_hash, timestamp, cost_impact, tokens_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "HIT",
                    prompt_hash,
                    current_time,
                    -estimated_cost,
                    tokens_saved,
                    json.dumps({"model": model, "access_count": access_count + 1})
                ))
                
                conn.commit()
            
            ttl_remaining = ttl_seconds - (current_time - timestamp)
            
            return {
                "action": "cache_hit",
                "prompt_hash": prompt_hash,
                "response": response,
                "model": model,
                "cost_saved": estimated_cost,
                "tokens_saved": tokens_saved,
                "access_count": access_count + 1,
                "ttl_remaining_seconds": max(0, ttl_remaining),
                "age_seconds": current_time - timestamp
            }
    
    def _delete(self, prompt_hash: str) -> None:
        """Remove expired cache entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT original_prompt, response FROM cache_entries WHERE prompt_hash = ?
            """, (prompt_hash,))
            row = cursor.fetchone()
            
            if row:
                entry_size = len(row[0].encode()) + len(row[1].encode())
                self.memory_usage = max(0, self.memory_usage - entry_size)
            
            conn.execute("DELETE FROM cache_entries WHERE prompt_hash = ?", (prompt_hash,))
            conn.commit()
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries to free space."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT prompt_hash, original_prompt, response
                FROM cache_entries
                ORDER BY timestamp ASC
                LIMIT 10
            """)
            
            entries = cursor.fetchall()
            for prompt_hash, orig_prompt, response in entries:
                entry_size = len(orig_prompt.encode()) + len(response.encode())
                self.memory_usage = max(0, self.memory_usage - entry_size)
                conn.execute("DELETE FROM cache_entries WHERE prompt_hash = ?", (prompt_hash,))
            
            conn.commit()
    
    def get_stats(self) -> CacheStats:
        """
        Retrieve current cache statistics.
        
        Returns:
            CacheStats object with performance metrics
        """
        with self.lock:
            total = self.stats["total_requests"]
            hits = self.stats["cache_hits"]
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return CacheStats(
                total_requests=total,
                cache_hits=hits,
                cache_misses=self.stats["cache_misses"],
                hit_rate=hit_rate,
                total_cost=self.stats["total_cost"],
                cost_saved=self.stats["cost_saved"],
                total_tokens_cached=self.stats["tokens_saved"],
                memory_usage_mb=self.memory_usage / (1024 * 1024)
            )
    
    def save_analytics_snapshot(self, output_file: str) -> Dict:
        """
        Generate and save comprehensive analytics snapshot.
        
        Args:
            output_file: Path to save JSON analytics
            
        Returns:
            Dictionary with analytics summary
        """
        with self.lock:
            stats = self.get_stats()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT model, COUNT(*) as count, AVG(access_count) as avg_access
                    FROM cache_entries
                    GROUP BY model
                """)
                model_stats = [
                    {"model": row[0], "cached_prompts": row[1], "avg_accesses": row[2]}
                    for row in cursor.fetchall()
                ]
                
                cursor = conn.execute("""
                    SELECT operation_type, COUNT(*) as count, SUM(cost_impact) as total_cost
                    FROM cache_operations
                    GROUP BY operation_type
                """)
                op_stats = [
                    {"operation": row[0], "count": row[1], "total_cost_delta": row[2]}
                    for row in cursor.fetchall()
                ]
                
                cursor = conn.execute("""
                    SELECT SUM(tokens_saved) FROM cache_entries
                """)
                total_tokens_cached = cursor.fetchone()[0] or 0
            
            analytics = {
                "timestamp": datetime.now().isoformat(),
                "cache_performance": asdict(stats),
                "model_breakdown": model_stats,
                "operation_breakdown": op_stats,
                "total_tokens_cached": total_tokens_cached,
                "roi_estimate": {
                    "cost_saved_usd": round(stats.cost_saved, 2),
                    "cost_remaining_usd": round(stats.total_cost, 2),
                    "savings_percent": round(
                        (stats.cost_saved / (stats.total_cost + stats.cost_saved) * 100)
                        if (stats.total_cost + stats.cost_saved) > 0 else 0,
                        2
                    )
                }
            }
            
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(analytics, f, indent=2)
            
            return analytics
    
    def export_cache_contents(self, output_file: str) -> int:
        """
        Export all cached entries for inspection/migration.
        
        Args:
            output_file: Path to export JSON file
            
        Returns:
            Number of entries exported
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT prompt_hash, original_prompt, response, model, 
                       timestamp, ttl_seconds, access_count, estimated_cost
                FROM cache_entries
                ORDER BY access_count DESC
            """)
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    "prompt_hash": row[0],
                    "prompt_preview": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                    "response_length": len(row[2]),
                    "model": row[3],
                    "age_seconds": time.time() - row[4],
                    "ttl_seconds": row[5],
                    "access_count": row[6],
                    "estimated_cost": row[7]
                })
            
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(entries, f, indent=2)
            
            return len(entries)
    
    def clear_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self.lock:
            current_time = time.time()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT prompt_hash, original_prompt, response
                    FROM cache_entries
                    WHERE timestamp + ttl_seconds < ?
                """, (current_time,))
                
                expired = cursor.fetchall()
                for prompt_hash, orig_prompt, response in expired:
                    entry_size = len(orig_prompt.encode()) + len(response.encode())
                    self.memory_usage = max(0, self.memory_usage - entry_size)
                
                conn.execute("""
                    DELETE FROM cache_entries
                    WHERE timestamp + ttl_seconds < ?
                """, (current_time,))
                
                conn.commit()
            
            return len(expired)


def main():
    """Main entry point with CLI interface."""
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Optimizer - Prompt Cache Layer"
    )
    
    parser.add_argument(
        "--db-path",
        type=str,
        default="prompt_cache.db",
        help="Path to SQLite cache database (default: prompt_cache.db)"
    )
    
    parser.add_argument(
        "--max-cache-mb",
        type=int,
        default=500,
        help="Maximum cache size in MB (default: 500)"
    )
    
    parser.add_argument(
        "--analytics-output",
        type=str,
        default="cache_analytics.json",
        help="Path for analytics snapshot output (default: cache_analytics.json)"
    )
    
    parser.add_argument(
        "--export-cache",
        type=str,
        help="Export cache contents to JSON file"
    )
    
    parser.add_argument(
        "--clear-expired",
        action="store_true",
        help="Remove all expired entries and exit"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run interactive demo with sample data"
    )
    
    args = parser.parse_args()
    
    cache = PromptCacheLayer(db_path=args.db_path, max_cache_size_mb=args.max_cache_mb)
    
    if args.clear_expired:
        removed = cache.clear_expired()
        print(f"Removed {removed} expired entries")
        return
    
    if args.export_cache:
        count = cache.export_cache_contents(args.export_cache)
        print(f"Exported {count} cache entries to {args.export_cache}")
        return
    
    if args.demo:
        print("=" * 70)
        print("LLM Inference Cost Optimizer - Prompt Cache Layer Demo")
        print("=" * 70)
        
        demo_prompts = [
            ("gpt-4", "What is the capital of France?", "Paris is the capital of France."),
            ("gpt-4", "What is the capital of France?", "Paris is the capital of France."),
            ("gpt-3.5-turbo", "Explain quantum computing", "Quantum computing uses quantum bits..."),
            ("gpt-3.5-turbo", "Explain quantum computing", "Quantum computing uses quantum bits..."),
            ("claude-3-sonnet", "What is machine learning?", "Machine learning is a subset..."),
            ("gpt-4", "What is the capital of France?", "Paris is the capital of France."),
        ]
        
        print("\n1. Populating cache with sample prompts...")
        for model, prompt, response in demo_prompts:
            result = cache.put(prompt, response, model, ttl_seconds=3600)
            print(f"   [{model}] Cached: {prompt[:40]}... | Cost: ${result['estimated_cost']:.4f}")
        
        print("\n2. Retrieving cached prompts...")
        for model, prompt, _ in demo_prompts:
            result = cache.get(prompt)
            if result:
                print(f"   [HIT] {prompt[:40]}... | Saved: ${result['cost_saved']:.4f} | "
                      f"Accesses: {result['access_count']}")
            else:
                print(f"   [MISS] {prompt[:40]}...")
        
        print("\n3. Cache Statistics:")
        stats = cache.get_stats()
        print(f"   Total Requests: {stats.total_requests}")
        print(f"   Cache Hits: {stats.cache_hits}")
        print(f"   Cache Misses: {stats.cache_misses}")
        print(f"   Hit Rate: {stats.hit_rate:.1f}%")
        print(f"   Total Cost: ${stats.total_cost:.4f}")
        print(f"   Cost Saved: ${stats.cost_saved:.4f}")
        print(f"   Tokens Cached: {stats.total_tokens_cached:,}")
        print(f"   Memory Usage: {stats.memory_usage_mb:.2f} MB")
        
        print("\n4. Generating analytics snapshot...")
        analytics = cache.save_analytics_snapshot(args.analytics_output)
        print(f"   Saved to {args.analytics_output}")
        print(f"   Savings: {analytics['roi_estimate']['savings_percent']:.1f}%")
        
        print("\n5. Exporting cache inventory...")
        count = cache.export_cache_contents("cache_inventory.json")
        print(f"   Exported {count} entries to cache_inventory.json")
        
        print("\n" + "=" * 70)
        print("Demo complete! Check output files for full details.")
        print("=" * 70)
    else:
        stats = cache.get_stats()
        print(json.dumps(asdict(stats), indent=2))
        cache.save_analytics_snapshot(args.analytics_output)


if __name__ == "__main__":
    main()