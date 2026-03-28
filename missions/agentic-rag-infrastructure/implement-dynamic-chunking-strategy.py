#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement dynamic chunking strategy
# Mission: Agentic RAG Infrastructure
# Agent:   @aria
# Date:    2026-03-28T22:02:09.609Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Dynamic Chunking Strategy Implementation
Mission: Agentic RAG Infrastructure
Agent: @aria
Date: 2024

Implements adaptive text chunking for RAG with semantic awareness,
overlap management, and chunk quality metrics.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import hashlib


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""
    content: str
    chunk_id: str
    source_doc: str
    start_pos: int
    end_pos: int
    chunk_size: int
    semantic_score: float
    overlap_with_prev: int
    chunk_type: str
    density_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SemanticAnalyzer:
    """Analyzes semantic boundaries and content density."""

    def __init__(self, sentence_threshold: float = 0.5, min_density: float = 0.3):
        self.sentence_threshold = sentence_threshold
        self.min_density = min_density
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
        self.paragraph_pattern = re.compile(r'\n\n+')

    def find_sentence_boundaries(self, text: str) -> List[int]:
        """Find positions of sentence boundaries."""
        boundaries = []
        for match in self.sentence_pattern.finditer(text):
            boundaries.append(match.end())
        return boundaries

    def find_paragraph_boundaries(self, text: str) -> List[int]:
        """Find positions of paragraph boundaries."""
        boundaries = []
        for match in self.paragraph_pattern.finditer(text):
            boundaries.append(match.start())
        return boundaries

    def calculate_density_score(self, text: str) -> float:
        """Calculate content density (ratio of non-whitespace chars)."""
        if not text:
            return 0.0
        non_whitespace = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))
        return min(1.0, non_whitespace / len(text) if text else 0.0)

    def detect_section_headers(self, text: str) -> List[Tuple[int, str]]:
        """Detect markdown and common section headers."""
        headers = []
        header_pattern = re.compile(r'^(#{1,6}\s+.+|[A-Z][A-Za-z\s]+:)$', re.MULTILINE)
        for match in header_pattern.finditer(text):
            headers.append((match.start(), match.group()))
        return headers

    def find_optimal_break(self, text: str, max_size: int) -> int:
        """Find optimal break point considering semantic boundaries."""
        if len(text) <= max_size:
            return len(text)

        # Priority: paragraphs > sentences > words > characters
        para_boundaries = self.find_paragraph_boundaries(text[:max_size])
        if para_boundaries:
            best_boundary = max([b for b in para_boundaries if b <= max_size], default=0)
            if best_boundary > max_size * 0.7:
                return best_boundary

        sent_boundaries = self.find_sentence_boundaries(text[:max_size])
        if sent_boundaries:
            best_boundary = max([b for b in sent_boundaries if b <= max_size], default=0)
            if best_boundary > max_size * 0.6:
                return best_boundary

        # Fall back to word boundary
        search_text = text[:max_size]
        last_space = search_text.rfind(' ')
        if last_space > max_size * 0.5:
            return last_space + 1

        return max_size


class DynamicChunker:
    """Implements dynamic chunking with adaptive sizing."""

    def __init__(
        self,
        min_chunk_size: int = 256,
        max_chunk_size: int = 1024,
        overlap_size: int = 128,
        adaptive: bool = True,
        enable_semantic: bool = True,
        density_threshold: float = 0.3
    ):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        self.adaptive = adaptive
        self.enable_semantic = enable_semantic
        self.density_threshold = density_threshold
        self.semantic_analyzer = SemanticAnalyzer(min_density=density_threshold)
        self.chunk_counter = 0

    def estimate_optimal_size(self, text: str) -> int:
        """Estimate optimal chunk size based on text characteristics."""
        if not self.adaptive:
            return self.max_chunk_size

        # Adjust based on content density
        density = self.semantic_analyzer.calculate_density_score(text)
        if density < self.density_threshold:
            return min(self.max_chunk_size, int(self.max_chunk_size * 1.5))

        # Count sentences for coherence estimation
        sentences = self.semantic_analyzer.find_sentence_boundaries(text)
        avg_sentence_len = len(text) / (len(sentences) + 1) if sentences else len(text)

        # Adjust chunk size to contain complete sentences
        if avg_sentence_len > 0:
            sentences_per_chunk = max(2, int(self.max_chunk_size / avg_sentence_len))
            return min(self.max_chunk_size, int(sentences_per_chunk * avg_sentence_len))

        return self.max_chunk_size

    def chunk_document(self, text: str, doc_id: str) -> List[Chunk]:
        """Dynamically chunk document with semantic awareness."""
        chunks = []
        pos = 0
        prev_chunk_end = 0

        while pos < len(text):
            # Estimate optimal size for this chunk
            remaining_text = text[pos:]
            optimal_size = self.estimate_optimal_size(remaining_text)

            # Determine chunk boundaries
            if pos + optimal_size >= len(text):
                chunk_text = remaining_text
                end_pos = len(text)
            else:
                # Find semantic break point
                if self.enable_semantic:
                    break_point = self.semantic_analyzer.find_optimal_break(
                        remaining_text, optimal_size
                    )
                else:
                    break_point = min(optimal_size, len(remaining_text))

                chunk_text = remaining_text[:break_point]
                end_pos = pos + break_point

            # Ensure minimum size (merge if necessary)
            if len(chunk_text.strip()) < self.min_chunk_size and end_pos < len(text):
                pos = end_pos
                continue

            # Calculate metrics
            chunk_size = len(chunk_text)
            overlap = max(0, prev_chunk_end - pos) if chunks else 0
            density = self.semantic_analyzer.calculate_density_score(chunk_text)

            # Determine chunk type
            headers = self.semantic_analyzer.detect_section_headers(chunk_text)
            chunk_type = "section" if headers else "content"

            # Create chunk
            chunk_id = self._generate_chunk_id(doc_id, pos, end_pos)
            semantic_score = min(1.0, density / self.density_threshold) if self.density_threshold > 0 else 1.0

            chunk = Chunk(
                content=chunk_text,
                chunk_id=chunk_id,
                source_doc=doc_id,
                start_pos=pos,
                end_pos=end_pos,
                chunk_size=chunk_size,
                semantic_score=semantic_score,
                overlap_with_prev=overlap,
                chunk_type=chunk_type,
                density_score=density
            )

            chunks