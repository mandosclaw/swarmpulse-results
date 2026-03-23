#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    OTel span instrumentation
# Mission: AI Agent Observability Platform
# Agent:   @sue
# Date:    2026-03-23T13:12:19.992Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""
OTel Span Instrumentation — instruments Python services with OpenTelemetry tracing.
"""
import argparse
import ast
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

OTEL_IMPORTS = """from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
"""

TRACER_INIT = """
def init_tracer(service_name: str, endpoint: str = "http://localhost:4317") -> trace.Tracer:
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
"""

@dataclass
class FunctionInfo:
    name: str
    lineno: int
    args: list[str]
    is_async: bool
    already_instrumented: bool = False

@dataclass
class InstrumentationReport:
    file: str
    functions_found: int = 0
    functions_instrumented: int = 0
    already_instrumented: int = 0
    issues: list[str] = field(default_factory=list)

def analyze_file(path: Path) -> tuple[list[FunctionInfo], bool]:
    try:
        source = path.read_text()
        tree = ast.parse(source)
    except SyntaxError as e:
        log.error("Syntax error in %s: %s", path, e)
        return [], False

    has_otel = "opentelemetry" in source
    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            already = any(
                isinstance(d, ast.Call) and
                (getattr(d.func, "attr", "") == "start_as_current_span" or
                 getattr(d.func, "id", "") == "span")
                for d in ast.walk(node)
            )
            functions.append(FunctionInfo(
                name=node.name,
                lineno=node.lineno,
                args=args,
                is_async=isinstance(node, ast.AsyncFunctionDef),
                already_instrumented=already,
            ))
    return functions, has_otel

def generate_instrumented(source: str, functions: list[FunctionInfo], tracer_name: str) -> str:
    lines = source.splitlines()
    # Insert imports at top
    insert_pos = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_pos = i
    lines.insert(insert_pos + 1, OTEL_IMPORTS.strip())
    lines.insert(insert_pos + 2, f'\ntracer = trace.get_tracer("{tracer_name}")')

    # Add @tracer.start_as_current_span decorator before uninstrumented functions
    offset = 2
    for fn in sorted(functions, key=lambda f: f.lineno):
        if not fn.already_instrumented:
            idx = fn.lineno - 1 + offset
            decorator = f'@tracer.start_as_current_span("{fn.name}")'
            lines.insert(idx, decorator)
            offset += 1
    return "\n".join(lines)

def instrument_directory(directory: Path, tracer_name: str, dry_run: bool = True) -> list[InstrumentationReport]:
    reports = []
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        functions, has_otel = analyze_file(py_file)
        report = InstrumentationReport(file=str(py_file), functions_found=len(functions))
        for fn in functions:
            if fn.already_instrumented:
                report.already_instrumented += 1
            else:
                report.functions_instrumented += 1
        if not dry_run and report.functions_instrumented > 0:
            source = py_file.read_text()
            instrumented = generate_instrumented(source, functions, tracer_name)
            py_file.write_text(instrumented)
            log.info("Instrumented %s (%d functions)", py_file, report.functions_instrumented)
        reports.append(report)
    return reports

def main():
    parser = argparse.ArgumentParser(description="OTel Span Instrumentation Tool")
    parser.add_argument("directory", help="Directory to instrument")
    parser.add_argument("--tracer-name", default="swarmpulse", help="Tracer name")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Analyze only, don't modify")
    parser.add_argument("--apply", action="store_true", help="Actually write instrumented files")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    args = parser.parse_args()

    reports = instrument_directory(Path(args.directory), args.tracer_name, dry_run=not args.apply)
    total_fns = sum(r.functions_found for r in reports)
    total_to_instrument = sum(r.functions_instrumented for r in reports)
    summary = {
        "files_analyzed": len(reports),
        "total_functions": total_fns,
        "to_instrument": total_to_instrument,
        "already_instrumented": sum(r.already_instrumented for r in reports),
        "dry_run": not args.apply,
        "files": [{"file": r.file, "functions": r.functions_found, "to_instrument": r.functions_instrumented} for r in reports],
    }
    print(json.dumps(summary, indent=2))
    if args.output:
        with open(args.output, "w") as f:
            json.dump(summary, f, indent=2)

if __name__ == "__main__":
    main()
