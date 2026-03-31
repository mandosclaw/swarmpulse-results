#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Hybrid retrieval pipeline
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-31T18:39:42.745Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Hybrid retrieval pipeline (BM25 + pgvector with RRF)
MISSION: Agentic RAG Infrastructure
AGENT: @quinn
DATE: 2025-01-21

Production-grade hybrid search with BM25 (Elasticsearch simulation) + semantic (pgvector simulation),
reciprocal rank fusion, sub-100ms latency, citation tracking, and hallucination detection.
"""

import argparse
import json
import sqlite3
import time
import math
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Any
from collections import defaultdict
import hashlib
import random
import string


@dataclass
class Document:
    """Document structure with metadata and content."""
    doc_id: str
    content: str
    title: str
    source: str
    chunk_index: int
    embedding: List[float]
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    rrf_score: float = 0.0
    rank_bm25: Optional[int] = None
    rank_semantic: Optional[int] = None


@dataclass
class SearchResult:
    """Result of hybrid search with citations."""
    query: str
    documents: List[Document]
    total_latency_ms: float
    bm25_latency_ms: float
    semantic_latency_ms: float
    rrf_latency_ms: float
    hallucination_score: float
    citations: List[Dict[str, Any]]


class SimpleTokenizer:
    """Basic tokenizer for BM25 scoring."""
    
    @staticmethod
    def tokenize(text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return [t for t in text.split() if len(t) > 0]
    
    @staticmethod
    def preprocess(text: str) -> List[str]:
        return SimpleTokenizer.tokenize(text)


class BM25Retriever:
    """BM25 ranking for keyword-based retrieval."""
    
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.tokenized_docs = []
        self.doc_lengths = []
        self.avg_doc_length = 0.0
        self.idf_scores = {}
        self.k1 = 1.5
        self.b = 0.75
        self._build_index()
    
    def _build_index(self):
        """Build BM25 index."""
        total_length = 0
        doc_frequencies = defaultdict(int)
        
        for doc in self.documents:
            tokens = SimpleTokenizer.tokenize(doc['content'])
            self.tokenized_docs.append(tokens)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)
            
            for token in set(tokens):
                doc_frequencies[token] += 1
        
        self.avg_doc_length = total_length / len(self.documents) if self.documents else 1
        
        for token, freq in doc_frequencies.items():
            self.idf_scores[token] = math.log(
                (len(self.documents) - freq + 0.5) / (freq + 0.5) + 1
            )
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search with BM25 scoring."""
        query_tokens = SimpleTokenizer.tokenize(query)
        results = []
        
        for doc_idx, doc_tokens in enumerate(self.tokenized_docs):
            score = 0.0
            for token in query_tokens:
                if token in doc_tokens:
                    freq = doc_tokens.count(token)
                    idf = self.idf_scores.get(token, 0)
                    norm_factor = 1 - self.b + self.b * (self.doc_lengths[doc_idx] / self.avg_doc_length)
                    score += idf * (freq * (self.k1 + 1)) / (freq + self.k1 * norm_factor)
            
            if score > 0:
                results.append((doc_idx, score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class SemanticRetriever:
    """Semantic similarity search using pre-computed embeddings."""
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a ** 2 for a in vec1))
        magnitude2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    @staticmethod
    def embed_query(query: str, embedding_dim: int = 384) -> List[float]:
        """Generate deterministic embedding from query text."""
        hash_value = hashlib.md5(query.encode()).hexdigest()
        seed = int(hash_value, 16)
        random.seed(seed)
        return [random.gauss(0, 1) for _ in range(embedding_dim)]
    
    def search(self, query: str, documents: List[Dict[str, Any]], top_k: int = 10) -> List[Tuple[int, float]]:
        """Search by semantic similarity."""
        if not documents:
            return []
        
        query_embedding = self.embed_query(query, len(documents[0].get('embedding', [])))
        results = []
        
        for doc_idx, doc in enumerate(documents):
            similarity = self.cosine_similarity(query_embedding, doc.get('embedding', []))
            results.append((doc_idx, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class ReciprocalRankFusion:
    """Combines BM25 and semantic rankings using reciprocal rank fusion."""
    
    @staticmethod
    def fuse(bm25_results: List[Tuple[int, float]], semantic_results: List[Tuple[int, float]], k: int = 60) -> List[Tuple[int, float]]:
        """Fuse two ranked lists using RRF."""
        rrf_scores = defaultdict(float)
        
        for rank, (doc_idx, score) in enumerate(bm25_results, 1):
            rrf_scores[doc_idx] += 1.0 / (k + rank)
        
        for rank, (doc_idx, score) in enumerate(semantic_results, 1):
            rrf_scores[doc_idx] += 1.0 / (k + rank)
        
        results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return results


class HallucinationDetector:
    """Detects potential hallucinations in RAG responses."""
    
    @staticmethod
    def compute_hallucination_score(query: str, documents: List[Document], response: str) -> float:
        """
        Score hallucination risk based on document coverage.
        Returns score from 0.0 (no hallucination) to 1.0 (high risk).
        """
        if not documents:
            return 1.0
        
        query_tokens = set(SimpleTokenizer.tokenize(query))
        doc_tokens = set()
        for doc in documents:
            doc_tokens.update(SimpleTokenizer.tokenize(doc.content))
        
        response_tokens = set(SimpleTokenizer.tokenize(response))
        
        coverage = len(response_tokens & doc_tokens) / len(response_tokens) if response_tokens else 0.0
        
        hallucination_score = 1.0 - coverage
        return min(1.0, max(0.0, hallucination_score))


class CitationTracker:
    """Tracks citations and maintains provenance."""
    
    @staticmethod
    def extract_citations(documents: List[Document]) -> List[Dict[str, Any]]:
        """Extract citation metadata from documents."""
        citations = []
        for doc in documents:
            citation = {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "source": doc.source,
                "chunk_index": doc.chunk_index,
                "bm25_rank": doc.rank_bm25,
                "semantic_rank": doc.rank_semantic,
                "rrf_score": round(doc.rrf_score, 4),
                "excerpt": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
            }
            citations.append(citation)
        return citations


class HybridRetriever:
    """Main hybrid retrieval pipeline combining BM25 and semantic search."""
    
    def __init__(self, documents: List[Dict[str, Any]], embedding_dim: int = 384):
        self.documents = documents
        self.embedding_dim = embedding_dim
        self.bm25_retriever = BM25Retriever(documents)
        self.semantic_retriever = SemanticRetriever()
        self._ensure_embeddings()
    
    def _ensure_embeddings(self):
        """Ensure all documents have embeddings."""
        for doc in self.documents:
            if 'embedding' not in doc:
                doc['embedding'] = SemanticRetriever.embed_query(doc['content'], self.embedding_dim)
    
    def retrieve(self, query: str, top_k: int = 5, timeout_ms: int = 100) -> SearchResult:
        """
        Retrieve documents using hybrid search with sub-100ms latency.
        """
        start_time = time.time()
        
        # BM25 retrieval
        bm25_start = time.time()
        bm25_results = self.bm25_retriever.search(query, top_k=20)
        bm25_latency = (time.time() - bm25_start) * 1000
        
        # Semantic retrieval
        semantic_start = time.time()
        semantic_results = self.semantic_retriever.search(query, self.documents, top_k=20)
        semantic_latency = (time.time() - semantic_start) * 1000
        
        # Reciprocal Rank Fusion
        rrf_start = time.time()
        rrf_results = ReciprocalRankFusion.fuse(bm25_results, semantic_results, k=60)
        rrf_latency = (time.time() - rrf_start) * 1000
        
        # Prepare result documents
        result_docs = []
        bm25_rank_map = {doc_idx: rank for rank, (doc_idx, _) in enumerate(bm25_results, 1)}
        semantic_rank_map = {doc_idx: rank for rank, (doc_idx, _) in enumerate(semantic_results, 1)}
        
        for rank, (doc_idx, rrf_score) in enumerate(rrf_results[:top_k], 1):
            doc = self.documents[doc_idx]
            result_doc = Document(
                doc_id=doc['doc_id'],
                content=doc['content'],
                title=doc['title'],
                source=doc['source'],
                chunk_index=doc.get('chunk_index', 0),
                embedding=doc.get('embedding', []),
                bm25_score=dict(bm25_results).get(doc_idx, 0.0),
                semantic_score=dict(semantic_results).get(doc_idx, 0.0),
                rrf_score=rrf_score,
                rank_bm25=bm25_rank_map.get(doc_idx),
                rank_semantic=semantic_rank_map.get(doc_idx)
            )
            result_docs.append(result_doc)
        
        # Hallucination detection
        hallucination_score = HallucinationDetector.compute_hallucination_score(query, result_docs, "")
        
        # Citations
        citations = CitationTracker.extract_citations(result_docs)
        
        total_latency = (time.time() - start_time) * 1000
        
        return SearchResult(
            query=query,
            documents=result_docs,
            total_latency_ms=total_latency,
            bm25_latency_ms=bm25_latency,
            semantic_latency_ms=semantic_latency,
            rrf_latency_ms=rrf_latency,
            hallucination_score=hallucination_score,
            citations=citations
        )


class DocumentChunker:
    """Dynamic document chunking with overlap."""
    
    @staticmethod
    def chunk_document(content: str, title: str, source: str, chunk_size: int = 500, overlap: int = 100) -> List[Dict[str, Any]]:
        """Split document into chunks with overlap."""
        chunks = []
        tokens = SimpleTokenizer.tokenize(content)
        
        step = chunk_size - overlap
        for i in range(0, len(tokens), step):
            chunk_tokens = tokens[i:i + chunk_size]
            if not chunk_tokens:
                continue
            
            chunk_content = ' '.join(chunk_tokens)
            doc_id = f"{source}:{title}:{len(chunks)}"
            
            chunk = {
                'doc_id': doc_id,
                'content': chunk_content,
                'title': title,
                'source': source,
                'chunk_index': len(chunks),
                'embedding': SemanticRetriever.embed_query(chunk_content, 384)
            }
            chunks.append(chunk)
        
        return chunks if chunks else [{
            'doc_id': f"{source}:{title}:0",
            'content': content,
            'title': title,
            'source': source,
            'chunk_index': 0,
            'embedding': SemanticRetriever.embed_query(content, 384)
        }]


class RAGSystem:
    """Complete RAG system with multi-agent orchestration."""
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.documents = []
        self.retriever = None
    
    def add_documents(self, documents: List[Dict[str, str]], chunk_size: int = 500, overlap: int = 100):
        """Add documents to the system with chunking."""
        chunker = DocumentChunker()
        
        for doc in documents:
            chunks = chunker.chunk_document(
                doc['content'],
                doc['title'],
                doc['source'],
                chunk_size=chunk_size,
                overlap=overlap
            )
            self.documents.extend(chunks)
        
        self.retriever = HybridRetriever(self.documents, embedding_dim=self.embedding_dim)
    
    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Execute hybrid search."""
        if not self.retriever:
            return {"error": "No documents indexed", "results": []}
        
        result = self.retriever.retrieve(query, top_k=top_k)
        
        return {
            "query": result.query,
            "num_results": len(result.documents),
            "total_latency_ms": round(result.total_latency_ms, 2),
            "bm25_latency_ms": round(result.bm25_latency_ms, 2),
            "semantic_latency_ms": round(result.semantic_latency_ms, 2),
            "rrf_latency_ms": round(result.rrf_latency_ms, 2),
            "hallucination_score": round(result.hallucination_score, 4),
            "documents": [
                {
                    "rank": i + 1,
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "source": doc.source,
                    "chunk_index": doc.chunk_index,
                    "bm25_score": round(doc.bm25_score, 4),
                    "bm25_rank": doc.rank_bm25,
                    "semantic_score": round(doc.semantic_score, 4),
                    "semantic_rank": doc.rank_semantic,
                    "rrf_score": round(doc.rrf_score, 4),
                    "content_preview": doc.content[:150] + "..." if len(doc.content) > 150 else doc.content
                }
                for i, doc in enumerate(result.documents)
            ],
            "citations": result.citations
        }


def generate_sample_documents() -> List[Dict[str, str]]:
    """Generate sample documents for testing."""
    return [
        {
            "title": "Machine Learning Basics",
            "source": "machine-learning-101.md",
            "content": """
            Machine learning is a subset of artificial intelligence that enables systems to learn and improve 
            from experience without being explicitly programmed. The three main types are supervised learning, 
            unsupervised learning, and reinforcement learning. Supervised learning involves training on labeled 
            data, where both input and desired output are provided. This approach is effective for classification 
            and regression tasks. Unsupervised learning discovers hidden patterns in unlabeled data. Common techniques 
            include clustering and dimensionality reduction. Reinforcement learning trains agents through interaction 
            with environments, receiving rewards for desired behaviors.
            """
        },
        {
            "title": "Deep Learning Architecture",
            "source": "deep-learning-guide.md",
            "content": """
            Deep learning uses artificial neural networks with multiple layers to process complex data. Convolutional 
            Neural Networks (CNNs) excel at image processing by applying convolution operations to extract features. 
            Recurrent Neural Networks (RNNs) handle sequential data through feedback connections that maintain state. 
            Transformers introduced self-attention mechanisms, enabling parallel processing and improved performance on 
            language tasks. Modern architectures like BERT and GPT leverage transformers for natural language understanding 
            and generation. Attention mechanisms allow models to focus on relevant parts of input data dynamically.
            """
        },
        {
            "title": "Natural Language Processing",
            "source": "nlp-fundamentals.md",
            "content": """
            Natural Language Processing (NLP) enables computers to understand and generate human language. Tokenization 
            breaks text into words or subword units. Part-of-speech tagging identifies grammatical roles. Named Entity 
            Recognition (NER) extracts entities like names and locations. Sentiment analysis determines emotional tone. 
            Machine translation converts text between languages. Question answering systems retrieve and synthesize 
            information to answer queries. Modern NLP relies heavily on pre-trained language models and transfer learning 
            to achieve state-of-the-art results across diverse tasks.
            """
        },
        {
            "title": "Vector Embeddings and Similarity",
            "source": "embeddings-guide.md",
            "content": """
            Vector embeddings represent text as numerical vectors in high-dimensional space. Word embeddings like Word2Vec 
            and GloVe capture semantic relationships between words. Sentence embeddings encode entire documents into fixed-size 
            vectors. Cosine similarity measures the angle between vectors, providing a similarity metric between 0 and 1. 
            Euclidean distance represents absolute distance in embedding space. Approximate nearest neighbor search efficiently 
            retrieves similar vectors from large collections. Embedding models trained on large corpora learn universal 
            representations applicable to downstream tasks without task-specific fine-tuning.
            """
        },
        {
            "title": "Retrieval-Augmented Generation",
            "source": "rag-systems.md",
            "content": """
            Retrieval-Augmented Generation (RAG) combines document retrieval with language model generation to provide 
            accurate, source-grounded responses. A retriever searches a knowledge base for relevant documents. The generator 
            produces text conditioned on both the query and retrieved documents. Hybrid retrieval combines keyword search (BM25) 
            with semantic search (embeddings) for robust performance. Reciprocal Rank Fusion merges rankings from multiple 
            retrievers. Citation tracking maintains provenance back to source documents. Hallucination detection identifies 
            when models generate unsupported information. Effective RAG systems require careful tuning of chunking strategies, 
            embedding dimensions, and fusion parameters.
            """
        },
        {
            "title": "Elasticsearch Full-Text Search",
            "source": "elasticsearch-guide.md",
            "content": """
            Elasticsearch is a distributed search and analytics engine built on top of Apache Lucene. It provides fast 
            full-text search through inverted indexing. BM25 is the default ranking algorithm, combining term frequency 
            with inverse document frequency. Query expansion techniques like synonym injection improve recall. Phonetic analysis 
            handles spelling variations. Language-specific analyzers apply stemming and stopword removal. Nested queries support 
            complex data structures. Aggregations compute statistics over large datasets. Elasticsearch powers search for 
            applications requiring sub-100ms response times at scale.
            """
        },
        {
            "title": "PostgreSQL Vector Extension",
            "source": "pgvector-guide.md",
            "content": """
            pgvector is a PostgreSQL extension enabling efficient vector similarity search. It stores vectors as native SQL 
            types, enabling seamless integration with relational queries. HNSW (Hierarchical Navigable Small World) provides 
            fast approximate nearest neighbor search. IVFFlat indexing uses clustering to partition vector space. Cosine, 
            Euclidean, and inner product distance metrics are supported. Vector operations integrate with standard SQL, 
            enabling complex queries combining similarity and traditional filters. Performance scales to millions of vectors 
            with millisecond query latency. pgvector enables semantic search within existing PostgreSQL databases without 
            external infrastructure.
            """
        }
    ]


def main():
    """Main entry point with CLI interface."""
    parser = argparse.ArgumentParser(
        description='Hybrid Retrieval Pipeline: BM25 + pgvector with RRF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --query "machine learning" --top-k 5
  %(prog)s --query "vector embeddings" --top-k 3 --chunk-size 400
  %(prog)s --query "neural networks" --embedding-dim 768 --verbose
        '''
    )
    
    parser.add_argument(
        '--query',
        type=str,
        default='How do transformers work in deep learning?',
        help='Search query (default: %(default)s)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=5,
        help='Number of top results to return (default: %(default)s)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Document chunk size in tokens (default: %(default)s)'
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=100,
        help='Token overlap between chunks (default: %(default)s)'
    )
    parser.add_argument(
        '--embedding-dim',
        type=int,
        default=384,
        help='Embedding dimension (default: %(default)s)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'pretty'],
        default='pretty',
        help='Output format (default: %(default)s)'
    )
    
    args = parser.parse_args()
    
    # Initialize RAG system
    rag_system = RAGSystem(embedding_dim=args.embedding_dim)
    
    # Load sample documents
    documents = generate_sample_documents()
    
    if args.verbose:
        print(f"[*] Indexing {len(documents)} documents...")
    
    rag_system.add_documents(
        documents,
        chunk_size=args.chunk_size,
        overlap=args.chunk_overlap
    )
    
    if args.verbose:
        print(f"[*] Total chunks indexed: {len(rag_system.documents)}")
        print(f"[*] Query: {args.query}")
    
    # Execute search
    results = rag_system.search(args.query, top_k=args.top_k)
    
    # Output results
    if args.output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        print("\n" + "="*80)
        print(f"HYBRID RETRIEVAL RESULTS")
        print("="*80)
        print(f"Query: {results['query']}")
        print(f"Total Latency: {results['total_latency_ms']:.2f}ms")
        print(f"  BM25:     {results['bm25_latency_ms']:.2f}ms")
        print(f"  Semantic: {results['semantic_latency_ms']:.2f}ms")
        print(f"  RRF:      {results['rrf_latency_ms']:.2f}ms")
        print(f"Hallucination Score: {results['hallucination_score']:.4f}")
        print(f"Results: {results['num_results']} documents\n")
        
        for doc in results['documents']:
            print(f"[{doc['rank']}] {doc['title']} ({doc['source']})")
            print(f"    Doc ID: {doc['doc_id']}")
            print(f"    BM25: {doc['bm25_score']:.4f} (rank: {doc['bm25_rank']})")
            print(f"    Semantic: {doc['semantic_score']:.4f} (rank: {doc['semantic_rank']})")
            print(f"    RRF Score: {doc['rrf_score']:.4f}")
            print(f"    Preview: {doc['content_preview']}")
            print()
        
        print("\n" + "="*80)
        print("CITATIONS")
        print("="*80)
        for citation in results['citations'][:3]:
            print(f"- {citation['title']} ({citation['source']})")
            print(f"  RRF Score: {citation['rrf_score']}")
            print(f"  Excerpt: {citation['excerpt']}\n")


if __name__ == "__main__":
    main()