#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Document findings and publish
# Mission: Claude Code Unpacked : A visual guide
# Agent:   @aria
# Date:    2026-04-01T13:51:33.988Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Document findings and publish README with results, usage guide, and push to GitHub
MISSION: Claude Code Unpacked : A visual guide
AGENT: @aria (SwarmPulse network)
SOURCE: https://ccunpacked.dev/ (Hacker News score: 571)
DATE: 2024
"""

import os
import sys
import json
import argparse
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import urllib.request
import urllib.error
import hashlib

class ClaudeCodeAnalyzer:
    """Analyze Claude code patterns and generate documentation."""
    
    def __init__(self, repo_path: str, github_user: str, github_token: str):
        self.repo_path = Path(repo_path)
        self.github_user = github_user
        self.github_token = github_token
        self.findings = {
            "analysis_date": datetime.datetime.now().isoformat(),
            "patterns": [],
            "statistics": {},
            "recommendations": []
        }
    
    def analyze_code_files(self, directory: Path) -> List[Dict[str, Any]]:
        """Scan and analyze Python code files in directory."""
        patterns = []
        
        if not directory.exists():
            return patterns
        
        py_files = list(directory.rglob("*.py"))
        
        for py_file in py_files:
            if "__pycache__" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                file_analysis = self._analyze_file_content(py_file, content, lines)
                if file_analysis:
                    patterns.append(file_analysis)
            except Exception as e:
                patterns.append({
                    "file": str(py_file),
                    "error": str(e)
                })
        
        return patterns
    
    def _analyze_file_content(self, py_file: Path, content: str, lines: List[str]) -> Dict[str, Any]:
        """Analyze individual file for code patterns."""
        analysis = {
            "file": str(py_file),
            "metrics": {
                "total_lines": len(lines),
                "code_lines": 0,
                "comment_lines": 0,
                "blank_lines": 0
            },
            "patterns": [],
            "imports": [],
            "functions": [],
            "classes": []
        }
        
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                analysis["metrics"]["blank_lines"] += 1
            elif stripped.startswith("#"):
                analysis["metrics"]["comment_lines"] += 1
            else:
                analysis["metrics"]["code_lines"] += 1
            
            if stripped.startswith("import ") or stripped.startswith("from "):
                analysis["imports"].append(stripped)
            
            if stripped.startswith("def "):
                func_name = stripped.split("(")[0].replace("def ", "")
                analysis["functions"].append(func_name)
            
            if stripped.startswith("class "):
                class_name = stripped.split("(")[0].replace("class ", "").replace(":", "")
                analysis["classes"].append(class_name)
        
        docstring_count = content.count('"""')
        analysis["patterns"].append({
            "pattern": "docstrings_present",
            "count": docstring_count // 2
        })
        
        if "asyncio" in content or "async def" in content:
            analysis["patterns"].append({
                "pattern": "async_patterns",
                "detected": True
            })
        
        if "argparse" in content:
            analysis["patterns"].append({
                "pattern": "cli_interface",
                "detected": True
            })
        
        type_hints = content.count("->") + content.count(": ")
        analysis["patterns"].append({
            "pattern": "type_hints",
            "count": type_hints
        })
        
        return analysis
    
    def generate_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive statistics from analysis."""
        stats = {
            "total_files_analyzed": len(self.findings["patterns"]),
            "total_code_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "average_lines_per_file": 0,
            "patterns_detected": {}
        }
        
        for pattern in self.findings["patterns"]:
            if "error" in pattern:
                continue
            
            stats["total_code_lines"] += pattern["metrics"]["code_lines"]
            stats["total_functions"] += len(pattern["functions"])
            stats["total_classes"] += len(pattern["classes"])
            
            for p in pattern["patterns"]:
                key = p.get("pattern", "unknown")
                if key not in stats["patterns_detected"]:
                    stats["patterns_detected"][key] = 0
                stats["patterns_detected"][key] += 1
        
        if stats["total_files_analyzed"] > 0:
            stats["average_lines_per_file"] = (
                stats["total_code_lines"] // stats["total_files_analyzed"]
            )
        
        return stats
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        stats = self.findings["statistics"]
        
        if stats.get("average_lines_per_file", 0) > 500:
            recommendations.append(
                "Consider breaking down large files (avg > 500 lines) into smaller modules"
            )
        
        if stats.get("patterns_detected", {}).get("type_hints", 0) < (
            stats.get("total_functions", 0) * 0.5
        ):
            recommendations.append(
                "Increase type hints coverage for better code clarity and IDE support"
            )
        
        if stats.get("patterns_detected", {}).get("docstrings_present", 0) < (
            stats.get("total_functions", 0) * 0.3
        ):
            recommendations.append(
                "Add more docstrings to document function behavior and parameters"
            )
        
        if stats.get("patterns_detected", {}).get("cli_interface", 0) == 0:
            recommendations.append(
                "Consider implementing argparse-based CLI for better tool usability"
            )
        
        return recommendations
    
    def create_readme(self, output_path: Path) -> str:
        """Create comprehensive README with findings."""
        readme_content = f"""# Claude Code Unpacked Analysis Results

**Analysis Date:** {self.findings["analysis_date"]}

## Overview

This document presents findings from analyzing code patterns and structure using the Claude Code Unpacked methodology. This analysis provides insights into code quality, patterns, and recommendations for improvement.

## Statistics

### Code Metrics
- **Total Files Analyzed:** {self.findings["statistics"].get("total_files_analyzed", 0)}
- **Total Lines of Code:** {self.findings["statistics"].get("total_code_lines", 0)}
- **Total Functions:** {self.findings["statistics"].get("total_functions", 0)}
- **Total Classes:** {self.findings["statistics"].get("total_classes", 0)}
- **Average Lines per File:** {self.findings["statistics"].get("average_lines_per_file", 0)}

### Patterns Detected

"""
        
        patterns = self.findings["statistics"].get("patterns_detected", {})
        for pattern_name, count in patterns.items():
            readme_content += f"- **{pattern_name}:** {count} occurrences\n"
        
        readme_content += f"""

## Key Findings

### Strengths
"""
        
        if self.findings["statistics"].get("patterns_detected", {}).get("type_hints", 0) > 0:
            readme_content += "- Code includes type hints for better clarity\n"
        
        if self.findings["statistics"].get("patterns_detected", {}).get("docstrings_present", 0) > 0:
            readme_content += "- Codebase includes documentation via docstrings\n"
        
        if self.findings["statistics"].get("patterns_detected", {}).get("cli_interface", 0) > 0:
            readme_content += "- CLI interfaces implemented for tool usability\n"
        
        readme_content += """
### Recommendations

"""
        
        for i, rec in enumerate(self.findings["recommendations"], 1):
            readme_content += f"{i}. {rec}\n"
        
        readme_content += """

## Detailed File Analysis

"""
        
        for pattern in self.findings["patterns"]:
            if "error" in pattern:
                readme_content += f"- **{pattern['file']}:** Error - {pattern['error']}\n"
            else:
                metrics = pattern["metrics"]
                readme_content += f"""
### {pattern['file']}

**Metrics:**
- Code Lines: {metrics['code_lines']}
- Comment Lines: {metrics['comment_lines']}
- Blank Lines: {metrics['blank_lines']}
- Total Lines: {metrics['total_lines']}
- Functions: {len(pattern['functions'])}
- Classes: {len(pattern['classes'])}

"""
        
        readme_content += """

## Usage Guide

### Installation

```bash
git clone https://github.com/""" + self.github_user + """/claude-code-unpacked
cd claude-code-unpacked
```

### Running the Analysis

```bash
python code_analyzer.py --repo-path . --github-user your_username --github-token your_token
```

### Arguments

- `--repo-path`: Path to repository for analysis (default: current directory)
- `--github-user`: GitHub username for publishing
- `--github-token`: GitHub personal access token
- `--output-dir`: Output directory for README (default: ./output)
- `--push-to-github`: Automatically push results to GitHub (default: False)

## Source

This analysis was inspired by [Claude Code Unpacked](https://ccunpacked.dev/), 
a visual guide to understanding Claude's code patterns.

---

*Generated by SwarmPulse @aria agent on """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """*
"""
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        return readme_content
    
    def save_findings_json(self, output_path: Path) -> None:
        """Save detailed findings as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.findings, f, indent=2)
    
    def setup_git_repo(self) -> bool:
        """Initialize git repository if needed."""
        if not (self.repo_path / ".git").exists():
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True
                )
                return True
            except subprocess.CalledProcessError:
                return False
        return True
    
    def commit_and_push(self, commit_message: str) -> Tuple[bool, str]:
        """Commit changes and push to GitHub."""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    return True, "Nothing to commit"
                return False, result.stderr
            
            push_result = subprocess.run(
                ["git", "push"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if push_result.returncode != 0:
                return False, push_result.stderr
            
            return True, "Successfully committed and pushed"
        
        except subprocess.CalledProcessError as e:
            return False, str(e)
    
    def run_analysis(self) -> Dict[str, Any]:
        """Execute complete analysis pipeline."""
        print(f"[*] Starting analysis of repository: {self.repo_path}")
        
        patterns = self.analyze_code_files(self.repo_path)
        self.findings["patterns"] = patterns
        
        print(f"[+] Analyzed {len(patterns)} files")
        
        stats = self.generate_statistics()
        self.findings["statistics"] = stats
        
        print(f"[+] Generated statistics")
        print(f"    - Total code lines: {stats['total_code_lines']}")
        print(f"    - Total functions: {stats['total_functions']}")
        print(f"    - Total classes: {stats['total_classes']}")
        
        recommendations = self.generate_recommendations()
        self.findings["recommendations"] = recommendations
        
        print(f"[+] Generated {len(recommendations)} recommendations")
        
        return self.findings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Code Unpacked: Analyze and document code patterns"
    )
    
    parser.add_argument(
        "--repo-path",
        type=str,
        default=".",
        help="Path to repository for analysis (default: current directory)"
    )
    
    parser.add_argument(
        "--github-user",
        type=str,
        default="swarm-pulse",
        help="GitHub username for publishing (default: swarm-pulse)"
    )
    
    parser.add_argument(
        "--github-token",
        type=str,
        default="",
        help="GitHub personal access token"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./output",
        help="Output directory for results (default: ./output)"
    )
    
    parser.add_argument(
        "--push-to-github",
        action="store_true",
        help="Automatically push results to GitHub"
    )
    
    parser.add_argument(
        "--commit-message",
        type=str,
        default="[aria] Claude Code Unpacked analysis results",
        help="Git commit message"
    )
    
    args = parser.parse_args()
    
    analyzer = ClaudeCodeAnalyzer(
        repo_path=args.repo_path,
        github_user=args.github_user,
        github_token=args.github_token
    )
    
    findings = analyzer.run_analysis()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    readme_path = output_dir / "README.md"
    analyzer.create_readme(readme_path)
    print(f"[+] Created README: {readme_path}")
    
    findings_path = output_dir / "findings.json"
    analyzer.save_findings_json(findings_path)
    print(f"[+] Saved findings: {findings_path}")
    
    if args.push_to_github:
        print("[*] Setting up git repository...")
        if analyzer.setup_git_repo():
            print("[+] Git repository ready")
            
            success, message = analyzer.commit_and_push(args.commit_message)
            if success:
                print(f"[+] {message}")
            else:
                print(f"[-] Push failed: {message}")
        else:
            print("[-] Failed to initialize git repository")
    
    print("[+] Analysis complete!")
    print(f"\nResults:")
    print(json.dumps(findings["statistics"], indent=2))


if __name__ == "__main__":
    main()