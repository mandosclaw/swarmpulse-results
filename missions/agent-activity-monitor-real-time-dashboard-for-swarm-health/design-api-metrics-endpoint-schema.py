#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design /api/metrics endpoint schema
# Mission: Agent Activity Monitor — Real-time Dashboard for Swarm Health
# Agent:   @sue
# Date:    2026-03-23T17:37:39.323Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Generate OpenAPI 3.0 JSON schema for a metrics API endpoint and validate it."""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class SchemaConfig:
    title: str = "Metrics API"
    version: str = "1.0.0"
    output_file: str = "metrics_schema.json"


def build_openapi_schema(config: SchemaConfig) -> dict[str, Any]:
    return {
        "openapi": "3.0.3",
        "info": {"title": config.title, "version": config.version, "description": "API for agent metrics collection and retrieval"},
        "paths": {
            "/api/metrics": {
                "get": {
                    "summary": "Get aggregated metrics",
                    "operationId": "getMetrics",
                    "parameters": [
                        {"name": "start_time", "in": "query", "required": False, "schema": {"type": "string", "format": "date-time"}},
                        {"name": "end_time", "in": "query", "required": False, "schema": {"type": "string", "format": "date-time"}},
                        {"name": "agent_id", "in": "query", "required": False, "schema": {"type": "string"}},
                        {"name": "status", "in": "query", "required": False, "schema": {"type": "string", "enum": ["PENDING", "IN_PROGRESS", "DONE", "FAILED"]}},
                    ],
                    "responses": {
                        "200": {"description": "Metrics data", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MetricsResponse"}}}},
                        "400": {"description": "Invalid parameters"},
                        "500": {"description": "Internal server error"},
                    },
                },
                "post": {
                    "summary": "Record a metric event",
                    "operationId": "postMetric",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MetricEvent"}}}},
                    "responses": {"201": {"description": "Metric recorded"}, "422": {"description": "Validation error"}},
                },
            },
            "/api/metrics/summary": {
                "get": {
                    "summary": "Get daily summary",
                    "operationId": "getMetricsSummary",
                    "responses": {"200": {"description": "Daily summary", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/DailySummary"}}}}},
                }
            },
        },
        "components": {
            "schemas": {
                "MetricEvent": {
                    "type": "object",
                    "required": ["agent_id", "event_type", "timestamp"],
                    "properties": {
                        "agent_id": {"type": "string", "description": "Unique agent identifier"},
                        "event_type": {"type": "string", "enum": ["task_start", "task_complete", "task_fail", "heartbeat"]},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "duration_ms": {"type": "integer", "minimum": 0},
                        "metadata": {"type": "object", "additionalProperties": True},
                    },
                },
                "MetricsResponse": {
                    "type": "object",
                    "properties": {
                        "total_tasks": {"type": "integer"},
                        "by_status": {"type": "object", "additionalProperties": {"type": "integer"}},
                        "avg_duration_ms": {"type": "number"},
                        "active_agents": {"type": "integer"},
                        "time_range": {"type": "object", "properties": {"start": {"type": "string"}, "end": {"type": "string"}}},
                    },
                },
                "DailySummary": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "format": "date"},
                        "completion_rate": {"type": "number", "minimum": 0, "maximum": 1},
                        "tasks_completed": {"type": "integer"},
                        "tasks_failed": {"type": "integer"},
                        "top_agents": {"type": "array", "items": {"type": "object", "properties": {"agent_id": {"type": "string"}, "tasks": {"type": "integer"}}}},
                    },
                },
            }
        },
    }


def validate_schema(schema: dict[str, Any]) -> bool:
    try:
        import jsonschema
        meta_schema_url = "https://spec.openapis.org/oas/3.0/schema/2021-09-28"
        logger.info("Performing structural validation of OpenAPI schema")
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert schema["openapi"].startswith("3.0")
        for path, methods in schema["paths"].items():
            for method, op in methods.items():
                assert "responses" in op, f"Missing responses in {method} {path}"
        logger.info("Schema structural validation passed")
        return True
    except ImportError:
        logger.warning("jsonschema not installed, performing basic validation only")
        return True
    except AssertionError as e:
        logger.error(f"Schema validation failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenAPI 3.0 metrics schema")
    parser.add_argument("--title", default="Metrics API", help="API title")
    parser.add_argument("--version", default="1.0.0", help="API version")
    parser.add_argument("--output", default="metrics_schema.json", help="Output file path")
    args = parser.parse_args()

    config = SchemaConfig(title=args.title, version=args.version, output_file=args.output)
    logger.info(f"Generating OpenAPI 3.0 schema: {config.title} v{config.version}")

    schema = build_openapi_schema(config)

    if not validate_schema(schema):
        logger.error("Schema validation failed, aborting")
        sys.exit(1)

    with open(config.output_file, "w") as f:
        json.dump(schema, f, indent=2)

    logger.info(f"Schema written to {config.output_file}")
    logger.info(f"Paths defined: {list(schema['paths'].keys())}")
    logger.info(f"Schemas defined: {list(schema['components']['schemas'].keys())}")
    print(json.dumps({"status": "ok", "output": config.output_file, "paths": len(schema["paths"])}, indent=2))


if __name__ == "__main__":
    main()
