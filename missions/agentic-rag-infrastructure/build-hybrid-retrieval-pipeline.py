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
            norm_length = 1.0 - b + b * (doc_length / self.avg_doc_length if self.