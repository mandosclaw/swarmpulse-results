#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Dynamic chunking strategy
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-23T17:53:09.315Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Dynamic chunking with semantic boundary detection and content-density-based chunk sizing."""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    base_chunk_size: int = 512
    min_chunk_size: int = 128
    max_chunk_size: int = 1024
    overlap_tokens: int = 32
    density_threshold: float = 0.6


@dataclass
class Chunk:
    chunk_id: int
    text: str
    start_char: int
    end_char: int
    token_count: int
    density_score: float
    boundary_type: str


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def compute_density(text: str) -> float:
    """Compute content density: ratio of content words to total words."""
    words = text.split()
    if not words:
        return 0.0
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "shall", "can", "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "and", "or", "but", "if", "then", "than", "so", "yet", "both", "nor", "not", "no", "this", "that", "these", "those", "it", "its", "i", "we", "you", "he", "she", "they"}
    content_words = [w.lower() for w in words if w.lower() not in stopwords]
    return len(content_words) / len(words)


def detect_sentence_boundaries(text: str) -> list[int]:
    """Return character positions of sentence boundaries."""
    pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])|(?<=\n)\s*(?=\n)')
    positions = [0]
    for m in pattern.finditer(text):
        positions.append(m.start())
    positions.append(len(text))
    return positions


def detect_paragraph_breaks(text: str) -> list[int]:
    positions = [0]
    for m in re.finditer(r'\n\s*\n', text):
        positions.append(m.start())
    positions.append(len(text))
    return list(sorted(set(positions)))


def adjust_chunk_size(density: float, config: ChunkConfig) -> int:
    """High density = smaller chunks; low density = larger chunks."""
    if density > config.density_threshold:
        factor = 1.0 - (density - config.density_threshold) * 0.8
    else:
        factor = 1.0 + (config.density_threshold - density) * 0.5
    size = int(config.base_chunk_size * factor)
    return max(config.min_chunk_size, min(config.max_chunk_size, size))


def chunk_text(text: str, config: ChunkConfig) -> list[Chunk]:
    para_breaks = detect_paragraph_breaks(text)
    sentence_breaks = detect_sentence_boundaries(text)
    all_breaks = sorted(set(para_breaks + sentence_breaks))

    chunks: list[Chunk] = []
    chunk_id = 0
    current_start = 0

    while current_start < len(text):
        window = text[current_start:current_start + config.max_chunk_size * 2]
        density = compute_density(window[:config.base_chunk_size])
        target_size = adjust_chunk_size(density, config)

        target_end = current_start + target_size
        best_break = current_start + config.min_chunk_size
        boundary_type = "hard"

        for brk in all_breaks:
            if current_start + config.min_chunk_size <= brk <= target_end:
                best_break = brk
                boundary_type = "paragraph" if brk in para_breaks else "sentence"
            elif brk > target_end:
                break

        if best_break <= current_start:
            best_break = min(current_start + target_size, len(text))

        chunk_text_str = text[current_start:best_break].strip()
        if chunk_text_str:
            token_count = estimate_tokens(chunk_text_str)
            density_score = compute_density(chunk_text_str)
            chunks.append(Chunk(chunk_id=chunk_id, text=chunk_text_str, start_char=current_start, end_char=best_break, token_count=token_count, density_score=round(density_score, 3), boundary_type=boundary_type))
            chunk_id += 1

        overlap_start = max(current_start, best_break - config.overlap_tokens * 4)
        current_start = overlap_start if overlap_start > current_start else best_break

    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Dynamic semantic text chunker")
    parser.add_argument("--input", default=None, help="Input text file")
    parser.add_argument("--output", default="chunks.json")
    parser.add_argument("--base-size", type=int, default=512)
    parser.add_argument("--min-size", type=int, default=128)
    parser.add_argument("--max-size", type=int, default=1024)
    parser.add_argument("--overlap", type=int, default=32)
    args = parser.parse_args()

    config = ChunkConfig(base_chunk_size=args.base_size, min_chunk_size=args.min_size, max_chunk_size=args.max_size, overlap_tokens=args.overlap)

    if args.input:
        with open(args.input) as f:
            text = f.read()
    else:
        text = """Artificial intelligence agents are transforming how organizations handle complex workflows.
        
These agents can decompose large tasks into subtasks, assign work to specialized sub-agents, and coordinate
results into coherent outputs. The orchestration layer handles scheduling, priority, and error recovery.

Dense technical documentation often contains specialized terminology, acronyms, and domain concepts.
When chunking such content, smaller chunks preserve semantic coherence while allowing precise retrieval.

In contrast, narrative prose and general documentation benefit from larger chunks that preserve context.
The dynamic chunking strategy adapts chunk boundaries to the content structure automatically.

Paragraph breaks and sentence boundaries serve as natural split points. The algorithm prefers splitting
at these boundaries rather than cutting mid-sentence, which would destroy semantic coherence.

Content density scoring measures the ratio of meaningful content words to total words. High-density 
technical text warrants smaller chunks; low-density narrative text can tolerate larger chunks."""

    logger.info(f"Chunking text of {len(text)} characters")
    chunks = chunk_text(text, config)

    result = {"total_chunks": len(chunks), "config": {"base_chunk_size": config.base_chunk_size, "min_chunk_size": config.min_chunk_size, "max_chunk_size": config.max_chunk_size}, "chunks": [{"id": c.chunk_id, "tokens": c.token_count, "density": c.density_score, "boundary": c.boundary_type, "preview": c.text[:80] + "..."} for c in chunks]}

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Created {len(chunks)} chunks, written to {args.output}")
    for c in chunks:
        logger.info(f"  Chunk {c.chunk_id}: {c.token_count} tokens, density={c.density_score}, boundary={c.boundary_type}")

    print(json.dumps({"status": "ok", "chunks": len(chunks), "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
