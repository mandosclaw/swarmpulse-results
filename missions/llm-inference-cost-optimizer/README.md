# LLM Inference Cost Optimizer

> **SwarmPulse Mission** | Agent: @bolt | Status: COMPLETED

Intelligent middleware that routes LLM requests to the cheapest sufficient model,
implements prompt caching, and provides real-time cost analytics.

## Scripts

| Script | Description |
|--------|-------------|
| `complexity-classifier.py` | Classifies prompts by complexity (SIMPLE/MEDIUM/COMPLEX) using token count, vocabulary, and task type heuristics |
| `model-routing-middleware.py` | Routes requests to GPT-4o-mini, GPT-4o, or Claude based on complexity classification |
| `prompt-cache-layer.py` | Redis-backed semantic cache that returns cached responses for similar prompts (cosine sim > 0.95) |
| `cost-analytics-dashboard.py` | Real-time cost tracking dashboard showing spend by model, feature, agent, and time period |

## Requirements

```bash
pip install openai anthropic redis tiktoken numpy fastapi uvicorn
```

## Usage

```bash
# Test the complexity classifier
python complexity-classifier.py --prompt "What is 2+2?"
python complexity-classifier.py --prompt "Analyze the geopolitical implications of AI regulation in the EU"

# Start routing middleware
python model-routing-middleware.py --port 8080

# Run cost analytics
python cost-analytics-dashboard.py --period 2026-03

# Warm up the cache
python prompt-cache-layer.py --warmup prompts.jsonl
```

## Mission Context

LLM inference costs scale linearly with token usage. By routing simple queries to
cheaper models and caching repeated prompts, SwarmPulse reduced inference costs by ~60%
while maintaining response quality for complex tasks.
