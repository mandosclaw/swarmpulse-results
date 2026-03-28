#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build prompt cache layer
# Mission: LLM Inference Cost Optimizer
# Agent:   @bolt
# Date:    2026-03-28T22:04:36.101Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build prompt cache layer
Mission: LLM Inference Cost Optimizer
Agent: @bolt
Date: 2024-01-15

Intelligent middleware that implements prompt caching for LLM inference,
reducing costs by reusing cached responses for identical or similar prompts.
"""

import argparse
import hashlib
import json
import time
import sqlite3
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class CacheStrategy(Enum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


@dataclass
class CacheEntry:
    prompt_hash: str
    prompt_text: str
    model: str
    response: str
    timestamp: float
    ttl_seconds: int
    hits: int
    cost_saved: float
    
    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl_seconds


@dataclass
class CacheStats:
    total_requests: int
    cache_hits: int
    cache_misses: int
    total_cost_saved: float
    hit_rate: float
    avg_response_time_ms: float
    storage_size_mb: float


class PromptCacheLayer:
    def __init__(self, db_path: str, cache_strategy: CacheStrategy = CacheStrategy.EXACT, max_cache_size_mb: int = 1024):
        self.db_path = db_path
        self.cache_strategy = cache_strategy
        self.max_cache_size_mb = max_cache_size_mb
        self.response_times: List[float] = []
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for cache storage."""
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY,
                prompt_hash TEXT UNIQUE,
                prompt_text TEXT,
                model TEXT,
                response TEXT,
                timestamp REAL,
                ttl_seconds INTEGER,
                hits INTEGER DEFAULT 0,
                cost_saved REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_stats (
                id INTEGER PRIMARY KEY,
                timestamp REAL,
                total_requests INTEGER,
                cache_hits INTEGER,
                cache_misses INTEGER,
                total_cost_saved REAL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_prompt_hash ON cache_entries(prompt_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model ON cache_entries(model)
        """)
        
        conn.commit()
        conn.close()
    
    def _compute_hash(self, prompt: str, model: str = "", include_semantic: bool = False) -> str:
        """Compute hash of prompt for caching."""
        base_text = f"{prompt}:{model}".strip()
        
        if include_semantic:
            normalized = self._normalize_prompt(base_text)
            return hashlib.sha256(normalized.encode()).hexdigest()
        else:
            return hashlib.sha256(base_text.encode()).hexdigest()
    
    def _normalize_prompt(self, prompt: str) -> str:
        """Normalize prompt for semantic similarity."""
        normalized = prompt.lower().strip()
        normalized = " ".join(normalized.split())
        normalized = "".join(c for c in normalized if c.isalnum() or c.isspace())
        return normalized
    
    def _semantic_similarity(self, prompt1: str, prompt2: str, threshold: float = 0.85) -> bool:
        """Calculate semantic similarity between two prompts."""
        norm1_set = set(self._normalize_prompt(prompt1).split())
        norm2_set = set(self._normalize_prompt(prompt2).split())
        
        if not norm1_set or not norm2_set:
            return False
        
        intersection = len(norm1_set & norm2_set)
        union = len(norm1_set | norm2_set)
        jaccard_similarity = intersection / union if union > 0 else 0
        
        return jaccard_similarity >= threshold
    
    def get(self, prompt: str, model: str, use_semantic: bool = False) -> Optional[Tuple[str, Dict]]:
        """Retrieve cached response if available."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if use_semantic and self.cache_strategy in (CacheStrategy.SEMANTIC, CacheStrategy.HYBRID):
            cursor.execute("SELECT prompt_text, response, hits, cost_saved, timestamp FROM cache_entries WHERE model = ?", (model,))
            rows = cursor.fetchall()
            
            for row in rows:
                cached_prompt, response, hits, cost_saved, timestamp = row
                entry = CacheEntry(
                    prompt_hash="",
                    prompt_text=cached_prompt,
                    model=model,
                    response=response,
                    timestamp=timestamp,
                    ttl_seconds=3600,
                    hits=hits,
                    cost_saved=cost_saved
                )
                
                if not entry.is_expired() and self._semantic_similarity(prompt, cached_prompt):
                    self._update_hit(cursor, conn, cached_prompt, model)
                    conn.close()
                    return response, {"hit_type": "semantic", "previous_prompt": cached_prompt}
        
        prompt_hash = self._compute_hash(prompt, model, include_semantic=False)
        cursor.execute(
            "SELECT response, hits, cost_saved, timestamp FROM cache_entries WHERE prompt_hash = ? AND model = ?",
            (prompt_hash, model)
        )
        row = cursor.fetchone()
        
        if row:
            response, hits, cost_saved, timestamp = row
            entry = CacheEntry(
                prompt_hash=prompt_hash,
                prompt_text=prompt,
                model=model,
                response=response,
                timestamp=timestamp,
                ttl_seconds=3600,
                hits=hits,
                cost_saved=cost_saved
            )
            
            if not entry.is_expired():
                self._update_hit(cursor, conn, prompt, model)
                conn.close()
                return response, {"hit_type": "exact"}
        
        conn.close()
        return None
    
    def _update_hit(self, cursor, conn, prompt: str, model: str):
        """Update hit count for a cache entry."""
        prompt_hash = self._compute_hash(prompt, model)
        cursor.execute(
            "UPDATE cache_entries SET hits = hits + 1 WHERE prompt_hash = ? AND model = ?",
            (prompt_hash, model)
        )
        conn.commit()
    
    def put(self, prompt: str, model: str, response: str, cost: float = 0.0, ttl_seconds: int = 3600):
        """Store response in cache."""
        prompt_hash = self._compute_hash(prompt, model)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO cache_entries 
                (prompt_hash, prompt_text, model, response, timestamp, ttl_seconds, hits, cost_saved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (prompt_hash, prompt, model, response, time.time(), ttl_seconds, 0, cost