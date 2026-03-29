#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build hybrid retrieval pipeline
# Mission: Agentic RAG Infrastructure
# Agent:   @aria
# Date:    2026-03-29T13:15:38.408Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build hybrid retrieval pipeline
Mission: Agentic RAG Infrastructure
Agent: @aria
Date: 2024

Production-ready Retrieval-Augmented Generation infrastructure with hybrid retrieval,
dynamic chunking, hallucination detection, and multi-agent coordination.
"""

import argparse
import json
import hashlib
import math
import re
import sys
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
from enum import Enum


class RetrievalStrategy(Enum):
    """Retrieval strategy enum."""
    SEMANTIC = "semantic"
    LEXICAL = "lexical"
    HYBRID = "hybrid"
    DENSE = "dense"
    SPARSE = "sparse"


@dataclass
class Document:
    """Document representation."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    tokens: Optional[List[str]] = None
    chunk_id: Optional[str] = None
    score: float = 0.0


@dataclass
class Chunk:
    """Text chunk with metadata."""
    chunk_id: str
    text: str
    doc_id: str
    start_pos: int
    end_pos: int
    tokens: List[str]
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    coherence_score: float = 1.0


@dataclass
class RetrievalResult:
    """Retrieval result with scoring."""
    chunk: Chunk
    score: float
    strategy: str
    rank: int
    hallucination_risk: float = 0.0
    confidence: float = 1.0


@dataclass
class HallucinationAnalysis:
    """Hallucination detection result."""
    risk_score: float
    indicators: List[str]
    is_hallucination: bool
    confidence: float
    evidence: List[str]


class SimpleTokenizer:
    """Simple tokenizer for demonstration."""

    @staticmethod
    def tokenize(text: str) -> List[str]:
        """Tokenize text into words."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    @staticmethod
    def detokenize(tokens: List[str]) -> str:
        """Reconstruct text from tokens."""
        return " ".join(tokens)


class SimpleEmbedder:
    """Simple embedding generator using hash-based vectors."""

    @staticmethod
    def embed(text: str, dim: int = 384) -> List[float]:
        """Generate deterministic embedding from text."""
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        embedding = []
        for i in range(dim):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val - 128) / 128.0)
        norm = math.sqrt(sum(x**2 for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        if not vec1 or not vec2:
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(x**2 for x in vec1))
        norm2 = math.sqrt(sum(x**2 for x in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)


class DynamicChunker:
    """Dynamic text chunking with adaptive boundaries."""

    def __init__(self, min_chunk_size: int = 100, max_chunk_size: int = 500,
                 overlap: int = 50):
        """Initialize chunker."""
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.tokenizer = SimpleTokenizer()

    def chunk_document(self, doc: Document) -> List[Chunk]:
        """Chunk document with intelligent boundaries."""
        chunks = []
        text = doc.content
        tokens = self.tokenizer.tokenize(text)

        sentences = self._split_sentences(text)
        current_chunk_tokens = []
        current_chunk_text = ""
        start_pos = 0
        chunk_count = 0

        for sentence in sentences:
            sentence_tokens = self.tokenizer.tokenize(sentence)
            potential_tokens = current_chunk_tokens + sentence_tokens

            if len(potential_tokens) > self.max_chunk_size:
                if current_chunk_tokens:
                    chunk = self._create_chunk(
                        doc.doc_id,
                        current_chunk_text,
                        start_pos,
                        chunk_count
                    )
                    chunks.append(chunk)
                    chunk_count += 1
                    start_pos += len(current_chunk_text)

                    overlap_tokens = current_chunk_tokens[-self.overlap:]
                    overlap_text = self.tokenizer.detokenize(overlap_tokens)
                    current_chunk_tokens = sentence_tokens
                    current_chunk_text = sentence
                else:
                    chunk = self._create_chunk(
                        doc.doc_id,
                        sentence,
                        start_pos,
                        chunk_count
                    )
                    chunks.append(chunk)
                    chunk_count += 1
                    start_pos += len(sentence)
                    current_chunk_tokens = []
                    current_chunk_text = ""
            else:
                current_chunk_tokens = potential_tokens
                current_chunk_text += (" " if current_chunk_text else "") + sentence

        if current_chunk_tokens:
            chunk = self._create_chunk(
                doc.doc_id,
                current_chunk_text,
                start_pos,
                chunk_count
            )
            chunks.append(chunk)

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunk(self, doc_id: str, text: str, start_pos: int,
                      chunk_idx: int) -> Chunk:
        """Create chunk object."""
        chunk_id = f"{doc_id}_chunk_{chunk_idx}_{uuid.uuid4().hex[:8]}"
        tokens = self.tokenizer.tokenize(text)
        embedding = SimpleEmbedder.embed(text)
        coherence = self._calculate_coherence(text)

        return Chunk(
            chunk_id=chunk_id,
            text=text,
            doc_id=doc_id,
            start_pos=start_pos,
            end_pos=start_pos + len(text),
            tokens=tokens,
            embedding=embedding,
            coherence_score=coherence
        )

    def _calculate_coherence(self, text: str) -> float:
        """Calculate text coherence score."""
        tokens = self.tokenizer.tokenize(text)
        if len(tokens) < 2:
            return 0.5
        unique_tokens = len(set(tokens))
        coherence = unique_tokens / len(tokens) if tokens else 0.0
        return min(1.0, max(0.0, coherence))


class LexicalRetriever:
    """Lexical (BM25-style) retrieval."""

    def __init__(self):
        """Initialize retriever."""
        self.chunks: List[Chunk] = []
        self.tokenizer = SimpleTokenizer()
        self.term_freqs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.doc_freqs: Dict[str, int] = defaultdict(int)
        self.chunk_lengths: Dict[str, int] = {}

    def index(self, chunks: List[Chunk]) -> None:
        """Index chunks for lexical search."""
        self.chunks = chunks
        for chunk in chunks:
            tokens = chunk.tokens
            seen_tokens = set()
            for token in tokens:
                self.term_freqs[token][chunk.chunk_id] += 1
                if token not in seen_tokens:
                    self.doc_freqs[token] += 1
                    seen_tokens.add(token)
            self.chunk_lengths[chunk.chunk_id] = len(tokens)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Retrieve chunks using BM25-style scoring."""
        query_tokens = self.tokenizer.tokenize(query)
        scores: Dict[str, float] = defaultdict(float)
        avg_chunk_len = sum(self.chunk_lengths.values()) / len(self.chunk_lengths) \
            if self.chunk_lengths else 100

        k1 = 1.5
        b = 0.75

        for token in query_tokens:
            idf = math.log(1 + len(self.chunks) / (self.doc_freqs.get(token, 0) + 1))
            for chunk_id, tf in self.term_freqs[token].items():
                chunk_len = self.chunk_lengths.get(chunk_id, avg_chunk_len)
                bm25_score = idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * (chunk_len / avg_chunk_len))
                )
                scores[chunk_id] += bm25_score

        results = []
        for chunk in self.chunks:
            if chunk.chunk_id in scores:
                results.append(RetrievalResult(
                    chunk=chunk,
                    score=scores[chunk.chunk_id],
                    strategy=RetrievalStrategy.LEXICAL.value,
                    rank=0
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        for i, result in enumerate(results[:top_k]):
            result.rank = i + 1
        return results[:top_k]


class SemanticRetriever:
    """Semantic (embedding-based) retrieval."""

    def __init__(self):
        """Initialize retriever."""
        self.chunks: List[Chunk] = []
        self.embedder = SimpleEmbedder()

    def index(self, chunks: List[Chunk]) -> None:
        """Index chunks for semantic search."""
        self.chunks = chunks
        for chunk in chunks:
            if chunk.embedding is None:
                chunk.embedding = self.embedder.embed(chunk.text)

    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """Retrieve chunks using semantic similarity."""
        query_embedding = self.embedder.embed(query)
        scores: List[Tuple[str, float]] = []

        for chunk in self.chunks:
            if chunk.embedding is None:
                chunk.embedding = self.embedder.embed(chunk.text)
            similarity = self.embedder.cosine_similarity(query_embedding, chunk.embedding)
            scores.append((chunk.chunk_id, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for rank, (chunk_id, score) in enumerate(scores[:top_k]):
            chunk = next(c for c in self.chunks if c.chunk_id == chunk_id)
            results.append(RetrievalResult(
                chunk=chunk,
                score=score,
                strategy=RetrievalStrategy.SEMANTIC.value,
                rank=rank + 1
            ))
        return results


class HallucinationDetector:
    """Detect and measure hallucination risks."""

    def __init__(self):
        """Initialize detector."""
        self.tokenizer = SimpleTokenizer()
        self.hallucination_patterns = [
            r'\b(maybe|perhaps|might|could|seems|appears|suggests)\b',
            r'\b(supposedly|allegedly|rumor|claim|believe)\b',
            r'\b(uncertain|unclear|ambiguous|vague|unclear)\b',
        ]

    def detect(self, query: str, retrieved_chunks: List[RetrievalResult],
               generated_response: str) -> HallucinationAnalysis:
        """Detect hallucination indicators."""
        indicators = []
        evidence = []
        risk_score = 0.0

        response_tokens = set(self.tokenizer.tokenize(generated_response))
        query_tokens = set(self.tokenizer.tokenize(query))
        retrieved_tokens = set()
        for result in retrieved_chunks:
            retrieved_tokens.update(result.chunk.tokens)

        unsupported_tokens = response_tokens - retrieved_tokens - query_tokens
        if unsupported_tokens:
            unsupported_ratio = len(unsupported_tokens) / len(response_tokens) \
                if response_tokens else 0
            if unsupported_ratio > 0.15:
                indicators.append("novel_tokens")
                evidence.append(f"Found {len(unsupported_tokens)} unsupported tokens")
                risk_score += 0.3

        for pattern in self.hallucination_patterns:
            matches = re.findall(pattern, generated_response.lower())
            if matches:
                indicators.append(f"uncertainty_marker:{pattern[:20]}")
                evidence.append(f"Found uncertainty markers: {matches}")
                risk_score += 0.2

        response_len = len(response_tokens)
        retrieved_len = len(retrieved_tokens)
        if retrieved_len > 0 and response_len > retrieved_len * 2:
            indicators.append("excessive_elaboration")
            evidence.append(f"Response length {response_len} >> retrieved length {retrieved_len}")
            risk_score += 0.2

        min_score = min((r.score for r in retrieved_chunks), default=0.5)
        if min_score < 0.3:
            indicators.append("low_retrieval_confidence")
            evidence.append(f"Minimum retrieval score: {min_score}")
            risk_score += 0.15

        risk_score = min(1.0, risk_score)
        is_hallucination = risk_score > 0.5

        return HallucinationAnalysis(
            risk_score=risk_score,
            indicators=indicators,
            is_hallucination=is_hallucination,
            confidence=1.0 - (risk_score * 0.5),
            evidence=evidence
        )


class HybridRetriever:
    """Hybrid retrieval combining lexical and semantic approaches."""

    def __init__(self, alpha: float = 0.5):
        """Initialize hybrid retriever."""
        self.alpha = alpha
        self.lexical = LexicalRetriever()
        self.semantic = SemanticRetriever()
        self.chunker = DynamicChunker()
        self.hallucination_detector = HallucinationDetector()
        self.documents: Dict[str, Document] = {}
        self.chunks: List[Chunk] = []

    def add_document(self, doc: Document) -> None:
        """Add document to retrieval pipeline."""
        self.documents[doc.doc_id] = doc
        chunks = self.chunker.chunk_document(doc)
        self.chunks.extend(chunks)
        self.lexical.index(self.chunks)
        self.semantic.index(self.chunks)

    def retrieve(self, query: str, top_k: int = 5,
                 strategy: str = "hybrid") -> List[RetrievalResult]:
        """Retrieve chunks using specified strategy."""
        if strategy == RetrievalStrategy.HYBRID.value:
            lexical_results = self.lexical