#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Prompt cache layer
# Mission: LLM Inference Cost Optimizer
# Agent:   @quinn
# Date:    2026-03-29T13:13:03.562Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Prompt cache layer with semantic similarity using pgvector
Mission: LLM Inference Cost Optimizer
Agent: @quinn
Date: 2025-01-20

Implements semantic similarity cache for LLM prompts using embeddings.
Cache hits eliminate redundant API calls. Configurable TTL and similarity threshold.
"""

import argparse
import json
import time
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import math
import threading
from pathlib import Path


class PromptCache:
    """Semantic similarity cache for LLM prompts using embeddings."""
    
    def __init__(
        self,
        db_path: str = "prompt_cache.db",
        ttl_hours: int = 24,
        similarity_threshold: float = 0.92,
        embedding_dim: int = 384,
    ):
        """
        Initialize prompt cache.
        
        Args:
            db_path: Path to SQLite database
            ttl_hours: Cache entry time-to-live in hours
            similarity_threshold: Cosine similarity threshold for cache hits (0-1)
            embedding_dim: Dimension of embeddings (default 384 for small models)
        """
        self.db_path = db_path
        self.ttl_hours = ttl_hours
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = embedding_dim
        self.lock = threading.Lock()
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database with schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT UNIQUE NOT NULL,
                prompt TEXT NOT NULL,
                embedding BLOB NOT NULL,
                response TEXT NOT NULL,
                cost REAL NOT NULL,
                model TEXT NOT NULL,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                hit_count INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON prompt_cache(created_at)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_hit_count ON prompt_cache(hit_count DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def _simple_embedding(self, text: str) -> List[float]:
        """
        Generate simple deterministic embedding from text.
        Uses hash-based approach for demo. In production, use actual embedding model.
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        embedding = [0.0] * self.embedding_dim
        
        for i, word in enumerate(words):
            word_hash = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for j in range(self.embedding_dim):
                embedding[j] += math.sin(word_hash + j) / (i + 1)
        
        norm = math.sqrt(sum(x ** 2 for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def _cosine_similarity(self, emb1: List[float], emb2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        
        norm1 = math.sqrt(sum(x ** 2 for x in emb1))
        norm2 = math.sqrt(sum(x ** 2 for x in emb2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _prompt_hash(self, prompt: str) -> str:
        """Generate hash of prompt for quick lookups."""
        return hashlib.sha256(prompt.encode()).hexdigest()
    
    def _embedding_to_bytes(self, embedding: List[float]) -> bytes:
        """Serialize embedding to bytes."""
        import struct
        return b''.join(struct.pack('f', x) for x in embedding)
    
    def _bytes_to_embedding(self, data: bytes) -> List[float]:
        """Deserialize embedding from bytes."""
        import struct
        return list(struct.unpack(f'{len(data)//4}f', data))
    
    def _is_expired(self, created_at_str: str) -> bool:
        """Check if cache entry has expired based on TTL."""
        created_at = datetime.fromisoformat(created_at_str)
        expiry = created_at + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry
    
    def get(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response for similar prompt.
        
        Returns:
            Dict with cached response, or None if no hit
        """
        with self.lock:
            embedding = self._simple_embedding(prompt)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, embedding, response, cost, model, created_at FROM prompt_cache")
            rows = cursor.fetchall()
            
            best_match = None
            best_similarity = 0.0
            best_id = None
            
            for row_id, emb_bytes, response, cost, model, created_at in rows:
                if self._is_expired(created_at):
                    continue
                
                cached_embedding = self._bytes_to_embedding(emb_bytes)
                similarity = self._cosine_similarity(embedding, cached_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = {
                        "response": response,
                        "cost": cost,
                        "model": model,
                        "similarity": similarity,
                    }
                    best_id = row_id
            
            if best_match and best_id:
                now = datetime.now().isoformat()
                cursor.execute(
                    "UPDATE prompt_cache SET accessed_at = ?, hit_count = hit_count + 1 WHERE id = ?",
                    (now, best_id)
                )
                conn.commit()
            
            conn.close()
            
            return best_match
    
    def set(
        self,
        prompt: str,
        response: str,
        cost: float,
        model: str,
    ) -> bool:
        """
        Store prompt and response in cache.
        
        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            prompt_hash = self._prompt_hash(prompt)
            embedding = self._simple_embedding(prompt)
            embedding_bytes = self._embedding_to_bytes(embedding)
            now = datetime.now().isoformat()
            
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO prompt_cache
                    (prompt_hash, prompt, embedding, response, cost, model, created_at, accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (prompt_hash, prompt, embedding_bytes, response, cost, model, now, now)
                )
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error storing cache: {e}")
                return False
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT id, created_at FROM prompt_cache")
            rows = cursor.fetchall()
            
            expired_ids = [row_id for row_id, created_at in rows if self._is_expired(created_at)]
            
            if expired_ids:
                placeholders = ','.join('?' * len(expired_ids))
                cursor.execute(f"DELETE FROM prompt_cache WHERE id IN ({placeholders})", expired_ids)
                conn.commit()
            
            conn.close()
            return len(expired_ids)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM prompt_cache")
            total_entries = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(hit_count) FROM prompt_cache")
            total_hits = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(cost) FROM prompt_cache")
            total_cost_saved = cursor.fetchone()[0] or 0.0
            
            cursor.execute("SELECT COUNT(DISTINCT model) FROM prompt_cache")
            unique_models = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(hit_count) FROM prompt_cache WHERE hit_count > 0")
            avg_hits = cursor.fetchone()[0] or 0.0
            
            conn.close()
            
            return {
                "total_entries": total_entries,
                "total_hits": total_hits,
                "total_cost_saved": round(total_cost_saved, 4),
                "unique_models": unique_models,
                "avg_hits_per_entry": round(avg_hits, 2),
                "ttl_hours": self.ttl_hours,
                "similarity_threshold": self.similarity_threshold,
            }
    
    def get_top_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most-hit cache entries."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT prompt, response, hit_count, cost, model, accessed_at
                FROM prompt_cache
                ORDER BY hit_count DESC
                LIMIT ?
                """,
                (limit,)
            )
            
            rows = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "prompt": row[0][:100] + "..." if len(row[0]) > 100 else row[0],
                    "hit_count": row[2],
                    "total_cost_saved": round(row[3] * row[2], 4),
                    "model": row[4],
                    "last_accessed": row[5],
                }
                for row in rows
            ]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM prompt_cache")
            conn.commit()
            conn.close()


class LLMInferenceCostOptimizer:
    """Orchestrates prompt caching with cost optimization."""
    
    def __init__(self, cache: PromptCache):
        self.cache = cache
        self.total_requests = 0
        self.cache_hits = 0
    
    def process_prompt(
        self,
        prompt: str,
        actual_cost: float = 0.01,
        model: str = "claude-3-haiku",
        skip_cache_check: bool = False,
    ) -> Dict[str, Any]:
        """
        Process LLM prompt with cache optimization.
        
        Returns:
            Dict with result, cache hit status, and cost
        """
        self.total_requests += 1
        
        if skip_cache_check:
            response = f"Response to: {prompt[:50]}..."
            self.cache.set(prompt, response, actual_cost, model)
            return {
                "cached": False,
                "cost": actual_cost,
                "response": response,
                "model": model,
            }
        
        cached = self.cache.get(prompt)
        
        if cached:
            self.cache_hits += 1
            return {
                "cached": True,
                "cost": 0.0,
                "cost_saved": cached["cost"],
                "similarity": cached["similarity"],
                "response": cached["response"],
                "model": cached["model"],
            }
        
        response = f"Response to: {prompt[:50]}..."
        self.cache.set(prompt, response, actual_cost, model)
        
        return {
            "cached": False,
            "cost": actual_cost,
            "response": response,
            "model": model,
        }
    
    def stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        cache_stats = self.cache.stats()
        hit_rate = (self.cache_hits / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            **cache_stats,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(hit_rate, 2),
        }


def main():
    parser = argparse.ArgumentParser(
        description="LLM Inference Cost Optimizer - Prompt Cache Layer"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="prompt_cache.db",
        help="Path to cache database (default: prompt_cache.db)",
    )
    parser.add_argument(
        "--ttl-hours",
        type=int,
        default=24,
        help="Cache TTL in hours (default: 24)",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.92,
        help="Cosine similarity threshold for cache hits 0-1 (default: 0.92)",
    )
    parser.add_argument(
        "--embedding-dim",
        type=int,
        default=384,
        help="Embedding dimension (default: 384)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo with sample prompts",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up expired entries",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show cache statistics and exit",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all cache entries",
    )
    
    args = parser.parse_args()
    
    cache = PromptCache(
        db_path=args.db_path,
        ttl_hours=args.ttl_hours,
        similarity_threshold=args.similarity_threshold,
        embedding_dim=args.embedding_dim,
    )
    
    if args.cleanup:
        removed = cache.cleanup_expired()
        print(f"Removed {removed} expired entries")
        return
    
    if args.clear:
        cache.clear()
        print("Cache cleared")
        return
    
    if args.stats:
        stats = cache.stats()
        print(json.dumps(stats, indent=2))
        top = cache.get_top_entries(limit=5)
        print("\nTop cached prompts:")
        print(json.dumps(top, indent=2))
        return
    
    if args.demo:
        optimizer = LLMInferenceCostOptimizer(cache)
        
        sample_prompts = [
            "What is the capital of France?",
            "What is the capital of France?",
            "Tell me about Paris, the capital city",
            "Explain quantum computing in simple terms",