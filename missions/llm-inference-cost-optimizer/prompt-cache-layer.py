#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Prompt cache layer
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-23T18:09:30.530Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""LRU cache with semantic similarity deduplication for LLM prompt caching."""

import argparse
import json
import logging
import math
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.95
DEFAULT_CACHE_SIZE = 1000


@dataclass
class CacheEntry:
    key: str
    prompt: str
    response: str
    embedding: list[float]
    created_at: float = field(default_factory=time.time)
    hit_count: int = 0
    last_accessed: float = field(default_factory=time.time)


def tokenize(text: str) -> list[str]:
    return [w.lower().strip(".,!?;:\"'()[]") for w in text.split() if len(w) > 1]


def compute_tfidf_embedding(text: str, dim: int = 128) -> list[float]:
    """Compute a deterministic TF-IDF-inspired sparse embedding."""
    import hashlib
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dim
    tf: dict[str, float] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1
    for k in tf:
        tf[k] = tf[k] / len(tokens)
    vec = [0.0] * dim
    for token, weight in tf.items():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(3):
            idx = (h >> (i * 10)) % dim
            vec[idx] += weight * math.log1p(len(tokens))
    norm = math.sqrt(sum(x * x for x in vec)) + 1e-9
    return [x / norm for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))


class SemanticLRUCache:
    def __init__(self, max_size: int = DEFAULT_CACHE_SIZE, similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD) -> None:
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self._lru: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._semantic_hits = 0

    def _make_key(self, prompt: str) -> str:
        import hashlib
        return hashlib.sha256(prompt.strip().encode()).hexdigest()[:16]

    def get(self, prompt: str) -> Optional[str]:
        key = self._make_key(prompt)
        if key in self._lru:
            entry = self._lru[key]
            self._lru.move_to_end(key)
            entry.hit_count += 1
            entry.last_accessed = time.time()
            self._hits += 1
            logger.debug(f"Cache HIT (exact): {prompt[:50]}")
            return entry.response

        query_emb = compute_tfidf_embedding(prompt)
        best_sim = 0.0
        best_key = None
        for k, entry in self._lru.items():
            sim = cosine_similarity(query_emb, entry.embedding)
            if sim > best_sim:
                best_sim = sim
                best_key = k

        if best_key and best_sim >= self.similarity_threshold:
            entry = self._lru[best_key]
            self._lru.move_to_end(best_key)
            entry.hit_count += 1
            entry.last_accessed = time.time()
            self._hits += 1
            self._semantic_hits += 1
            logger.debug(f"Cache HIT (semantic, sim={best_sim:.3f}): {prompt[:50]}")
            return entry.response

        self._misses += 1
        logger.debug(f"Cache MISS (best_sim={best_sim:.3f}): {prompt[:50]}")
        return None

    def put(self, prompt: str, response: str) -> None:
        key = self._make_key(prompt)
        embedding = compute_tfidf_embedding(prompt)
        entry = CacheEntry(key=key, prompt=prompt, response=response, embedding=embedding)
        if key in self._lru:
            self._lru.move_to_end(key)
        self._lru[key] = entry
        if len(self._lru) > self.max_size:
            evicted_key, _ = self._lru.popitem(last=False)
            logger.debug(f"Evicted cache entry: {evicted_key}")

    def get_stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {"size": len(self._lru), "max_size": self.max_size, "total_requests": total, "hits": self._hits, "misses": self._misses, "semantic_hits": self._semantic_hits, "hit_rate": round(self._hits / max(total, 1), 3), "similarity_threshold": self.similarity_threshold}

    def clear(self) -> None:
        self._lru.clear()
        self._hits = self._misses = self._semantic_hits = 0


def simulate_llm_call(prompt: str, cache: SemanticLRUCache) -> tuple[str, bool]:
    cached = cache.get(prompt)
    if cached:
        return cached, True
    response = f"[LLM Response to: {prompt[:60]}...]"
    cache.put(prompt, response)
    return response, False


def main() -> None:
    parser = argparse.ArgumentParser(description="Semantic LRU cache for LLM prompts")
    parser.add_argument("--max-size", type=int, default=1000)
    parser.add_argument("--similarity-threshold", type=float, default=0.95)
    parser.add_argument("--output", default="cache_stats.json")
    parser.add_argument("--demo", action="store_true", default=True)
    args = parser.parse_args()

    cache = SemanticLRUCache(max_size=args.max_size, similarity_threshold=args.similarity_threshold)

    if args.demo:
        prompts = [
            "What is the capital of France?",
            "Tell me the capital city of France",
            "What's the capital of France?",
            "Explain machine learning",
            "Can you explain machine learning to me?",
            "What is machine learning?",
            "How do I sort a list in Python?",
            "How to sort a Python list?",
            "Sorting lists in Python",
            "What is the weather today?",
        ]
        logger.info(f"Running cache demo with {len(prompts)} prompts (threshold={args.similarity_threshold})")
        for prompt in prompts:
            response, was_cached = simulate_llm_call(prompt, cache)
            status = "CACHED" if was_cached else "MISS"
            logger.info(f"  [{status}] {prompt[:60]}")

    stats = cache.get_stats()
    with open(args.output, "w") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Cache stats: {stats['hits']}/{stats['total_requests']} hits ({stats['hit_rate']:.1%}), {stats['semantic_hits']} semantic hits")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
