#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Complexity classifier
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-23T18:09:28.459Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Classify prompts as simple/medium/complex using token count, regex patterns, keyword density."""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

COMPLEX_KEYWORDS = {"analyze", "compare", "evaluate", "synthesize", "critique", "design", "implement", "architect", "research", "comprehensive", "detailed", "in-depth", "multi-step", "reasoning", "prove", "derive", "algorithm", "optimize", "explain why", "how does", "what are the implications", "step by step"}

MEDIUM_KEYWORDS = {"summarize", "describe", "explain", "list", "what is", "how to", "define", "outline", "pros and cons", "difference between", "advantages", "disadvantages", "overview", "example"}

SIMPLE_KEYWORDS = {"translate", "fix", "format", "convert", "calculate", "spell", "grammar", "rewrite", "shorter", "longer", "complete", "fill in"}

CODE_INDICATORS = re.compile(r'```|def |class |function |import |require\(|<\w+>|SELECT |CREATE |ALTER ')
MATH_INDICATORS = re.compile(r'\b(?:integral|derivative|matrix|vector|probability|statistics|regression|calculus|differential|eigenvalue)\b', re.I)
MULTI_PART = re.compile(r'\b(?:also|additionally|furthermore|moreover|first|second|third|finally|step \d)\b', re.I)


@dataclass
class ClassificationResult:
    prompt: str
    classification: str
    confidence: float
    token_estimate: int
    complexity_score: float
    signals: list[str]
    recommended_model: str


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 4 // 3 + len(text) // 6)


def compute_keyword_density(text: str, keyword_set: set[str]) -> float:
    text_lower = text.lower()
    words = text_lower.split()
    if not words:
        return 0.0
    hits = sum(1 for phrase in keyword_set if phrase in text_lower)
    return hits / max(len(words) * 0.1, 1)


def classify_prompt(prompt: str) -> ClassificationResult:
    signals: list[str] = []
    score = 0.0

    tokens = estimate_tokens(prompt)
    if tokens > 500:
        score += 3.0
        signals.append(f"long_prompt:{tokens}_tokens")
    elif tokens > 200:
        score += 1.5
        signals.append(f"medium_prompt:{tokens}_tokens")
    elif tokens < 30:
        score -= 0.5
        signals.append(f"short_prompt:{tokens}_tokens")

    complex_density = compute_keyword_density(prompt, COMPLEX_KEYWORDS)
    if complex_density > 0.5:
        score += 3.0
        signals.append(f"complex_keywords:density={complex_density:.2f}")
    elif complex_density > 0.2:
        score += 1.5
        signals.append(f"moderate_complex_keywords")

    medium_density = compute_keyword_density(prompt, MEDIUM_KEYWORDS)
    if medium_density > 0.3:
        score += 1.0
        signals.append(f"medium_keywords")

    simple_density = compute_keyword_density(prompt, SIMPLE_KEYWORDS)
    if simple_density > 0.3:
        score -= 1.0
        signals.append(f"simple_keywords")

    if CODE_INDICATORS.search(prompt):
        score += 2.0
        signals.append("code_indicators")

    if MATH_INDICATORS.search(prompt):
        score += 2.5
        signals.append("math_indicators")

    multi_parts = len(MULTI_PART.findall(prompt))
    if multi_parts >= 3:
        score += 2.0
        signals.append(f"multi_part:{multi_parts}_connectors")
    elif multi_parts >= 1:
        score += 0.5

    question_marks = prompt.count("?")
    if question_marks >= 3:
        score += 1.0
        signals.append(f"multi_question:{question_marks}_questions")

    if score >= 4.0:
        classification = "complex"
        model = "gpt-4"
        confidence = min(0.95, 0.7 + score * 0.02)
    elif score >= 1.5:
        classification = "medium"
        model = "gpt-3.5-turbo"
        confidence = min(0.90, 0.65 + abs(score - 2.5) * 0.05)
    else:
        classification = "simple"
        model = "gpt-3.5-turbo"
        confidence = min(0.95, 0.75 - score * 0.05)

    return ClassificationResult(prompt=prompt[:100] + "..." if len(prompt) > 100 else prompt, classification=classification, confidence=round(confidence, 3), token_estimate=tokens, complexity_score=round(score, 2), signals=signals, recommended_model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prompt complexity classifier for LLM routing")
    parser.add_argument("--prompt", default=None, help="Single prompt to classify")
    parser.add_argument("--input", default=None, help="JSON file with list of prompts")
    parser.add_argument("--output", default="classifications.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.prompt:
        prompts = [args.prompt]
    elif args.input:
        with open(args.input) as f:
            prompts = json.load(f)
    else:
        prompts = [
            "What is 2+2?",
            "Translate 'hello' to French",
            "Summarize this article in 3 bullet points",
            "Explain how neural networks work",
            "Write a comprehensive analysis comparing transformer architectures, including attention mechanisms, positional encoding, and multi-head attention. Also discuss the computational complexity and compare BERT vs GPT approaches with examples.",
            "Fix this Python syntax error: print 'hello'",
            "Design a distributed system for real-time event processing at 1M events/second, considering fault tolerance, exactly-once delivery semantics, and horizontal scaling strategies.",
        ]

    results = []
    for prompt in prompts:
        result = classify_prompt(prompt)
        results.append({"prompt": result.prompt, "classification": result.classification, "confidence": result.confidence, "complexity_score": result.complexity_score, "token_estimate": result.token_estimate, "recommended_model": result.recommended_model, "signals": result.signals})
        logger.info(f"[{result.classification.upper()}] {result.prompt[:60]}... (score={result.complexity_score}, model={result.recommended_model})")

    summary = {"total": len(results), "simple": sum(1 for r in results if r["classification"] == "simple"), "medium": sum(1 for r in results if r["classification"] == "medium"), "complex": sum(1 for r in results if r["classification"] == "complex")}

    with open(args.output, "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print(json.dumps({"summary": summary, "output": args.output}, indent=2))


if __name__ == "__main__":
    main()
