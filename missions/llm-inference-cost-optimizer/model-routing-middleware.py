#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Model routing middleware
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-23T18:09:29.577Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""WSGI middleware that intercepts LLM API calls, routes based on complexity, logs cost per request."""

import argparse
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_COSTS = {
    "gpt-4": {"input_per_1k": 0.03, "output_per_1k": 0.06},
    "gpt-4-turbo": {"input_per_1k": 0.01, "output_per_1k": 0.03},
    "gpt-3.5-turbo": {"input_per_1k": 0.001, "output_per_1k": 0.002},
    "gpt-3.5-turbo-16k": {"input_per_1k": 0.003, "output_per_1k": 0.004},
}

COMPLEX_SIGNALS = re.compile(r'\b(?:analyze|compare|synthesize|design|architect|comprehensive|multi-step|derive|algorithm|proof|research)\b', re.I)
CODE_SIGNALS = re.compile(r'```|def |class |function |SELECT |import ')


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()) * 4 // 3 + len(text) // 6)


def classify_complexity(prompt: str) -> str:
    tokens = estimate_tokens(prompt)
    complex_hits = len(COMPLEX_SIGNALS.findall(prompt))
    code_hits = len(CODE_SIGNALS.findall(prompt))
    score = (tokens / 100) + complex_hits * 1.5 + code_hits * 1.0
    if score >= 5.0:
        return "complex"
    elif score >= 2.0:
        return "medium"
    return "simple"


def select_model(complexity: str, force_model: Optional[str] = None) -> str:
    if force_model:
        return force_model
    return {"complex": "gpt-4", "medium": "gpt-3.5-turbo", "simple": "gpt-3.5-turbo"}[complexity]


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-3.5-turbo"])
    return (input_tokens / 1000) * costs["input_per_1k"] + (output_tokens / 1000) * costs["output_per_1k"]


@dataclass
class RequestLog:
    request_id: str
    timestamp: str
    prompt_preview: str
    complexity: str
    model_requested: str
    model_used: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    status: str


class LLMRoutingMiddleware:
    def __init__(self, app: Callable, api_key: str = "", log_file: str = "llm_costs.jsonl", dry_run: bool = False) -> None:
        self.app = app
        self.api_key = api_key
        self.log_file = log_file
        self.dry_run = dry_run
        self.request_logs: list[RequestLog] = []

    def __call__(self, environ: dict, start_response: Callable) -> Any:
        if environ.get("PATH_INFO", "") != "/v1/chat/completions":
            return self.app(environ, start_response)

        body_size = int(environ.get("CONTENT_LENGTH", 0) or 0)
        body = environ["wsgi.input"].read(body_size)

        try:
            request_data = json.loads(body)
        except json.JSONDecodeError:
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [json.dumps({"error": "Invalid JSON"}).encode()]

        messages = request_data.get("messages", [])
        full_prompt = " ".join(m.get("content", "") for m in messages)
        requested_model = request_data.get("model", "gpt-3.5-turbo")

        complexity = classify_complexity(full_prompt)
        routed_model = select_model(complexity, force_model=requested_model if requested_model.startswith("gpt-4") else None)

        if requested_model != routed_model:
            logger.info(f"Routing: {requested_model} -> {routed_model} (complexity: {complexity})")
            request_data["model"] = routed_model

        t0 = time.time()
        input_tokens = estimate_tokens(full_prompt)

        if self.dry_run:
            response_body = json.dumps({"id": "dry-run", "model": routed_model, "choices": [{"message": {"role": "assistant", "content": "[dry run response]"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": input_tokens, "completion_tokens": 50, "total_tokens": input_tokens + 50}})
            output_tokens = 50
            status_code = 200
        else:
            response_body, status_code, output_tokens = self._forward_request(request_data)

        latency = (time.time() - t0) * 1000
        cost = compute_cost(routed_model, input_tokens, output_tokens)

        log_entry = RequestLog(request_id=f"req-{int(time.time()*1000)}", timestamp=datetime.now().isoformat(), prompt_preview=full_prompt[:80], complexity=complexity, model_requested=requested_model, model_used=routed_model, input_tokens=input_tokens, output_tokens=output_tokens, cost_usd=round(cost, 6), latency_ms=round(latency, 2), status=str(status_code))
        self.request_logs.append(log_entry)
        self._write_log(log_entry)

        logger.info(f"[{complexity.upper()}] model={routed_model} tokens={input_tokens}+{output_tokens} cost=${cost:.6f} {latency:.0f}ms")
        status_str = f"{status_code} {'OK' if status_code == 200 else 'Error'}"
        start_response(status_str, [("Content-Type", "application/json")])
        return [response_body.encode() if isinstance(response_body, str) else response_body]

    def _forward_request(self, data: dict) -> tuple[str, int, int]:
        url = "https://api.openai.com/v1/chat/completions"
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                response_body = resp.read().decode()
                resp_data = json.loads(response_body)
                output_tokens = resp_data.get("usage", {}).get("completion_tokens", 50)
                return response_body, resp.status, output_tokens
        except urllib.error.HTTPError as e:
            return e.read().decode(), e.code, 0
        except Exception as ex:
            return json.dumps({"error": str(ex)}), 500, 0

    def _write_log(self, entry: RequestLog) -> None:
        with open(self.log_file, "a") as f:
            f.write(json.dumps({"request_id": entry.request_id, "timestamp": entry.timestamp, "complexity": entry.complexity, "model_used": entry.model_used, "tokens_in": entry.input_tokens, "tokens_out": entry.output_tokens, "cost_usd": entry.cost_usd, "latency_ms": entry.latency_ms}) + "\n")

    def get_cost_summary(self) -> dict[str, Any]:
        by_model: dict[str, dict] = {}
        for log in self.request_logs:
            if log.model_used not in by_model:
                by_model[log.model_used] = {"requests": 0, "total_cost": 0.0, "total_tokens": 0}
            by_model[log.model_used]["requests"] += 1
            by_model[log.model_used]["total_cost"] += log.cost_usd
            by_model[log.model_used]["total_tokens"] += log.input_tokens + log.output_tokens
        return {"total_requests": len(self.request_logs), "total_cost_usd": round(sum(l.cost_usd for l in self.request_logs), 6), "by_model": by_model}


def simple_wsgi_app(environ: dict, start_response: Callable) -> list:
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"base app"]


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM routing middleware demo")
    parser.add_argument("--api-key", default="", help="OpenAI API key")
    parser.add_argument("--log-file", default="llm_costs.jsonl")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--simulate-requests", type=int, default=5)
    args = parser.parse_args()

    middleware = LLMRoutingMiddleware(simple_wsgi_app, api_key=args.api_key, log_file=args.log_file, dry_run=args.dry_run)

    test_prompts = [
        "What is 2+2?", "Summarize the key points of machine learning", "Write a comprehensive analysis of transformer architectures with code examples",
        "Fix this: print 'hello'", "Design a distributed event streaming system with exactly-once guarantees, fault tolerance, and horizontal scaling",
    ]

    for i, prompt in enumerate(test_prompts[:args.simulate_requests]):
        import io
        body = json.dumps({"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": prompt}]}).encode()
        environ = {"PATH_INFO": "/v1/chat/completions", "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
        responses = []
        def start_response(status, headers, exc=None): responses.append(status)
        middleware(environ, start_response)

    summary = middleware.get_cost_summary()
    logger.info(f"Middleware summary: {summary}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
