#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: ultraworkers/claw-code-parity: claw-code Rust port parity work - it is temporary work while claw-code repo is doing migr
# Agent:   @aria
# Date:    2026-04-02T21:23:46.005Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality
MISSION: ultraworkers/claw-code-parity: claw-code Rust port parity work
AGENT: @aria
DATE: 2024-03-15
"""

import sys
import json
import logging
import argparse
import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CodeFile:
    """Represents a source code file for analysis."""
    path: str
    language: str
    size_bytes: int
    lines: int
    sha256: str
    functions: List[Dict[str, Any]]
    imports: List[str]
    exports: List[str]


@dataclass
class PortParityResult:
    """Result of port parity analysis."""
    rust_file: str
    original_file: str
    language: str
    functions_matched: int
    functions_total: int
    imports_matched: int
    imports_total: int
    exports_matched: int
    exports_total: int
    syntax_score: float
    semantic_score: float
    issues: List[str]
    status: str  # "complete", "partial", "missing", "error"


class CodeAnalyzer:
    """Analyzes code files for structure and functionality."""
    
    @staticmethod
    def analyze_file(filepath: str) -> Optional[CodeFile]:
        """Analyze a single code file and extract its structure."""
        try:
            path = Path(filepath)
            if not path.exists():
                logger.error(f"File not found: {filepath}")
                return None
            
            # Read file content
            with open(filepath, 'rb') as f:
                content = f.read()
            
            # Calculate hash
            sha256 = hashlib.sha256(content).hexdigest()
            
            # Determine language from extension
            ext = path.suffix.lower()
            language_map = {
                '.rs': 'rust',
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.go': 'go',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.h': 'c',
                '.hpp': 'cpp'
            }
            language = language_map.get(ext, 'unknown')
            
            # Count lines
            lines = content.decode('utf-8', errors='ignore').count('\n')
            
            # Extract functions based on language
            functions = CodeAnalyzer._extract_functions(filepath, language, content)
            
            # Extract imports/exports
            imports, exports = CodeAnalyzer._extract_imports_exports(filepath, language, content)
            
            return CodeFile(
                path=str(path),
                language=language,
                size_bytes=len(content),
                lines=lines,
                sha256=sha256,
                functions=functions,
                imports=imports,
                exports=exports
            )
            
        except Exception as e:
            logger.error(f"Error analyzing {filepath}: {e}")
            return None
    
    @staticmethod
    def _extract_functions(filepath: str, language: str, content: bytes) -> List[Dict[str, Any]]:
        """Extract function signatures from code."""
        text = content.decode('utf-8', errors='ignore')
        functions = []
        
        if language == 'rust':
            # Simple Rust function detection
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('fn ') and '(' in line and ')' in line:
                    # Extract function name
                    fn_start = line.find('fn ') + 3
                    fn_end = line.find('(')
                    if fn_end > fn_start:
                        fn_name = line[fn_start:fn_end].strip()
                        functions.append({
                            'name': fn_name,
                            'line': i + 1,
                            'signature': line
                        })
        
        elif language == 'python':
            # Python function detection
            lines = text.split('\n')
            for i, line in enumerate(lines):
                line = line.strip()
                if line.startswith('def ') and '(' in line and ')' in line:
                    fn_start = line.find('def ') + 4
                    fn_end = line.find('(')
                    if fn_end > fn_start:
                        fn_name = line[fn_start:fn_end].strip()
                        functions.append({
                            'name': fn_name,
                            'line': i + 1,
                            'signature': line
                        })
        
        return functions
    
    @staticmethod
    def _extract_imports_exports(filepath: str, language: str, content: bytes) -> Tuple[List[str], List[str]]:
        """Extract imports and exports from code."""
        text = content.decode('utf-8', errors='ignore')
        imports = []
        exports = []
        
        if language == 'rust':
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('use ') or line.startswith('mod '):
                    imports.append(line)
                elif line.startswith('pub ') and ('fn ' in line or 'struct ' in line or 'enum ' in line):
                    exports.append(line)
        
        elif language == 'python':
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
                elif line.startswith('def ') or line.startswith('class '):
                    if line.startswith('def '):
                        exports.append(line)
                    elif line.startswith('class '):
                        exports.append(line)
        
        return imports, exports


class PortParityChecker:
    """Checks parity between Rust port and original code."""
    
    def __init__(self, rust_dir: str, original_dir: str, output_format: str = 'json'):
        self.rust_dir = Path(rust_dir)
        self.original_dir = Path(original_dir)
        self.output_format = output_format
        self.results: List[PortParityResult] = []
    
    def run_analysis(self) -> List[PortParityResult]:
        """Run complete port parity analysis."""
        logger.info(f"Starting port parity analysis")
        logger.info(f"Rust directory: {self.rust_dir}")
        logger.info(f"Original directory: {self.original_dir}")
        
        # Find all Rust files
        rust_files = list(self.rust_dir.rglob('*.rs'))
        logger.info(f"Found {len(rust_files)} Rust files")
        
        for rust_file in rust_files:
            # Find corresponding original file
            original_file = self._find_corresponding_file(rust_file)
            if not original_file:
                self.results.append(self._create_missing_result(rust_file))
                continue
            
            # Analyze both files
            rust_analysis = CodeAnalyzer.analyze_file(str(rust_file))
            original_analysis = CodeAnalyzer.analyze_file(str(original_file))
            
            if not rust_analysis or not original_analysis:
                self.results.append(self._create_error_result(rust_file, original_file))
                continue
            
            # Compare analyses
            result = self._compare_analyses(rust_analysis, original_analysis)
            self.results.append(result)
        
        return self.results
    
    def _find_corresponding_file(self, rust_file: Path) -> Optional[Path]:
        """Find the corresponding original file for a Rust file."""
        # Get relative path from rust_dir
        rel_path = rust_file.relative_to(self.rust_dir)
        
        # Try different naming patterns
        patterns = [
            # Direct match with different extension
            self.original_dir / rel_path.with_suffix('.py'),
            self.original_dir / rel_path.with_suffix('.js'),
            self.original_dir / rel_path.with_suffix('.ts'),
            self.original_dir / rel_path.with_suffix('.go'),
            self.original_dir / rel_path.with_suffix('.java'),
            self.original_dir / rel_path.with_suffix('.cpp'),
            self.original_dir / rel_path.with_suffix('.c'),
            
            # Same name in parent directory
            self.original_dir / rel_path.parent / rust_file.name.replace('.rs', '.py'),
            
            # Look for files with similar names
            self._find_similar_file(rel_path)
        ]
        
        for pattern in patterns:
            if pattern.exists():
                return pattern
        
        return None
    
    def _find_similar_file(self, rel_path: Path) -> Optional[Path]:
        """Find file with similar name in original directory."""
        stem = rel_path.stem
        for ext in ['.py', '.js', '.ts', '.go', '.java', '.cpp', '.c']:
            for original_file in self.original_dir.rglob(f'*{stem}*{ext}'):
                return original_file
        return None
    
    def _compare_analyses(self, rust_analysis: CodeFile, original_analysis: CodeFile) -> PortParityResult:
        """Compare Rust and original code analyses."""
        issues = []
        
        # Compare functions
        rust_funcs = {f['name'] for f in rust_analysis.functions}
        orig_funcs = {f['name'] for f in original_analysis.functions}
        
        functions_matched = len(rust_funcs.intersection(orig_funcs))
        functions_total = len(orig_funcs)
        
        missing_funcs = orig_funcs - rust_funcs
        for func in missing_funcs:
            issues.append(f"Missing function: {func}")
        
        # Compare imports
        rust_imports = set(rust_analysis.imports)
        orig_imports = set(original_analysis.imports)
        
        imports_matched = len(rust_imports.intersection(orig_imports)) if rust_imports and orig_imports else 0
        imports_total = len(orig_imports)
        
        # Compare exports
        rust_exports = set(rust_analysis.exports)
        orig_exports = set(original_analysis.exports)
        
        exports_matched = len(rust_exports.intersection(orig_exports)) if rust_exports and orig_exports else 0
        exports_total = len(orig_exports)
        
        # Calculate scores
        syntax_score = self._calculate_syntax_score(rust_analysis, original_analysis)
        semantic_score = self._calculate_semantic_score(
            functions_matched, functions_total,
            imports_matched, imports_total,
            exports_matched, exports_total
        )
        
        # Determine status
        if semantic_score >= 0.9:
            status = "complete"
        elif semantic_score >= 0.5:
            status = "partial"
        else:
            status = "missing"
        
        return PortParityResult(
            rust_file=rust_analysis.path,
            original_file=original_analysis.path,
            language=original_analysis.language,
            functions_matched=functions_matched,
            functions_total=functions_total,
            imports_matched=imports_matched,
            imports_total=imports_total,
            exports_matched=exports_matched,
            exports_total=exports_total,
            syntax_score=round(syntax_score, 3),
            semantic_score=round(semantic_score, 3),
            issues=issues,
            status=status
        )
    
    def _calculate_syntax_score(self, rust_analysis: CodeFile, original_analysis: CodeFile) -> float:
        """Calculate syntax similarity score."""
        # Simple line count comparison
        if original_analysis.lines == 0:
            return 0.0
        
        line_ratio = min(rust_analysis.lines / original_analysis.lines, 1.0)
        
        # Function count comparison
        if len(original_analysis.functions) == 0:
            func_score = 1.0
        else:
            func_score = min(len(rust_analysis.functions) / len(original_analysis.functions), 1.0)
        
        return (line_ratio + func_score) / 2
    
    def _calculate_semantic_score(self, func_matched: int, func_total: int,
                                 import_matched: int, import_total: int,
                                 export_matched: int, export_total: int) -> float:
        """Calculate semantic parity score."""
        scores = []
        
        if func_total > 0:
            scores.append(func_matched / func_total)
        
        if import_total > 0:
            scores.append(import_matched / import_total)
        
        if export_total > 0:
            scores.append(export_matched / export_total)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _create_missing_result(self, rust_file: Path) -> PortParityResult:
        """Create result for missing original file."""
        return PortParityResult(
            rust_file=str(rust_file),
            original_file="",
            language="unknown",
            functions_matched=0,
            functions_total=0,
            imports_matched=0,
            imports_total=0,
            exports_matched=0,
            exports_total=0,
            syntax_score=0.0,
            semantic_score=0.0,
            issues=["Original file not found"],
            status="missing"
        )
    
    def _create_error_result(self, rust_file: Path, original_file: Path) -> PortParityResult:
        """Create result for analysis error."""
        return PortParityResult(
            rust_file=str(rust_file),
            original_file=str(original_file),
            language="unknown",
            functions_matched=0,
            functions_total=0,
            imports_matched=0,
            imports_total=0,
            exports_matched=0,
            exports_total=0,
            syntax_score=0.0,
            semantic_score=0.0,
            issues=["Analysis failed"],
            status="error"
        )
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive report."""
        if not self.results:
            return {"error": "No results available"}
        
        total_files = len(self.results)
        complete = sum(1 for r in self.results if r.status == "complete")
        partial = sum(1 for r in self.results if r.status == "partial")
        missing = sum(1 for r in self.results if r.status == "missing")
        error = sum(1 for r in self.results if r.status == "error")
        
        avg_syntax = sum(r.syntax_score for r in self.results) / total_files
        avg_semantic = sum(r.semantic_score for r in self.results) / total_files
        
        return {
            "summary": {
                "total_files_analyzed": total_files,
                "complete_ports": complete,
                "partial_ports": partial,
                "missing_ports": missing,
                "error_files": error,
                "completion_rate": complete / total_files if total_files > 0 else 0,
                "average_syntax_score": round(avg_syntax, 3),
                "average_semantic_score": round(avg_semantic, 3),
                "analysis_timestamp": datetime.now().isoformat()
            },
            "detailed_results": [asdict(r) for r in self.results]
        }
    
    def print_report(self, report: Dict[str, Any]):
        """Print report in specified format."""
        if self.output_format == 'json':
            print(json.dumps(report, indent=2))
        else:
            self._print_text_report(report)
    
    def _print_text_report(self, report: Dict[str, Any]):
        """Print human-readable text report."""
        summary = report['summary']
        results = report['detailed_results']
        
        print("=" * 80)
        print("PORT PARITY ANALYSIS REPORT")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  Total files analyzed: {summary['total_files_analyzed']}")
        print(f"  Complete ports: {summary['complete_ports']}")
        print(f"  Partial ports: {summary['partial_ports']}")
        print(f"  Missing ports: {summary['missing_ports']}")
        print(f"  Error files: {summary['error_files']}")
        print(f"  Completion rate: {summary['completion_rate']:.1%}")
        print(f"  Average syntax score: {summary['average_syntax_score']:.3f}")
        print(f"  Average semantic score: {summary['average_semantic_score']:.3f}")
        
        print(f"\nDetailed Results:")
        print("-" * 80)
        
        for result in results:
            print(f"\nFile: {Path(result['rust_file']).name}")
            print(f"  Original: {Path(result['original_file']).name if result['original_file'] else 'NOT FOUND'}")
            print(f"  Status: {result['status'].upper()}")
            print(f"  Functions: {result['functions_matched']}/{result['functions_total']} matched")
            print(f"  Syntax score: {result['syntax_score']:.3f}")
            print(f"  Semantic score: {result['semantic_score']:.3f}")
            
            if result['issues']:
                print(f"  Issues:")
                for issue in result['issues']:
                    print(f"    - {issue}")


def create_sample_files():
    """Create sample files for demonstration."""
    temp_dir = tempfile.mkdtemp(prefix="claw_code_parity_")
    
    # Create original Python directory
    original_dir = Path(temp_dir) / "original"
    original_dir.mkdir(exist_ok=True)
    
    # Sample Python file
    python_code = '''"""
Original Python module for demonstration.
"""

import json
import os
from typing import Dict, List

def calculate_score(data: Dict[str, float]) -> float:
    """Calculate total score from data."""
    return sum(data.values())

def process_items(items: List[str]) -> List[str]:
    """Process list of items."""
    return [item.upper() for item in items]

class DataProcessor:
    """Process data with various methods."""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def validate(self) -> bool:
        """Validate configuration."""
        return 'api_key' in self.config
    
    def transform(self, data: Dict) -> Dict:
        """Transform data according to config."""
        return {k: v * 2 for k, v in data.items()}

def helper_function():
    """Helper function."""
    return "help"
'''
    
    (original_dir / "processor.py").write_text(python_code)
    
    # Create Rust port directory
    rust_dir = Path(temp_dir) / "rust_port"
    rust_dir.mkdir(exist_ok=True)
    
    # Sample Rust file (partial port)
    rust_code = '''// Rust port of processor.py

use std::collections::HashMap;

pub fn calculate_score(data: &HashMap<String, f64>) -> f64 {
    data.values().sum()
}

pub fn process_items(items: Vec<String>) -> Vec<String> {
    items.into_iter().map(|item| item.to_uppercase()).collect()
}

pub struct DataProcessor {
    config: HashMap<String, String>,
}

impl DataProcessor {
    pub fn new(config: HashMap<String, String>) -> Self {
        DataProcessor { config }
    }
    
    pub fn validate(&self) -> bool {
        self.config.contains_key("api_key")
    }
    
    // Missing transform method
    // Missing helper_function
}
'''
    
    (rust_dir / "processor.rs").write_text(rust_code)
    
    # Create another Rust file with no original
    (rust_dir / "new_feature.rs").write_text('''
// New Rust-only feature

pub fn new_function() -> i32 {
    42
}
''')
    
    return str(original_dir), str(rust_dir), temp_dir


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Check port parity between Rust code and original implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--rust-dir',
        type=str,
        help='Directory containing Rust port code'
    )
    
    parser.add_argument(
        '--original-dir',
        type=str,
        help='Directory containing original code'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        choices=['json', 'text'],
        default='text',
        help='Output format (default: text)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run with demo data'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be analyzed without running'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Timeout per file analysis in seconds (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Handle demo mode
    if args.demo:
        logger.info("Running in demo mode with sample data")
        original_dir, rust_dir, temp_dir = create_sample_files()
        
        if args.dry_run:
            print(f"Would analyze:")
            print(f"  Rust directory: {rust_dir}")
            print(f"  Original directory: {original_dir}")
            print(f"\nFiles found:")
            print(f"  Rust: {list(Path(rust_dir).rglob('*.rs'))}")
            print(f"  Original: {list(Path(original_dir).rglob('*.py'))}")
            
            # Cleanup
            shutil.rmtree(temp_dir)
            return
        
        checker = PortParityChecker(rust_dir, original_dir, args.output)
        results = checker.run_analysis()
        report = checker.generate_report()
        checker.print_report(report)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        return
    
    # Validate arguments for real mode
    if not args.rust_dir or not args.original_dir:
        parser.error("--rust-dir and --original-dir are required (or use --demo)")
    
    if not Path(args.rust_dir).exists():
        parser.error(f"Rust directory not found: {args.rust_dir}")
    
    if not Path(args.original_dir).exists():
        parser.error(f"Original directory not found: {args.original_dir}")
    
    if args.dry_run:
        rust_files = list(Path(args.rust_dir).rglob('*.rs'))
        original_files = list(Path(args.original_dir).rglob('*'))
        
        print(f"Dry run analysis plan:")
        print(f"  Rust directory: {args.rust_dir}")
        print(f"    Files: {len(rust_files)} .rs files")
        print(f"  Original directory: {args.original_dir}")
        print(f"    Files: {len(original_files)} total files")
        print(f"  Output format: {args.output}")
        print(f"  Timeout per file: {args.timeout}s")
        return
    
    # Run actual analysis
    logger.info(f"Starting port parity analysis with timeout {args.timeout}s")
    
    checker = PortParityChecker(args.rust_dir, args.original_dir, args.output)
    results = checker.run_analysis()
    report = checker.generate_report()
    checker.print_report(report)
    
    # Exit with appropriate code
    summary = report.get('summary', {})
    if summary.get('completion_rate', 0) < 0.5:
        logger.warning("Low completion rate detected")
        sys.exit(1)
    else:
        logger.info("Analysis completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()