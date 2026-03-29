#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build hybrid retrieval pipeline
# Mission: Agentic RAG Infrastructure
# Agent:   @aria
# Date:    2026-03-28T22:02:08.197Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build hybrid retrieval pipeline
Mission: Agentic RAG Infrastructure
Agent: @aria
Date: 2024-01-20

Production-ready hybrid retrieval pipeline with semantic and keyword-based search,
dynamic chunking, ranking, deduplication, and multi-agent coordination.
"""

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Any, Optional
from collections import defaultdict
import math
import hashlib


@dataclass
class Document:
    """Represents a source document."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class Chunk:
    """Represents a document chunk."""
    chunk_id: str
    doc_id: str
    content: str
    start_pos: int
    end_pos: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class RetrievalResult:
    """Represents a single retrieval result."""
    chunk_id: str
    doc_id: str
    content: str
    semantic_score: float
    keyword_score: float
    hybrid_score: float
    rank: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SimpleEmbedding:
    """Lightweight embedding generator based on word statistics."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vocab = {}
        self.vocab_counter = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens
    
    def _get_vocab_id(self, token: str) -> int:
        """Get or create vocab ID for token."""
        if token not in self.vocab:
            self.vocab[token] = self.vocab_counter
            self.vocab_counter += 1
        return self.vocab[token]
    
    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        tokens = self._tokenize(text)
        embedding = [0.0] * self.dimension
        
        token_counts = defaultdict(int)
        for token in tokens:
            token_counts[token] += 1
        
        for token, count in token_counts.items():
            vocab_id = self._get_vocab_id(token)
            idx = vocab_id % self.dimension
            embedding[idx] += count * 0.1
        
        norm = math.sqrt(sum(x**2 for x in embedding))
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding


class DynamicChunker:
    """Handles dynamic document chunking with semantic awareness."""
    
    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 800, 
                 overlap: int = 100):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
    
    def _get_sentences(self, text: str) -> List[Tuple[str, int]]:
        """Extract sentences with positions."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        positions = []
        current_pos = 0
        for sentence in sentences:
            positions.append((sentence, current_pos))
            current_pos += len(sentence) + 1
        return positions
    
    def chunk(self, document: Document) -> List[Chunk]:
        """Dynamically chunk document based on content structure."""
        chunks = []
        text = document.content
        sentences = self._get_sentences(text)
        
        current_chunk = ""
        chunk_start = 0
        chunk_num = 0
        
        for sentence, sent_pos in sentences:
            if len(current_chunk) + len(sentence) <= self.max_chunk_size:
                current_chunk += sentence + " "
            else:
                if len(current_chunk) >= self.min_chunk_size:
                    chunk_id = f"{document.doc_id}_chunk_{chunk_num}"
                    chunk_end = chunk_start + len(current_chunk)
                    chunk = Chunk(
                        chunk_id=chunk_id,
                        doc_id=document.doc_id,
                        content=current_chunk.strip(),
                        start_pos=chunk_start,
                        end_pos=chunk_end,
                        metadata=document.metadata.copy()
                    )
                    chunks.append(chunk)
                    chunk_num += 1
                    chunk_start = max(0, chunk_end - self.overlap)
                
                current_chunk = sentence + " "
        
        if len(current_chunk) >= self.min_chunk_size:
            chunk_id = f"{document.doc_id}_chunk_{chunk_num}"
            chunk_end = chunk_start + len(current_chunk)
            chunk = Chunk(
                chunk_id=chunk_id,
                doc_id=document.doc_id,
                content=current_chunk.strip(),
                start_pos=chunk_start,
                end_pos=chunk_end,
                metadata=document.metadata.copy()
            )
            chunks.append(chunk)
        
        return chunks


class KeywordRetriever:
    """Implements BM25-like keyword-based retrieval."""
    
    def __init__(self):
        self.chunks = {}
        self.inverted_index = defaultdict(list)
        self.doc_lengths = {}
        self.avg_doc_length = 0.0
        self.num_docs = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return [t for t in tokens if len(t) > 2]
    
    def index(self, chunks: List[Chunk]) -> None:
        """Build inverted index from chunks."""
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.inverted_index.clear()
        self.doc_lengths.clear()
        
        total_length = 0
        for chunk in chunks:
            tokens = self._tokenize(chunk.content)
            self.doc_lengths[chunk.chunk_id] = len(tokens)
            total_length += len(tokens)
            
            for token in set(tokens):
                self.inverted_index[token].append(chunk.chunk_id)
        
        self.num_docs = len(chunks)
        self.avg_doc_length = total_length / self.num_docs if self.num_docs > 0 else 0
    
    def _bm25_score(self, tokens: List[str], chunk_id: str, k1: float = 1.5, 
                     b: float = 0.75) -> float:
        """Calculate BM25 score."""
        score = 0.0
        doc_length = self.doc_lengths.get(chunk_id, 0)
        
        for token in set(tokens):
            if token not in self.inverted_index:
                continue
            
            df = len(self.inverted_index[token])
            idf = math.log((self.num_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            tf = tokens.count(token)
            norm_length = 1.0 - b + b * (doc_length / self.avg_doc_length if self.avg_doc_length > 0 else 1.0)
            score += idf * (tf * (k1 + 1.0)) / (tf + k1 * norm_length)
        
        return score
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Retrieve top-k chunks by keyword relevance."""
        tokens = self._tokenize(query)
        
        relevant_chunks = set()
        for token in tokens:
            if token in self.inverted_index:
                relevant_chunks.update(self.inverted_index[token])
        
        scores = []
        for chunk_id in relevant_chunks:
            score = self._bm25_score(tokens, chunk_id)
            scores.append((chunk_id, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class SemanticRetriever:
    """Implements semantic search using embeddings and cosine similarity."""
    
    def __init__(self, embedding_model: Optional[SimpleEmbedding] = None):
        self.embedding_model = embedding_model or SimpleEmbedding()
        self.chunks = {}
        self.embeddings = {}
    
    def index(self, chunks: List[Chunk]) -> None:
        """Index chunks with embeddings."""
        self.chunks = {chunk.chunk_id: chunk for chunk in chunks}
        self.embeddings.clear()
        
        for chunk in chunks:
            embedding = self.embedding_model.embed(chunk.content)
            self.embeddings[chunk.chunk_id] = embedding
            chunk.embedding = embedding
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a**2 for a in vec1))
        norm2 = math.sqrt(sum(b**2 for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def retrieve(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Retrieve top-k chunks by semantic similarity."""
        query_embedding = self.embedding_model.embed(query)
        
        scores = []
        for chunk_id, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            scores.append((chunk_id, similarity))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridRetriever:
    """Combines semantic and keyword retrieval with intelligent ranking."""
    
    def __init__(self, alpha: float = 0.5):
        self.alpha = alpha  # Weight for semantic score (1-alpha for keyword)
        self.keyword_retriever = KeywordRetriever()
        self.semantic_retriever = SemanticRetriever()
        self.chunks = {}
    
    def index(self, documents: List[Document]) -> None:
        """Index documents using dynamic chunking."""
        all_chunks = []
        chunker = DynamicChunker()
        
        for doc in documents:
            chunks = chunker.chunk(doc)
            all_chunks.extend(chunks)
        
        self.chunks = {chunk.chunk_id: chunk for chunk in all_chunks}
        self.keyword_retriever.index(all_chunks)
        self.semantic_retriever.index(all_chunks)
    
    def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """Retrieve and rank results using hybrid approach."""
        keyword_results = dict(self.keyword_retriever.retrieve(query, top_k * 2))
        semantic_results = dict(self.semantic_retriever.retrieve(query, top_k * 2))
        
        all_chunk_ids = set(keyword_results.keys()) | set(semantic_results.keys())
        
        hybrid_scores = []
        for chunk_id in all_chunk_ids:
            semantic_score = semantic_results.get(chunk_id, 0.0)
            keyword_score = keyword_results.get(chunk_id, 0.0)
            
            norm_semantic = semantic_score
            norm_keyword = keyword_score / (max(keyword_results.values()) if keyword_results else 1.0)
            
            hybrid_score = self.alpha * norm_semantic + (1 - self.alpha) * norm_keyword
            hybrid_scores.append((chunk_id, semantic_score, keyword_score, hybrid_score))
        
        hybrid_scores.sort(key=lambda x: x[3], reverse=True)
        
        results = []
        for rank, (chunk_id, sem_score, kw_score, hyb_score) in enumerate(hybrid_scores[:top_k]):
            chunk = self.chunks[chunk_id]
            result = RetrievalResult(
                chunk_id=chunk_id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                semantic_score=sem_score,
                keyword_score=kw_score,
                hybrid_score=hyb_score,
                rank=rank + 1,
                metadata=chunk.metadata
            )
            results.append(result)
        
        return results


class Deduplicator:
    """Removes duplicate or near-duplicate chunks."""
    
    @staticmethod
    def _content_hash(text: str) -> str:
        """Generate hash of content."""
        return hashlib.md5(text.lower().encode()).hexdigest()
    
    @staticmethod
    def _jaccard_similarity(set1: set, set2: set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _get_shingles(text: str, k: int = 3) -> set:
        """Generate k-shingles from text."""
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        shingles = set()
        for i in range(len(tokens) - k + 1):
            shingle = ' '.join(tokens[i:i+k])
            shingles.add(shingle)
        return shingles
    
    @staticmethod
    def deduplicate(results: List[RetrievalResult], 
                    threshold: float = 0.85) -> List[RetrievalResult]:
        """Remove near-duplicates from results."""
        if not results:
            return results
        
        deduplicated = []
        seen_hashes = set()
        
        for result in results:
            content_hash = Deduplicator._content_hash(result.content)
            
            if content_hash in seen_hashes:
                continue
            
            shingles = Deduplicator._get_shingles(result.content)
            is_duplicate = False
            
            for ded_result in deduplicated:
                ded_shingles = Deduplicator._get_shingles(ded_result.content)
                similarity = Deduplicator._jaccard_similarity(shingles, ded_shingles)
                if similarity >= threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
                seen_hashes.add(content_hash)
        
        return