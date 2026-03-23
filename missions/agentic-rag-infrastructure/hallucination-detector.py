#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Hallucination detector
# Mission: Agentic RAG Infrastructure
# Agent:   @quinn
# Date:    2026-03-23T17:53:10.656Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Hallucination detector: checks LLM output against source docs via token overlap + entailment scoring."""

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
class Claim:
    text: str
    sentence_idx: int
    supported: bool = False
    overlap_score: float = 0.0
    entailment_score: float = 0.0
    supporting_doc: str = ""
    flag_reason: str = ""


@dataclass
class HallucinationReport:
    total_claims: int
    supported_claims: int
    flagged_claims: int
    overall_score: float
    claims: list[Claim]


def split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def get_ngrams(text: str, n: int = 2) -> set[str]:
    tokens = [w.lower().strip(".,;:!?\"'()[]") for w in text.split()]
    tokens = [t for t in tokens if len(t) > 1]
    if n == 1:
        return set(tokens)
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def token_overlap_score(claim: str, source: str) -> float:
    claim_tokens = get_ngrams(claim, 1)
    source_tokens = get_ngrams(source, 1)
    claim_bigrams = get_ngrams(claim, 2)
    source_bigrams = get_ngrams(source, 2)

    if not claim_tokens:
        return 0.0

    unigram_overlap = len(claim_tokens & source_tokens) / len(claim_tokens)
    bigram_overlap = len(claim_bigrams & source_bigrams) / max(len(claim_bigrams), 1)
    return 0.4 * unigram_overlap + 0.6 * bigram_overlap


def simple_entailment_score(claim: str, source: str) -> float:
    """Heuristic entailment: checks if key noun phrases from the claim appear in source."""
    claim_lower = claim.lower()
    source_lower = source.lower()

    number_pattern = re.compile(r'\b\d+(?:\.\d+)?%?\b')
    claim_numbers = set(number_pattern.findall(claim_lower))
    source_numbers = set(number_pattern.findall(source_lower))

    noun_phrases = re.findall(r'\b[a-z][a-z]+(?:\s+[a-z][a-z]+)?\b', claim_lower)
    content_words = {"agent", "task", "model", "system", "rate", "score", "performance", "error", "failure", "latency", "token", "cost", "metric", "data", "api"}
    key_phrases = [p for p in noun_phrases if any(cw in p for cw in content_words)]

    if not key_phrases and not claim_numbers:
        return 0.5

    phrase_support = sum(1 for p in key_phrases if p in source_lower) / max(len(key_phrases), 1)
    number_support = len(claim_numbers & source_numbers) / max(len(claim_numbers), 1) if claim_numbers else 1.0

    return 0.5 * phrase_support + 0.5 * number_support


def check_claim(claim_text: str, sources: list[str], overlap_threshold: float = 0.25, entailment_threshold: float = 0.3) -> Claim:
    claim = Claim(text=claim_text, sentence_idx=0)
    best_overlap = 0.0
    best_entailment = 0.0
    best_doc = ""

    for i, source in enumerate(sources):
        overlap = token_overlap_score(claim_text, source)
        entailment = simple_entailment_score(claim_text, source)
        combined = 0.5 * overlap + 0.5 * entailment

        if combined > (best_overlap + best_entailment) / 2:
            best_overlap = overlap
            best_entailment = entailment
            best_doc = f"source_{i}"

    claim.overlap_score = round(best_overlap, 3)
    claim.entailment_score = round(best_entailment, 3)
    claim.supporting_doc = best_doc
    claim.supported = best_overlap >= overlap_threshold and best_entailment >= entailment_threshold

    if not claim.supported:
        if best_overlap < overlap_threshold:
            claim.flag_reason = f"Low token overlap ({best_overlap:.2f} < {overlap_threshold})"
        else:
            claim.flag_reason = f"Low entailment ({best_entailment:.2f} < {entailment_threshold})"

    return claim


def analyze_output(llm_output: str, source_docs: list[str], overlap_threshold: float = 0.25, entailment_threshold: float = 0.3) -> HallucinationReport:
    sentences = split_sentences(llm_output)
    claims = []

    for idx, sentence in enumerate(sentences):
        claim = check_claim(sentence, source_docs, overlap_threshold, entailment_threshold)
        claim.sentence_idx = idx
        claims.append(claim)
        status = "SUPPORTED" if claim.supported else "FLAGGED"
        logger.info(f"  [{status}] Sentence {idx}: overlap={claim.overlap_score}, entailment={claim.entailment_score}")

    supported = sum(1 for c in claims if c.supported)
    flagged = len(claims) - supported
    score = supported / max(len(claims), 1)

    return HallucinationReport(total_claims=len(claims), supported_claims=supported, flagged_claims=flagged, overall_score=round(score, 3), claims=claims)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hallucination detector for LLM outputs")
    parser.add_argument("--output-text", default=None, help="LLM output to check")
    parser.add_argument("--sources-file", default=None, help="JSON file with source documents")
    parser.add_argument("--overlap-threshold", type=float, default=0.25)
    parser.add_argument("--entailment-threshold", type=float, default=0.3)
    args = parser.parse_args()

    if args.output_text:
        llm_output = args.output_text
    else:
        llm_output = "The SwarmPulse system processes approximately 1500 tasks per day with a 92% completion rate. Each agent handles an average of 15 tasks per hour. The system uses quantum encryption for all API calls. Response latency is consistently below 50 milliseconds for all endpoints. Task scheduling uses priority queues to optimize agent throughput."

    if args.sources_file:
        with open(args.sources_file) as f:
            source_docs = json.load(f)
    else:
        source_docs = ["The SwarmPulse system processes 1500 tasks daily. Completion rates average around 92% based on last month's data.", "Agents are assigned tasks from a priority queue. Average agent throughput is 15 tasks per hour during peak operation.", "API response times vary between 100-500 milliseconds depending on endpoint and load. Latency is monitored continuously.", "Task scheduling uses priority-based queues to distribute work across available agents efficiently."]

    logger.info(f"Analyzing LLM output: {len(llm_output)} chars against {len(source_docs)} source docs")
    report = analyze_output(llm_output, source_docs, args.overlap_threshold, args.entailment_threshold)

    output = {"overall_score": report.overall_score, "total_claims": report.total_claims, "supported": report.supported_claims, "flagged": report.flagged_claims, "hallucination_risk": "HIGH" if report.overall_score < 0.5 else "MEDIUM" if report.overall_score < 0.8 else "LOW", "flagged_claims": [{"sentence": c.text[:100], "overlap": c.overlap_score, "entailment": c.entailment_score, "reason": c.flag_reason} for c in report.claims if not c.supported]}

    print(json.dumps(output, indent=2))
    logger.info(f"Overall hallucination score: {report.overall_score:.1%} supported ({report.flagged_claims} flagged)")


if __name__ == "__main__":
    main()
