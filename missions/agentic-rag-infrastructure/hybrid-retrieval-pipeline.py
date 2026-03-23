#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Hybrid retrieval pipeline
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-23T17:53:07.687Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Hybrid retrieval pipeline: BM25 sparse + cosine dense retrieval, re-ranked with RRF."""

import argparse
import json
import logging
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class Document:
    doc_id: str
    text: str
    embedding: list[float] = field(default_factory=list)


@dataclass
class RetrievalResult:
    doc_id: str
    text: str
    bm25_rank: int = 0
    dense_rank: int = 0
    rrf_score: float = 0.0


def tokenize(text: str) -> list[str]:
    return [w.lower().strip(".,!?;:") for w in text.split() if len(w) > 1]


class BM25:
    def __init__(self, docs: list[Document], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.docs = docs
        self.doc_tokens = [tokenize(d.text) for d in docs]
        self.avgdl = sum(len(t) for t in self.doc_tokens) / max(len(self.doc_tokens), 1)
        self.df: dict[str, int] = defaultdict(int)
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] += 1
        self.N = len(docs)

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.N - df + 0.5) / (df + 0.5) + 1)

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        tokens = self.doc_tokens[doc_idx]
        dl = len(tokens)
        tf_map: dict[str, int] = defaultdict(int)
        for t in tokens:
            tf_map[t] += 1
        score = 0.0
        for term in query_tokens:
            tf = tf_map.get(term, 0)
            idf = self.idf(term)
            tf_norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            score += idf * tf_norm
        return score

    def retrieve(self, query: str, top_k: int = 10) -> list[tuple[int, float]]:
        qterms = tokenize(query)
        scores = [(i, self.score(qterms, i)) for i in range(self.N)]
        return sorted(scores, key=lambda x: -x[1])[:top_k]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b + 1e-9)


def simple_embedding(text: str, dim: int = 64) -> list[float]:
    """Deterministic pseudo-embedding for demonstration."""
    import hashlib
    tokens = tokenize(text)
    vec = [0.0] * dim
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(dim):
            vec[i] += math.sin(h * (i + 1) * 0.001)
    norm = math.sqrt(sum(x * x for x in vec)) + 1e-9
    return [x / norm for x in vec]


def dense_retrieve(query_emb: list[float], docs: list[Document], top_k: int = 10) -> list[tuple[int, float]]:
    scores = [(i, cosine_similarity(query_emb, d.embedding)) for i, d in enumerate(docs)]
    return sorted(scores, key=lambda x: -x[1])[:top_k]


def reciprocal_rank_fusion(rankings: list[list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float]]:
    rrf_scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, (doc_idx, _) in enumerate(ranking, start=1):
            rrf_scores[doc_idx] += 1.0 / (k + rank)
    return sorted(rrf_scores.items(), key=lambda x: -x[1])


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid BM25 + Dense retrieval with RRF")
    parser.add_argument("--query", default="agent task monitoring performance metrics")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus", default=None, help="JSON file with documents [{id, text}]")
    args = parser.parse_args()

    if args.corpus:
        with open(args.corpus) as f:
            raw = json.load(f)
        docs = [Document(doc_id=r["id"], text=r["text"]) for r in raw]
    else:
        corpus_texts = [
            ("doc-1", "Agent monitoring tracks task completion rates and performance metrics"),
            ("doc-2", "BM25 is a sparse retrieval algorithm based on term frequency and inverse document frequency"),
            ("doc-3", "Dense retrieval uses neural embeddings and cosine similarity for semantic search"),
            ("doc-4", "Reciprocal rank fusion combines results from multiple retrieval systems"),
            ("doc-5", "Daily metrics summaries help track agent activity and system health"),
            ("doc-6", "Task scheduling and priority queues improve agent throughput"),
            ("doc-7", "Logging and observability are critical for production AI systems"),
            ("doc-8", "Vector databases store embeddings for fast nearest-neighbor search"),
        ]
        docs = [Document(doc_id=did, text=txt) for did, txt in corpus_texts]

    logger.info(f"Building embeddings for {len(docs)} documents")
    for doc in docs:
        doc.embedding = simple_embedding(doc.text)

    bm25 = BM25(docs)
    query_emb = simple_embedding(args.query)

    logger.info(f"Running BM25 retrieval for: {args.query}")
    bm25_results = bm25.retrieve(args.query, top_k=args.top_k * 2)

    logger.info("Running dense retrieval")
    dense_results = dense_retrieve(query_emb, docs, top_k=args.top_k * 2)

    logger.info("Fusing results with RRF")
    fused = reciprocal_rank_fusion([bm25_results, dense_results])[:args.top_k]

    output = {"query": args.query, "top_k": args.top_k, "results": [{"rank": i + 1, "doc_id": docs[idx].doc_id, "text": docs[idx].text[:120], "rrf_score": round(score, 6)} for i, (idx, score) in enumerate(fused)]}

    print(json.dumps(output, indent=2))
    logger.info(f"Retrieved {len(fused)} results")


if __name__ == "__main__":
    main()
