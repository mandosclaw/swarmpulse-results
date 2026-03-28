#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Complexity classifier
# Mission: LLM Inference Cost Optimizer
# Agent:   @quinn
# Date:    2026-03-28T22:00:28.250Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Complexity classifier for LLM inference cost optimization
Mission: LLM Inference Cost Optimizer
Agent: @quinn
Date: 2024
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple, List, Dict, Any
import random
import string


@dataclass
class ComplexityScore:
    """Complexity analysis result."""
    prompt: str
    score: float
    category: str
    reasoning: Dict[str, Any]
    recommendation: str


class LexicalAnalyzer:
    """Analyzes lexical properties of text."""
    
    def __init__(self):
        self.technical_keywords = {
            'algorithm', 'regression', 'neural', 'tensor', 'gradient',
            'optimization', 'convergence', 'probability', 'distribution',
            'matrix', 'eigenvalue', 'derivative', 'integral', 'topology',
            'cryptography', 'blockchain', 'quantum', 'entropy', 'hash',
            'microservice', 'kubernetes', 'docker', 'pipeline', 'etl',
            'api', 'database', 'schema', 'normalization', 'denormalization',
            'byzantine', 'consensus', 'protocol', 'handshake', 'ssl',
            'regression', 'classification', 'clustering', 'anomaly',
            'reinforcement', 'supervised', 'unsupervised', 'transfer',
            'framework', 'middleware', 'abstraction', 'inheritance',
            'polymorphism', 'encapsulation', 'refactoring', 'lint'
        }
        
        self.domain_patterns = {
            'medical': ['diagnosis', 'treatment', 'symptom', 'disease', 'clinical', 'patient', 'therapy'],
            'legal': ['contract', 'litigation', 'statute', 'jurisdiction', 'precedent', 'compliance', 'regulation'],
            'financial': ['portfolio', 'derivative', 'hedge', 'arbitrage', 'valuation', 'yield', 'liquidity'],
            'scientific': ['hypothesis', 'experiment', 'methodology', 'peer-review', 'statistical', 'control'],
            'code': ['function', 'class', 'loop', 'variable', 'method', 'return', 'import', 'module']
        }
    
    def count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        return len(re.split(r'[.!?]+', text.strip())) - 1
    
    def count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())
    
    def average_word_length(self, text: str) -> float:
        """Calculate average word length."""
        words = text.split()
        if not words:
            return 0.0
        return sum(len(w) for w in words) / len(words)
    
    def detect_technical_terms(self, text: str) -> float:
        """Score based on technical term density."""
        text_lower = text.lower()
        words = set(text_lower.split())
        matches = len(words & self.technical_keywords)
        total = len(words)
        return matches / max(total, 1)
    
    def detect_domain_specificity(self, text: str) -> Dict[str, float]:
        """Detect domain-specific terminology."""
        text_lower = text.lower()
        scores = {}
        for domain, terms in self.domain_patterns.items():
            matches = sum(1 for term in terms if term in text_lower)
            scores[domain] = matches / len(terms)
        return scores
    
    def calculate_lexical_diversity(self, text: str) -> float:
        """Calculate type-token ratio (vocabulary diversity)."""
        words = text.lower().split()
        if not words:
            return 0.0
        unique_words = len(set(words))
        return unique_words / len(words)
    
    def count_special_tokens(self, text: str) -> Dict[str, int]:
        """Count special tokens and structures."""
        return {
            'brackets': len(re.findall(r'[\[\]{}<>()]', text)),
            'numbers': len(re.findall(r'\d+', text)),
            'urls': len(re.findall(r'https?://\S+', text)),
            'emails': len(re.findall(r'\S+@\S+', text)),
            'code_blocks': len(re.findall(r'```|`[^`]*`', text)),
            'math_notation': len(re.findall(r'[∑∏∫√∞±≤≥=≠]|\\[a-z]+', text)),
        }


class StructuralAnalyzer:
    """Analyzes structural complexity of prompts."""
    
    def detect_nested_structures(self, text: str) -> int:
        """Detect nesting depth in brackets/parentheses."""
        max_depth = 0
        current_depth = 0
        for char in text:
            if char in '([{':
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char in ')]}':
                current_depth = max(0, current_depth - 1)
        return max_depth
    
    def count_logical_operators(self, text: str) -> int:
        """Count logical operators and connectors."""
        operators = ['and', 'or', 'not', 'if', 'then', 'else', 'elif', 'unless', 'while', 'for']
        text_lower = text.lower()
        count = sum(len(re.findall(r'\b' + op + r'\b', text_lower)) for op in operators)
        return count
    
    def count_questions(self, text: str) -> int:
        """Count question marks and interrogative structures."""
        return len(re.findall(r'\?', text))
    
    def count_instructions(self, text: str) -> int:
        """Count imperative/instruction patterns."""
        imperatives = ['calculate', 'find', 'solve', 'analyze', 'explain', 'list', 'describe',
                      'compare', 'contrast', 'summarize', 'evaluate', 'predict', 'generate']
        text_lower = text.lower()
        count = sum(len(re.findall(r'\b' + imp + r'\b', text_lower)) for imp in imperatives)
        return count
    
    def count_constraints(self, text: str) -> int:
        """Count constraint patterns."""
        constraints = ['must', 'should', 'cannot', 'only', 'exactly', 'at least', 'no more than',
                      'within', 'between', 'require', 'constraint', 'limit', 'maximum', 'minimum']
        text_lower = text.lower()
        count = sum(len(re.findall(r'\b' + c + r'\b', text_lower)) for c in constraints)
        return count


class ComplexityClassifier:
    """BERT-tiny-inspired lightweight complexity classifier."""
    
    def __init__(self, model_weights: Dict[str, float] = None):
        """Initialize with optional custom weights."""
        self.lexical = LexicalAnalyzer()
        self.structural = StructuralAnalyzer()
        
        self.weights = model_weights or {
            'word_count': 0.08,
            'sentence_count': 0.07,
            'avg_word_length': 0.06,
            'technical_terms': 0.15,
            'domain_specificity': 0.12,
            'lexical_diversity': 0.08,
            'nested_structures': 0.10,
            'logical_operators':