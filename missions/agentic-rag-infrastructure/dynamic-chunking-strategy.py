#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Dynamic chunking strategy
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-31T18:39:32.420Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Dynamic chunking strategy (Sentence-window + parent-document retrieval)
Mission: Agentic RAG Infrastructure
Agent: @quinn
Date: 2025

Implements adaptive chunk size by document type with sentence-window and
parent-document retrieval for production-grade RAG systems.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class DocumentType(Enum):
    """Document type enumeration for adaptive chunking."""
    TECHNICAL = "technical"
    LEGAL = "legal"
    GENERAL = "general"
    CODE = "code"
    ACADEMIC = "academic"


@dataclass
class ChunkingConfig:
    """Configuration for adaptive chunking."""
    doc_type: DocumentType
    target_chunk_size: int
    sentence_window_size: int
    overlap_sentences: int
    min_chunk_size: int
    max_chunk_size: int

    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            "doc_type": self.doc_type.value,
            "target_chunk_size": self.target_chunk_size,
            "sentence_window_size": self.sentence_window_size,
            "overlap_sentences": self.overlap_sentences,
            "min_chunk_size": self.min_chunk_size,
            "max_chunk_size": self.max_chunk_size,
        }


@dataclass
class Chunk:
    """Represents a single chunk with metadata."""
    chunk_id: str
    content: str
    chunk_index: int
    doc_id: str
    start_char: int
    end_char: int
    sentence_indices: List[int]
    parent_chunk_id: Optional[str] = None
    is_parent: bool = False
    metadata: Dict = None

    def to_dict(self) -> Dict:
        """Convert chunk to dictionary."""
        if self.metadata is None:
            self.metadata = {}
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "doc_id": self.doc_id,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "sentence_indices": self.sentence_indices,
            "parent_chunk_id": self.parent_chunk_id,
            "is_parent": self.is_parent,
            "metadata": self.metadata,
        }


class SentenceTokenizer:
    """Tokenize text into sentences with handling for edge cases."""

    def __init__(self):
        """Initialize sentence patterns."""
        self.sentence_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\n+|(?<=\.)\s+(?=[A-Z])'
        )
        self.abbreviations = {
            "dr.", "mr.", "mrs.", "ms.", "prof.", "sr.", "jr.",
            "vs.", "ph.d.", "inc.", "ltd.", "co.", "corp.", "avg.",
            "approx.", "etc.", "e.g.", "i.e.", "vol.", "fig.", "cf.",
        }

    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into sentences."""
        sentences = []
        current_sentence = ""

        tokens = text.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            current_sentence += token + " "

            is_end_punct = token.rstrip(",;:").endswith((".", "!", "?"))
            is_abbreviation = token.lower() in self.abbreviations

            if is_end_punct and not is_abbreviation:
                if i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    if next_token[0].isupper() or next_token.startswith("("):
                        sentences.append(current_sentence.strip())
                        current_sentence = ""
            i += 1

        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return [s for s in sentences if s]


class AdaptiveChunker:
    """Dynamic chunking with sentence-window and parent-document retrieval."""

    def __init__(self, tokenizer: Optional[SentenceTokenizer] = None):
        """Initialize chunker with configuration."""
        self.tokenizer = tokenizer or SentenceTokenizer()
        self.chunking_configs = self._initialize_configs()
        self.chunks: List[Chunk] = []
        self.doc_sentences: Dict[str, List[str]] = {}

    def _initialize_configs(self) -> Dict[DocumentType, ChunkingConfig]:
        """Initialize adaptive chunking configs by document type."""
        return {
            DocumentType.TECHNICAL: ChunkingConfig(
                doc_type=DocumentType.TECHNICAL,
                target_chunk_size=512,
                sentence_window_size=3,
                overlap_sentences=1,
                min_chunk_size=256,
                max_chunk_size=1024,
            ),
            DocumentType.LEGAL: ChunkingConfig(
                doc_type=DocumentType.LEGAL,
                target_chunk_size=768,
                sentence_window_size=2,
                overlap_sentences=1,
                min_chunk_size=512,
                max_chunk_size=1536,
            ),
            DocumentType.GENERAL: ChunkingConfig(
                doc_type=DocumentType.GENERAL,
                target_chunk_size=512,
                sentence_window_size=3,
                overlap_sentences=1,
                min_chunk_size=256,
                max_chunk_size=1024,
            ),
            DocumentType.CODE: ChunkingConfig(
                doc_type=DocumentType.CODE,
                target_chunk_size=256,
                sentence_window_size=5,
                overlap_sentences=2,
                min_chunk_size=128,
                max_chunk_size=512,
            ),
            DocumentType.ACADEMIC: ChunkingConfig(
                doc_type=DocumentType.ACADEMIC,
                target_chunk_size=768,
                sentence_window_size=4,
                overlap_sentences=1,
                min_chunk_size=384,
                max_chunk_size=1536,
            ),
        }

    def detect_document_type(self, text: str) -> DocumentType:
        """Detect document type from content patterns."""
        text_lower = text.lower()
        
        code_indicators = ["def ", "class ", "import ", "function", "return ", "const ", "let ", "var "]
        if sum(1 for ind in code_indicators if ind in text_lower) >= 3:
            return DocumentType.CODE

        legal_indicators = ["whereas", "hereinafter", "party", "shall", "agreement", "liability"]
        if sum(1 for ind in legal_indicators if ind in text_lower) >= 3:
            return DocumentType.LEGAL

        academic_indicators = ["abstract", "methodology", "conclusion", "references", "hypothesis", "research"]
        if sum(1 for ind in academic_indicators if ind in text_lower) >= 3:
            return DocumentType.ACADEMIC

        tech_indicators = ["system", "algorithm", "implementation", "performance", "architecture", "database"]
        if sum(1 for ind in tech_indicators if ind in text_lower) >= 3:
            return DocumentType.TECHNICAL

        return DocumentType.GENERAL

    def chunk_document(
        self,
        text: str,
        doc_id: str,
        doc_type: Optional[DocumentType] = None,
    ) -> List[Chunk]:
        """
        Chunk document using sentence-window strategy with parent-document retrieval.
        
        Args:
            text: Document text to chunk
            doc_id: Document identifier
            doc_type: Type of document for adaptive sizing
            
        Returns:
            List of chunks with parent-document references
        """
        if doc_type is None:
            doc_type = self.detect_document_type(text)

        config = self.chunking_configs[doc_type]
        sentences = self.tokenizer.tokenize(text)
        self.doc_sentences[doc_id] = sentences

        if not sentences:
            return []

        doc_chunks = []
        parent_chunk_id = f"{doc_id}_parent_0"
        parent_start_idx = 0

        parent_sentences = []
        parent_start_char = 0
        char_offset = 0
        parent_chunk_count = 0

        for sent_idx, sentence in enumerate(sentences):
            parent_sentences.append(sentence)
            
            parent_text = " ".join(parent_sentences)
            if len(parent_text) >= config.target_chunk_size or sent_idx == len(sentences) - 1:
                parent_chunk_id = f"{doc_id}_parent_{parent_chunk_count}"
                
                parent_end_char = char_offset + len(parent_text)
                parent_chunk = Chunk(
                    chunk_id=parent_chunk_id,
                    content=parent_text,
                    chunk_index=parent_chunk_count,
                    doc_id=doc_id,
                    start_char=parent_start_char,
                    end_char=parent_end_char,
                    sentence_indices=list(range(parent_start_idx, sent_idx + 1)),
                    is_parent=True,
                    metadata={
                        "doc_type": doc_type.value,
                        "sentence_count": len(parent_sentences),
                    },
                )
                doc_chunks.append(parent_chunk)

                window_start = max(0, parent_start_idx - config.overlap_sentences)
                window_end = min(len(sentences), sent_idx + config.sentence_window_size + 1)
                window_sentences = sentences[window_start:window_end]
                window_text = " ".join(window_sentences)

                if config.min_chunk_size <= len(window_text) <= config.max_chunk_size:
                    window_start_char = sum(len(s) + 1 for s in sentences[:window_start])
                    window_end_char = window_start_char + len(window_text)

                    window_chunk = Chunk(
                        chunk_id=f"{doc_id}_window_{parent_chunk_count}",
                        content=window_text,
                        chunk_index=parent_chunk_count,
                        doc_id=doc_id,
                        start_char=window_start_char,
                        end_char=window_end_char,
                        sentence_indices=list(range(window_start, window_end)),
                        parent_chunk_id=parent_chunk_id,
                        is_parent=False,
                        metadata={
                            "doc_type": doc_type.value,
                            "window_size": config.sentence_window_size,
                            "sentence_count": len(window_sentences),
                        },
                    )
                    doc_chunks.append(window_chunk)

                parent_sentences = []
                parent_start_idx = sent_idx + 1
                parent_start_char = parent_end_char + 1
                parent_chunk_count += 1
                char_offset = parent_end_char + 1

        self.chunks.extend(doc_chunks)
        return doc_chunks

    def get_retrieval_context(
        self,
        chunk: Chunk,
        include_parent: bool = True,
    ) -> Dict:
        """
        Get full retrieval context for a chunk.
        
        Args:
            chunk: The chunk to get context for
            include_parent: Whether to include parent document
            
        Returns:
            Dictionary with chunk and context information
        """
        context = {
            "chunk": asdict(chunk),
            "parent_content": None,
            "surrounding_sentences": [],
        }

        if include_parent and chunk.parent_chunk_id:
            parent = next(
                (c for c in self.chunks if c.chunk_id == chunk.parent_chunk_id),
                None,
            )
            if parent:
                context["parent_content"] = parent.content

        doc_sentences = self.doc_sentences.get(chunk.doc_id, [])
        if doc_sentences and chunk.sentence_indices:
            max_idx = max(chunk.sentence_indices)
            if max_idx + 1 < len(doc_sentences):
                context["surrounding_sentences"] = doc_sentences[max_idx + 1 : max_idx + 3]

        return context

    def get_all_chunks(self) -> List[Chunk]:
        """Get all chunks."""
        return self.chunks

    def get_chunks_by_doc(self, doc_id: str) -> List[Chunk]:
        """Get all chunks for a specific document."""
        return [c for c in self.chunks if c.doc_id == doc_id]

    def get_parent_chunks(self, doc_id: str) -> List[Chunk]:
        """Get parent chunks for a document."""
        return [c for c in self.chunks if c.doc_id == doc_id and c.is_parent]

    def get_window_chunks(self, doc_id: str) -> List[Chunk]:
        """Get window chunks for a document."""
        return [c for c in self.chunks if c.doc_id == doc_id and not c.is_parent]

    def reset(self):
        """Reset chunker state."""
        self.chunks = []
        self.doc_sentences = {}


def main():
    """Main entry point with CLI."""
    parser = argparse.ArgumentParser(
        description="Dynamic chunking with sentence-window and parent-document retrieval"
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Input text file to chunk",
    )
    parser.add_argument(
        "--doc-type",
        type=str,
        choices=[dt.value for dt in DocumentType],
        default=None,
        help="Document type for adaptive chunking",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "text"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--include-context",
        action="store_true",
        help="Include full retrieval context",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data",
    )

    args = parser.parse_args()

    chunker = AdaptiveChunker()

    if args.demo:
        demo_data = [
            {
                "id": "doc_001",
                "type": None,
                "text": """
                The machine learning system implements a sophisticated algorithm for natural language processing.
                The system architecture consists of multiple layers including embedding, attention, and output.
                Performance metrics show significant improvement over baseline approaches.
                The implementation uses efficient data structures for optimal memory usage.
                We achieved 95% accuracy on the test dataset with minimal latency overhead.
                """,
            },
            {
                "id": "doc_legal_001",
                "type": DocumentType.LEGAL,
                "text": """
                This Agreement is entered into as of the date hereinafter referred to as the Effective Date.
                Whereas, the Party of the first part desires to engage the Party of the second part.
                Now, therefore, in consideration of the mutual covenants and agreements hereinafter contained,
                the parties agree as follows: The Party shall perform services as requested.
                Liability shall be limited to direct damages only.
                Neither party shall be liable for consequential or indirect damages arising from this agreement.
                """,
            },
            {
                "id": "doc_code_001",
                "type": DocumentType.CODE,
                "text": """
                def process_data(input_list):
                    result = []
                    for item in input_list:
                        if isinstance(item, dict):
                            processed = transform(item)
                            result.append(processed)
                    return result
                
                class DataProcessor:
                    def __init__(self, config):
                        self.config = config
                        self.cache = {}
                    
                    def execute(self, data):
                        return process_data(data)
                """,
            },
        ]

        print("=" * 80)
        print("DYNAMIC CHUNKING DEMO - Sentence-Window + Parent-Document Retrieval")
        print("=" * 80)

        for doc_data in demo_data:
            doc_id = doc_data["id"]
            doc_type = doc_data.get("type")
            text = doc_data["text"].strip()

            print(f"\nProcessing Document: {doc_id}")
            print(f"Original text length: {len(text)} characters")

            chunks = chunker.chunk_document(text, doc_id, doc_type)

            detected_type = chunker.detect_document_type(text)
            print(f"Detected document type: {detected_type.value}")
            print(f"Total chunks created: {len(chunks)}")

            parent_chunks = [c for c in chunks if c.is_parent]
            window_chunks = [c for c in chunks if not c.is_parent]

            print(f"  - Parent chunks: {len(parent_chunks)}")
            print(f"  - Window chunks: {len(window_chunks)}")

            print("\nChunks:")
            for chunk in chunks:
                chunk_type = "PARENT" if chunk.is_parent else "WINDOW"
                print(f"\n  [{chunk_type}] {chunk.chunk_id}")
                print(f"  Content preview: {chunk.content[:80]}...")
                print(f"  Char range: {chunk.start_char}-{chunk.end_char}")
                print(f"  Sentence indices: {chunk.sentence_indices}")
                if chunk.parent_chunk_id:
                    print(f"  Parent: {chunk.parent_chunk_id}")

        print("\n" + "=" * 80)
        print("RETRIEVAL CONTEXT EXAMPLE")
        print("=" * 80)

        all_chunks = chunker.get_all_chunks()
        if all_chunks:
            sample_chunk = next((c for c in all_chunks if not c.is_parent), all_chunks[0])
            context = chunker.get_retrieval_context(sample_chunk, include_parent=True)

            print(f"\nSample chunk: {sample_chunk.chunk_id}")
            print(f"Content: {sample_chunk.content[:100]}...")
            if context["parent_content"]:
                print(f"Parent content: {context['parent_content'][:100]}...")
            if context["surrounding_sentences"]:
                print(f"Surrounding sentences: {context['surrounding_sentences']}")

        print("\n" + "=" * 80)
        print("JSON OUTPUT SAMPLE")
        print("=" * 80)

        if all_chunks:
            sample_chunk = all_chunks[0]
            output = {
                "chunk": sample_chunk.to_dict(),
                "metadata": {
                    "total_chunks": len(all_chunks),
                    "doc_id": sample_chunk.doc_id,
                }
            }
            print(json.dumps(output, indent=2))

    elif args.input_file:
        try:
            with open(args.input_file, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: File '{args.input_file}' not found", file=sys.stderr)
            sys.exit(1)

        doc_type = None
        if args.doc_type:
            doc_type = DocumentType(args.doc_type)

        chunks = chunker.chunk_document(text, "input_doc", doc_type)

        if args.output_format == "json":
            output = {
                "document_id": "input_doc",
                "doc_type": (doc_type or chunker.detect_document_type(text)).value,
                "chunks": [c.to_dict() for c in chunks],
                "statistics": {
                    "total_chunks": len(chunks),
                    "parent_chunks": len([c for c in chunks if c.is_parent]),
                    "window_chunks": len([c for c in chunks if not c.is_parent]),
                    "original_text_length": len(text),
                },
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Document ID: input_doc")
            print(f"Document type: {(doc_type or chunker.detect_document_type(text)).value}")
            print(f"Total chunks: {len(chunks)}\n")

            for chunk in chunks:
                chunk_type = "PARENT" if chunk.is_parent else "WINDOW"
                print(f"[{chunk_type}] {chunk.chunk_id}")
                print(f"Content: {chunk.content}")
                print(f"Char range: {chunk.start_char}-{chunk.end_char}")
                print("-" * 40)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()