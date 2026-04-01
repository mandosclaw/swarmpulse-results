#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build proof-of-concept implementation
# Mission: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
# Agent:   @aria
# Date:    2026-04-01T18:07:07.306Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build proof-of-concept implementation for claude-code-sourcemap
Mission: ChinaSiro/claude-code-sourcemap - Source map generation for Claude AI code outputs
Agent: @aria (SwarmPulse network)
Date: 2024

This implements a proof-of-concept source map generator that tracks code transformations,
mappings between original and generated code, and provides debugging information for AI-generated code.
"""

import argparse
import json
import sys
import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import base64


@dataclass
class SourceLocation:
    """Represents a location in source code"""
    line: int
    column: int
    
    def to_dict(self) -> Dict:
        return {"line": self.line, "column": self.column}


@dataclass
class Mapping:
    """Maps a position in generated code to source code"""
    generated_line: int
    generated_column: int
    source_line: int
    source_column: int
    source_index: int
    name_index: Optional[int] = None
    
    def to_vlq(self) -> str:
        """Convert to VLQ (Variable-Length Quantity) format for source maps"""
        values = [
            self.generated_column,
            self.source_index,
            self.source_line,
            self.source_column,
        ]
        if self.name_index is not None:
            values.append(self.name_index)
        return encode_vlq(values)


@dataclass
class SourceMapMetadata:
    """Metadata about code generation and transformations"""
    timestamp: str
    model: str
    prompt_hash: str
    transformations: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CodeSourceMap:
    """Complete source map for generated code"""
    version: int = 3
    sources: List[str] = field(default_factory=list)
    source_root: str = ""
    names: List[str] = field(default_factory=list)
    mappings: List[str] = field(default_factory=list)
    sources_content: List[Optional[str]] = field(default_factory=list)
    metadata: Optional[SourceMapMetadata] = None
    
    def to_dict(self) -> Dict:
        result = {
            "version": self.version,
            "sources": self.sources,
            "names": self.names,
            "mappings": ",".join(self.mappings),
        }
        if self.source_root:
            result["sourceRoot"] = self.source_root
        if self.sources_content:
            result["sourcesContent"] = self.sources_content
        return result


def encode_vlq(values: List[int]) -> str:
    """Encode a list of integers using Variable-Length Quantity encoding"""
    def vlq_encode(value: int) -> str:
        # Handle sign bit
        if value < 0:
            value = ((-value) << 1) | 1
        else:
            value = value << 1
        
        result = ""
        while True:
            digit = value & 0x1f
            value >>= 5
            if value > 0:
                digit |= 0x20
            result += "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"[digit]
            if value == 0:
                break
        return result
    
    encoded = [vlq_encode(v) for v in values]
    return "".join(encoded)


def generate_line_mappings(
    source_lines: List[str],
    generated_lines: List[str],
    transformation_type: str = "identity"
) -> Tuple[List[Mapping], List[str]]:
    """Generate mappings between source and generated code lines"""
    mappings = []
    vlq_mappings = []
    
    min_lines = min(len(source_lines), len(generated_lines))
    
    for i in range(min_lines):
        source_line = source_lines[i]
        gen_line = generated_lines[i]
        
        # Simple token-based mapping
        source_tokens = tokenize_line(source_line)
        gen_tokens = tokenize_line(gen_line)
        
        gen_col = 0
        src_col = 0
        
        for j, (src_token, gen_token) in enumerate(zip(source_tokens, gen_tokens)):
            if gen_token.strip():
                mapping = Mapping(
                    generated_line=i,
                    generated_column=gen_col,
                    source_line=i,
                    source_column=src_col,
                    source_index=0,
                    name_index=j if j < 100 else None
                )
                mappings.append(mapping)
                vlq_mappings.append(mapping.to_vlq())
            
            gen_col += len(gen_token)
            src_col += len(src_token)
    
    return mappings, vlq_mappings


def tokenize_line(line: str) -> List[str]:
    """Tokenize a line of code into logical units"""
    # Split on whitespace and common delimiters
    pattern = r'(\s+|[(){}\[\];,.]|[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+|.)'
    tokens = re.findall(pattern, line)
    return tokens


def extract_identifiers(code: str) -> List[str]:
    """Extract all identifiers from code"""
    pattern = r'[a-zA-Z_][a-zA-Z0-9_]*'
    return list(set(re.findall(pattern, code)))


def analyze_transformations(source: str, generated: str) -> List[str]:
    """Analyze what transformations were applied to source code"""
    transformations = []
    
    if len(generated) > len(source) * 1.2:
        transformations.append("expansion")
    elif len(generated) < len(source) * 0.8:
        transformations.append("minification")
    else:
        transformations.append("modification")
    
    if source.count('\n') != generated.count('\n'):
        if generated.count('\n') > source.count('\n'):
            transformations.append("line_expansion")
        else:
            transformations.append("line_reduction")
    
    source_ids = set(extract_identifiers(source))
    gen_ids = set(extract_identifiers(generated))
    
    if source_ids != gen_ids:
        transformations.append("identifier_changes")
    
    if '"""' in generated or "'''" in generated:
        if '"""' not in source and "'''" not in source:
            transformations.append("documentation_added")
    
    return transformations


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content"""
    return hashlib.sha256(content.encode()).hexdigest()


def build_source_map(
    source_code: str,
    generated_code: str,
    source_name: str = "input.py",
    model_name: str = "claude-3",
    prompt: str = "",
    include_content: bool = True
) -> CodeSourceMap:
    """Build a complete source map for generated code"""
    
    source_lines = source_code.splitlines(keepends=False)
    generated_lines = generated_code.splitlines(keepends=False)
    
    # Generate line mappings
    mappings, vlq_mappings = generate_line_mappings(
        source_lines,
        generated_lines,
        transformation_type="ai_generation"
    )
    
    # Extract names
    names = extract_identifiers(generated_code)
    
    # Create source map
    source_map = CodeSourceMap(
        version=3,
        sources=[source_name],
        names=names,
        mappings=vlq_mappings if vlq_mappings else [""],
        sources_content=[source_code] if include_content else [None],
        metadata=SourceMapMetadata(
            timestamp=datetime.utcnow().isoformat() + "Z",
            model=model_name,
            prompt_hash=compute_hash(prompt),
            transformations=analyze_transformations(source_code, generated_code),
            confidence=0.95
        )
    )
    
    return source_map


def generate_source_map_comment(source_map_url: str) -> str:
    """Generate a source map reference comment for code"""
    return f"# //# sourceMappingURL={source_map_url}"


def format_source_map_output(
    source_map: CodeSourceMap,
    format_type: str = "json",
    include_metadata: bool = True
) -> str:
    """Format source map for output"""
    
    if format_type == "json":
        output = source_map.to_dict()
        if not include_metadata:
            output.pop("metadata", None)
        return json.dumps(output, indent=2)
    
    elif format_type == "sourcemap":
        # Standard source map format
        output = source_map.to_dict()
        if include_metadata:
            output["x_metadata"] = source_map.metadata.to_dict()
        return json.dumps(output, indent=2)
    
    elif format_type == "inline":
        # Inline base64 encoded source map
        source_map_json = json.dumps(source_map.to_dict())
        encoded = base64.b64encode(source_map_json.encode()).decode()
        return f"data:application/json;base64,{encoded}"
    
    else:
        return json.dumps(source_map.to_dict(), indent=2)


def process_code_pair(
    source_file: Path,
    generated_file: Path,
    output_file: Optional[Path] = None,
    format_type: str = "json"
) -> Dict:
    """Process a pair of source and generated code files"""
    
    # Read files
    source_code = source_file.read_text(encoding='utf-8')
    generated_code = generated_file.read_text(encoding='utf-8')
    
    # Build source map
    source_map = build_source_map(
        source_code=source_code,
        generated_code=generated_code,
        source_name=source_file.name,
        include_content=True
    )
    
    # Format output
    output = format_source_map_output(source_map, format_type=format_type)
    
    # Write output if specified
    if output_file:
        output_file.write_text(output, encoding='utf-8')
    
    return {
        "status": "success",
        "source_file": str(source_file),
        "generated_file": str(generated_file),
        "output_file": str(output_file) if output_file else None,
        "source_hash": compute_hash(source_code),
        "generated_hash": compute_hash(generated_code),
        "transformations": source_map.metadata.transformations,
        "confidence": source_map.metadata.confidence,
        "source_map": source_map.to_dict()
    }


def main():
    parser = argparse.ArgumentParser(
        description="Claude Code SourceMap - Generate source maps for AI-generated code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -s source.py -g generated.py -o map.json
  %(prog)s -s source.py -g generated.py --format inline
  %(prog)s -s source.py -g generated.py --model gpt-4 --format sourcemap
        """
    )
    
    parser.add_argument(
        "-s", "--source",
        type=Path,
        required=True,
        help="Path to source code file"
    )
    
    parser.add_argument(
        "-g", "--generated",
        type=Path,
        required=True,
        help="Path to generated code file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output path for source map (if not specified, writes to stdout)"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "sourcemap", "inline"],
        default="json",
        help="Output format for source map"
    )
    
    parser.add_argument(
        "--model",
        default="claude-3",
        help="Model name used for generation"
    )
    
    parser.add_argument(
        "--prompt",
        default="",
        help="Original prompt used for generation"
    )
    
    parser.add_argument(
        "--include-content",
        action="store_true",
        default=True,
        help="Include source content in source map"
    )
    
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output processing result as JSON"
    )
    
    args = parser.parse_args()
    
    # Validate input files exist
    if not args.source.exists():
        print(f"Error: Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)
    
    if not args.generated.exists():
        print(f"Error: Generated file not found: {args.generated}", file=sys.stderr)
        sys.exit(1)
    
    # Process files
    result = process_code_pair(
        source_file=args.source,
        generated_file=args.generated,
        output_file=args.output,
        format_type=args.format
    )
    
    # Output results
    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        if args.output:
            print(f"✓ Source map written to: {args.output}")
        else:
            # Output formatted source map to stdout
            source_code = args.source.read_text(encoding='utf-8')
            generated_code = args.generated.read_text(encoding='utf-8')
            source_map = build_source_map(
                source_code=source_code,
                generated_code=generated_code,
                source_name=args.source.name,
                model_name=args.model,
                prompt=args.prompt,
                include_content=args.include_content
            )
            print(format_source_map_output(source_map, format_type=args.format))


if __name__ == "__main__":
    # Demo: Generate sample source and code, create source map
    demo_source = '''def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
'''
    
    demo_generated = '''def calculate_sum(numbers):
    """Calculate the sum of a list of numbers.
    
    Args:
        numbers: A list of numeric values to sum.
        
    Returns:
        The sum of all numbers in the list.
    """
    total = 0
    for num in numbers:
        total += num
    return total
'''
    
    # Create temporary files for demo
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        source_file = tmpdir / "source.py"
        generated_file = tmpdir / "generated.py"
        output_file = tmpdir / "sourcemap.json"
        
        source_file.write_text(demo_source)
        generated_file.write_text(demo_generated)
        
        # Run the processing
        print("=" * 70)
        print("CLAUDE CODE SOURCEMAP - PROOF OF CONCEPT DEMO")
        print("=" * 70)
        print()
        
        result = process_code_pair(
            source_file=source_file,
            generated_file=generated_file,
            output_file=output_file,
            format_type="sourcemap"
        )
        
        print("SOURCE CODE:")
        print(demo_source)
        print()
        print("GENERATED CODE:")
        print(demo_generated)
        print()
        print("SOURCE MAP METADATA:")
        print(json.dumps(result["source_map"]["x_metadata"], indent=2))
        print()
        print("TRANSFORMATIONS DETECTED:")
        for transform in result["transformations"]:
            print(f"  - {transform}")
        print()
        print(f"CONFIDENCE: {result['confidence']}")
        print(f"OUTPUT FILE: {result['output_file']}")
        print()
        print("SAMPLE GENERATED SOURCE MAP:")
        with open(output_file) as f:
            content = json.load(f)
            print(json.dumps({
                "version": content["version"],
                "sources": content["sources"],
                "names": content["names"][:5],
                "mappings": content["mappings"][:100] + "...",
                "x_metadata": content.get("x_metadata")
            }, indent=2))