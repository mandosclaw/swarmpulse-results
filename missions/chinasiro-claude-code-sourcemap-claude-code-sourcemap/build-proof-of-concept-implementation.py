#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build proof-of-concept implementation
# Mission: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
# Agent:   @aria
# Date:    2026-04-01T18:04:19.091Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build proof-of-concept implementation for claude-code-sourcemap
Mission: ChinaSiro/claude-code-sourcemap
Agent: @aria (SwarmPulse)
Date: 2024

This implementation demonstrates core sourcemap generation and code mapping
functionality that allows Claude-generated code to be traced back to original
sources for debugging and attribution purposes.
"""

import argparse
import json
import hashlib
import sys
import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime


@dataclass
class SourceLocation:
    """Represents a location in source code"""
    file: str
    line: int
    column: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GeneratedLocation:
    """Represents a location in generated code"""
    file: str
    line: int
    column: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Mapping:
    """Maps generated code location to original source location"""
    generated: GeneratedLocation
    original: SourceLocation
    name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "generated": self.generated.to_dict(),
            "original": self.original.to_dict(),
            "name": self.name
        }


class SourceMapGenerator:
    """Generates and manages source maps for Claude-generated code"""
    
    def __init__(self):
        self.mappings: List[Mapping] = []
        self.sources: Dict[str, str] = {}
        self.source_content: Dict[str, str] = {}
        self.metadata: Dict = {
            "version": 3,
            "sources": [],
            "names": [],
            "mappings": "",
            "sourcesContent": []
        }
    
    def add_source(self, source_file: str, content: str) -> None:
        """Add a source file to the sourcemap"""
        self.sources[source_file] = content
        if source_file not in self.metadata["sources"]:
            self.metadata["sources"].append(source_file)
            self.metadata["sourcesContent"].append(content)
    
    def add_mapping(
        self,
        gen_file: str,
        gen_line: int,
        gen_col: int,
        src_file: str,
        src_line: int,
        src_col: int,
        name: Optional[str] = None
    ) -> None:
        """Add a mapping between generated and source code locations"""
        generated = GeneratedLocation(file=gen_file, line=gen_line, column=gen_col)
        original = SourceLocation(file=src_file, line=src_line, column=src_col)
        mapping = Mapping(generated=generated, original=original, name=name)
        self.mappings.append(mapping)
        
        if name and name not in self.metadata["names"]:
            self.metadata["names"].append(name)
    
    def generate_vlq_mapping(self) -> str:
        """Generate VLQ (Variable-Length Quantity) encoded mappings"""
        vlq_map = []
        
        sorted_mappings = sorted(
            self.mappings,
            key=lambda m: (m.generated.line, m.generated.column)
        )
        
        prev_gen_col = 0
        prev_gen_line = 0
        prev_src_file_idx = 0
        prev_src_line = 0
        prev_src_col = 0
        prev_name_idx = 0
        
        for mapping in sorted_mappings:
            line_diff = mapping.generated.line - prev_gen_line
            
            if line_diff > 0:
                vlq_map.append(";" * line_diff)
                prev_gen_col = 0
                prev_gen_line = mapping.generated.line
            
            col_diff = mapping.generated.column - prev_gen_col
            vlq_str = self._encode_vlq(col_diff)
            
            src_file_idx = self.metadata["sources"].index(mapping.original.file)
            src_file_diff = src_file_idx - prev_src_file_idx
            vlq_str += "," + self._encode_vlq(src_file_diff)
            
            src_line_diff = mapping.original.line - prev_src_line
            vlq_str += "," + self._encode_vlq(src_line_diff)
            
            src_col_diff = mapping.original.column - prev_src_col
            vlq_str += "," + self._encode_vlq(src_col_diff)
            
            if mapping.name:
                name_idx = self.metadata["names"].index(mapping.name)
                name_diff = name_idx - prev_name_idx
                vlq_str += "," + self._encode_vlq(name_diff)
                prev_name_idx = name_idx
            
            vlq_map.append(vlq_str)
            prev_gen_col = mapping.generated.column
            prev_src_file_idx = src_file_idx
            prev_src_line = mapping.original.line
            prev_src_col = mapping.original.column
        
        self.metadata["mappings"] = ",".join(vlq_map)
        return self.metadata["mappings"]
    
    @staticmethod
    def _encode_vlq(value: int) -> str:
        """Encode integer using VLQ"""
        vlq_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
        
        vlq_value = abs(value) << 1
        if value < 0:
            vlq_value = (vlq_value ^ -1) + 1
        
        result = ""
        while True:
            digit = vlq_value & 31
            vlq_value >>= 5
            if vlq_value > 0:
                digit |= 32
            result += vlq_alphabet[digit]
            if vlq_value == 0:
                break
        
        return result
    
    def to_sourcemap_json(self) -> str:
        """Generate complete sourcemap JSON"""
        self.generate_vlq_mapping()
        return json.dumps(self.metadata, indent=2)
    
    def to_mappings_list(self) -> List[Dict]:
        """Return mappings as structured list"""
        return [m.to_dict() for m in self.mappings]


class CodeAnalyzer:
    """Analyzes Claude-generated code and creates mappings"""
    
    def __init__(self):
        self.imports_pattern = re.compile(r'^(?:from|import)\s+(.+)$', re.MULTILINE)
        self.function_pattern = re.compile(r'^(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE)
        self.class_pattern = re.compile(r'^class\s+(\w+)[\s(:]', re.MULTILINE)
    
    def extract_definitions(self, code: str) -> Dict[str, List[Tuple[int, str]]]:
        """Extract function and class definitions from code"""
        definitions = {
            "functions": [],
            "classes": [],
            "imports": []
        }
        
        for match in self.function_pattern.finditer(code):
            line_num = code[:match.start()].count('\n') + 1
            definitions["functions"].append((line_num, match.group(1)))
        
        for match in self.class_pattern.finditer(code):
            line_num = code[:match.start()].count('\n') + 1
            definitions["classes"].append((line_num, match.group(1)))
        
        for match in self.imports_pattern.finditer(code):
            line_num = code[:match.start()].count('\n') + 1
            definitions["imports"].append((line_num, match.group(1)))
        
        return definitions
    
    def detect_code_regions(self, code: str) -> List[Dict]:
        """Identify regions of code for mapping"""
        regions = []
        lines = code.split('\n')
        
        in_block = False
        block_start = 0
        indent_level = 0
        
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            
            if stripped and not stripped.startswith('#'):
                current_indent = len(line) - len(stripped)
                
                if not in_block:
                    in_block = True
                    block_start = idx
                    indent_level = current_indent
                
                if stripped.endswith(':'):
                    regions.append({
                        "start_line": block_start + 1,
                        "end_line": idx + 1,
                        "type": "block",
                        "content": '\n'.join(lines[block_start:idx+1])
                    })
                    in_block = False
            else:
                if in_block and not stripped:
                    continue
                in_block = False
        
        return regions


class SourceMapTracer:
    """Traces generated code back to sources"""
    
    def __init__(self, sourcemap: SourceMapGenerator):
        self.sourcemap = sourcemap
    
    def find_mapping(
        self,
        gen_file: str,
        gen_line: int,
        gen_col: int
    ) -> Optional[Mapping]:
        """Find mapping for a specific location in generated code"""
        for mapping in self.sourcemap.mappings:
            if (mapping.generated.file == gen_file and
                mapping.generated.line == gen_line and
                mapping.generated.column == gen_col):
                return mapping
        return None
    
    def find_mappings_in_range(
        self,
        gen_file: str,
        start_line: int,
        end_line: int
    ) -> List[Mapping]:
        """Find all mappings in a line range"""
        results = []
        for mapping in self.sourcemap.mappings:
            if (mapping.generated.file == gen_file and
                start_line <= mapping.generated.line <= end_line):
                results.append(mapping)
        return results
    
    def trace_to_source(self, gen_file: str, gen_line: int) -> Dict:
        """Trace a generated code line back to its original source"""
        mappings_in_line = [
            m for m in self.sourcemap.mappings
            if m.generated.file == gen_file and m.generated.line == gen_line
        ]
        
        if not mappings_in_line:
            return {
                "found": False,
                "generated": {"file": gen_file, "line": gen_line},
                "original": None
            }
        
        first_mapping = mappings_in_line[0]
        return {
            "found": True,
            "generated": first_mapping.generated.to_dict(),
            "original": first_mapping.original.to_dict(),
            "name": first_mapping.name
        }


def create_demo_sourcemap() -> SourceMapGenerator:
    """Create a demonstration sourcemap"""
    sourcemap = SourceMapGenerator()
    
    prompt_content = """
def fibonacci(n):
    '''Calculate fibonacci number at position n'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def process_data(data):
    '''Process input data'''
    result = []
    for item in data:
        result.append(item * 2)
    return result
"""
    
    generated_content = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result

if __name__ == "__main__":
    print(fibonacci(5))
    print(process_data([1, 2, 3]))
"""
    
    sourcemap.add_source("prompt.py", prompt_content)
    sourcemap.add_source("generated.py", generated_content)
    
    mappings_config = [
        (1, 0, 1, 0, "fibonacci"),
        (1, 4, 1, 4, "fibonacci"),
        (2, 0, 2, 4, None),
        (3, 4, 3, 4, None),
        (5, 0, 6, 0, "process_data"),
        (5, 4, 5, 4, "process_data"),
        (6, 0, 6, 4, None),
        (7, 4, 7, 4, None),
        (8, 0, 9, 4, None),
    ]
    
    for gen_line, gen_col, src_line, src_col, name in mappings_config:
        sourcemap.add_mapping(
            "generated.py", gen_line, gen_col,
            "prompt.py", src_line, src_col,
            name
        )
    
    return sourcemap


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code Sourcemap - Trace generated code to original sources"
    )
    parser.add_argument(
        "--mode",
        choices=["generate", "trace", "analyze", "demo"],
        default="demo",
        help="Operation mode"
    )
    parser.add_argument(
        "--prompt-file",
        type=str,
        help="Path to original prompt/source file"
    )
    parser.add_argument(
        "--generated-file",
        type=str,
        help="Path to generated code file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sourcemap.json",
        help="Output sourcemap file"
    )
    parser.add_argument(
        "--trace-line",
        type=int,
        help="Line number in generated file to trace"
    )
    parser.add_argument(
        "--trace-file",
        type=str,
        help="Generated file to trace from"
    )
    parser.add_argument(
        "--format",
        choices=["sourcemap", "mappings", "json"],
        default="json",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    if args.mode == "demo":
        print("=" * 70)
        print("CLAUDE CODE SOURCEMAP - PROOF OF CONCEPT DEMONSTRATION")
        print("=" * 70)
        print()
        
        sourcemap = create_demo_sourcemap()
        
        print("1. SOURCE MAP METADATA")
        print("-" * 70)
        metadata = {
            "version": sourcemap.metadata["version"],
            "sources": sourcemap.metadata["sources"],
            "names": sourcemap.metadata["names"]
        }
        print(json.dumps(metadata, indent=2))
        print()
        
        print("2. MAPPINGS (BEFORE VLQ ENCODING)")
        print("-" * 70)
        for i, mapping in enumerate(sourcemap.to_mappings_list()[:5], 1):
            print(f"Mapping {i}: {json.dumps(mapping, indent=2)}")
        print(f"... ({len(sourcemap.mappings)} total mappings)")
        print()
        
        print("3. GENERATED SOURCEMAP (VLQ ENCODED)")
        print("-" * 70)
        sourcemap_json = sourcemap.to_sourcemap_json()
        print(sourcemap_json[:300] + "...")
        print()
        
        print("4. CODE ANALYSIS")
        print("-" * 70)
        analyzer = CodeAnalyzer()
        for source_file, content in sourcemap.sources.items():
            print(f"\nAnalyzing: {source_file}")
            definitions = analyzer.extract_definitions(content)
            print(f"  Functions: {[name for _, name in definitions['functions']]}")
            print(f"  Classes: {[name for _, name in definitions['classes']]}")
            print(f"  Imports: {len(definitions['imports'])}")
        print()
        
        print("5. SOURCEMAP TRACING")
        print("-" * 70)
        tracer = SourceMapTracer(sourcemap)
        
        test_traces = [
            ("generated.py", 1),
            ("generated.py", 5),
            ("generated.py", 10),
        ]
        
        for gen_file, gen_line in test_traces:
            trace_result = tracer.trace_to_source(gen_file, gen_line)
            print(f"\nTracing {gen_file}:{gen_line}")
            print(f"  Result: {json.dumps(trace_result, indent=4)}")
        print()
        
        print("6. REGION DETECTION")
        print("-" * 70)
        analyzer = CodeAnalyzer()
        regions = analyzer.detect_code_regions(sourcemap.sources["generated.py"])
        for region in regions[:3]:
            print(f"Region (lines {region['start_line']}-{region['end_line']}): {region['type']}")
        print()
        
        print("7. METADATA STATISTICS")
        print("-" * 70)
        stats = {
            "total_mappings": len(sourcemap.mappings),
            "source_files": len(sourcemap.sources),
            "named_mappings": len([m for m in sourcemap.mappings if m.name]),
            "unique_names": len(sourcemap.metadata["names"])
        }
        print(json.dumps(stats, indent=2))
        print()
        
        print("=" * 70)
        print(f"Sourcemap written to {args.output}")
        with open(args.output, 'w') as f:
            f.write(sourcemap_json)
        print("=" * 70)
    
    elif args.mode == "generate" and args.prompt_file and args.generated_file:
        sourcemap = SourceMapGenerator()
        
        with open(args.prompt_file, 'r') as f:
            prompt_content = f.read()
        with open(args.generated_file, 'r') as f:
            gen_content = f.read()
        
        sourcemap.add_source(args.prompt_file, prompt_content)
        sourcemap.add_source(args.generated_file, gen_content)
        
        analyzer = CodeAnalyzer()
        prompt_defs = analyzer.extract_definitions(prompt_content)
        gen_defs = analyzer.extract_definitions(gen_content)
        
        for (gen_line, func_name) in gen_defs["functions"]:
            for (src_line, src_func) in prompt_defs["functions"]:
                if func_name == src_func:
                    sourcemap.add_mapping(
                        args.generated_file, gen_line, 0,
                        args.prompt_file, src_line, 0,
                        func_name
                    )
                    break
        
        if args.format == "sourcemap":
            output = sourcemap.to_sourcemap_json()
        else:
            output = json.dumps(sourcemap.to_mappings_list(), indent=2)
        
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Sourcemap generated: {args.output}")
    
    elif args.mode == "trace" and args.trace_file and args.trace_line is not None:
        sourcemap = create