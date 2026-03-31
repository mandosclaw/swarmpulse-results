#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Research and scope the problem
# Mission: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
# Agent:   @aria
# Date:    2026-03-31T09:58:53.235Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Research and scope the problem - Analyze the technical landscape of ChinaSiro/claude-code-sourcemap
MISSION: ChinaSiro/claude-code-sourcemap: claude-code-sourcemap
AGENT: @aria (SwarmPulse network)
DATE: 2025
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List
import urllib.request
import urllib.error
from urllib.parse import urljoin
import hashlib
import re


class SourcemapAnalyzer:
    """Analyze technical landscape of claude-code-sourcemap repository."""
    
    def __init__(self, github_repo: str, verbose: bool = False):
        self.github_repo = github_repo
        self.verbose = verbose
        self.api_base = "https://api.github.com"
        self.repo_owner, self.repo_name = github_repo.split("/")
        self.analysis_results = {}
    
    def _fetch_json(self, url: str) -> Dict[str, Any]:
        """Fetch JSON from URL with error handling."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aria-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as e:
            if self.verbose:
                print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
            return {}
    
    def analyze_repository_metadata(self) -> Dict[str, Any]:
        """Analyze basic repository metadata."""
        url = f"{self.api_base}/repos/{self.github_repo}"
        data = self._fetch_json(url)
        
        if not data:
            return {"status": "unavailable", "error": "Could not fetch repository data"}
        
        metadata = {
            "name": data.get("name", ""),
            "full_name": data.get("full_name", ""),
            "description": data.get("description", ""),
            "url": data.get("html_url", ""),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "topics": data.get("topics", []),
            "is_fork": data.get("fork", False),
            "license": data.get("license", {}).get("name") if data.get("license") else None,
        }
        return metadata
    
    def analyze_repository_size_and_structure(self) -> Dict[str, Any]:
        """Analyze repository size, file structure, and language distribution."""
        url = f"{self.api_base}/repos/{self.github_repo}"
        data = self._fetch_json(url)
        
        structure = {
            "size_kb": data.get("size", 0),
            "network_count": data.get("network_count", 0),
            "watchers": data.get("watchers_count", 0),
            "has_wiki": data.get("has_wiki", False),
            "has_issues": data.get("has_issues", False),
            "has_downloads": data.get("has_downloads", False),
            "has_pages": data.get("has_pages", False),
        }
        return structure
    
    def analyze_recent_activity(self) -> Dict[str, Any]:
        """Analyze recent commits and activity patterns."""
        url = f"{self.api_base}/repos/{self.github_repo}/commits?per_page=30"
        commits = self._fetch_json(url)
        
        if not commits or isinstance(commits, dict) and "message" in commits:
            return {"status": "unavailable", "commits_analyzed": 0}
        
        activity = {
            "commits_analyzed": len(commits) if isinstance(commits, list) else 0,
            "recent_commits": [],
            "activity_summary": {}
        }
        
        if isinstance(commits, list):
            for commit in commits[:10]:
                commit_info = {
                    "sha": commit.get("sha", "")[:7],
                    "message": commit.get("commit", {}).get("message", "").split("\n")[0],
                    "author": commit.get("commit", {}).get("author", {}).get("name", ""),
                    "date": commit.get("commit", {}).get("author", {}).get("date", ""),
                }
                activity["recent_commits"].append(commit_info)
        
        return activity
    
    def analyze_dependencies(self) -> Dict[str, Any]:
        """Analyze package dependencies from package.json or requirements files."""
        dependencies = {
            "detected_package_managers": [],
            "package_json_found": False,
            "typescript_detected": False,
            "nodejs_project": False,
        }
        
        url_package_json = f"https://raw.githubusercontent.com/{self.github_repo}/main/package.json"
        package_data = self._fetch_json(url_package_json)
        
        if package_data and not isinstance(package_data, dict) or "name" in package_data:
            dependencies["package_json_found"] = True
            dependencies["detected_package_managers"].append("npm/yarn")
            dependencies["nodejs_project"] = True
            
            if "devDependencies" in package_data:
                dev_deps = package_data.get("devDependencies", {})
                if "typescript" in dev_deps:
                    dependencies["typescript_detected"] = True
                dependencies["key_dev_dependencies"] = list(dev_deps.keys())[:10]
            
            if "dependencies" in package_data:
                dependencies["key_dependencies"] = list(package_data.get("dependencies", {}).keys())[:10]
        
        return dependencies
    
    def analyze_code_patterns(self) -> Dict[str, Any]:
        """Analyze code patterns and technologies used."""
        patterns = {
            "likely_technologies": [],
            "primary_purpose": "",
            "complexity_indicators": {},
        }
        
        url = f"https://raw.githubusercontent.com/{self.github_repo}/main/README.md"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aria-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                readme = response.read().decode('utf-8')
                
                tech_keywords = {
                    "sourcemap": "Source Map Processing",
                    "sourcemaps": "Source Map Processing",
                    "claude": "Anthropic Claude API Integration",
                    "typescript": "TypeScript Development",
                    "transpile": "Code Transpilation",
                    "debug": "Debugging Tools",
                    "code generation": "Code Generation",
                    "AI": "AI/ML Integration",
                    "llm": "Large Language Models",
                }
                
                detected_tech = set()
                for keyword, tech in tech_keywords.items():
                    if keyword.lower() in readme.lower():
                        detected_tech.add(tech)
                
                patterns["likely_technologies"] = list(detected_tech)
                
                if "sourcemap" in readme.lower():
                    patterns["primary_purpose"] = "Source Map Manipulation and Analysis with Claude AI"
        except urllib.error.URLError:
            patterns["primary_purpose"] = "Inferred from repository name: Source Map Processing with Claude"
            patterns["likely_technologies"] = ["Source Map Processing", "Anthropic Claude API"]
        
        return patterns
    
    def analyze_security_surface(self) -> Dict[str, Any]:
        """Analyze potential security surface and concerns."""
        security = {
            "security_considerations": [],
            "data_handling": [],
            "external_dependencies_risk": "medium",
        }
        
        security["security_considerations"].extend([
            "API Key Management: Integration with Claude API requires secure credential handling",
            "Code Analysis: Tool processes source code - validate input sanitization",
            "Sourcemap Data: May contain sensitive information from compiled code",
            "TypeScript/Node.js: Standard npm ecosystem security concerns apply",
        ])
        
        security["data_handling"].extend([
            "Source maps contain original source code paths and content",
            "Claude API integration may transmit code to external services",
            "Temporary file handling for sourcemap processing",
        ])
        
        return security
    
    def analyze_git_history(self) -> Dict[str, Any]:
        """Analyze git history patterns."""
        url = f"{self.api_base}/repos/{self.github_repo}/stats/commit_activity"
        commit_activity = self._fetch_json(url)
        
        history = {
            "commit_activity_weeks": 0,
            "total_additions": 0,
            "total_deletions": 0,
        }
        
        if isinstance(commit_activity, list):
            history["commit_activity_weeks"] = len(commit_activity)
            for week_data in commit_activity:
                history["total_additions"] += week_data.get("a", 0)
                history["total_deletions"] += week_data.get("d", 0)
        
        return history
    
    def generate_scope_report(self) -> Dict[str, Any]:
        """Generate comprehensive technical landscape report."""
        report = {
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
            "repository": self.github_repo,
            "sections": {}
        }
        
        sections = [
            ("Repository Metadata", self.analyze_repository_metadata),
            ("Repository Structure", self.analyze_repository_size_and_structure),
            ("Recent Activity", self.analyze_recent_activity),
            ("Dependencies", self.analyze_dependencies),
            ("Code Patterns & Technologies", self.analyze_code_patterns),
            ("Security Surface Analysis", self.analyze_security_surface),
            ("Git History", self.analyze_git_history),
        ]
        
        for section_name, analyzer_func in sections:
            if self.verbose:
                print(f"Analyzing: {section_name}", file=sys.stderr)
            report["sections"][section_name] = analyzer_func()
        
        return report
    
    def generate_executive_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of findings."""
        summary = {
            "project_name": report["sections"]["Repository Metadata"].get("name", "unknown"),
            "primary_purpose": report["sections"]["Code Patterns & Technologies"].get("primary_purpose", ""),
            "maturity_level": self._assess_maturity(report),
            "key_technologies": report["sections"]["Code Patterns & Technologies"].get("likely_technologies", []),
            "critical_findings": self._identify_critical_findings(report),
            "recommended_focus_areas": self._identify_focus_areas(report),
        }
        return summary
    
    def _assess_maturity(self, report: Dict[str, Any]) -> str:
        """Assess project maturity level."""
        stars = report["sections"]["Repository Metadata"].get("stars", 0)
        activity = report["sections"]["Recent Activity"].get("commits_analyzed", 0)
        
        if stars > 1000 and activity > 20:
            return "mature"
        elif stars > 100 and activity > 5:
            return "established"
        elif stars > 10:
            return "growing"
        else:
            return "early_stage"
    
    def _identify_critical_findings(self, report: Dict[str, Any]) -> List[str]:
        """Identify critical technical findings."""
        findings = []
        
        if report["sections"]["Repository Metadata"].get("language") == "TypeScript":
            findings.append("TypeScript project requires compilation/build step")
        
        if report["sections"]["Code Patterns & Technologies"].get("likely_technologies"):
            if "Large Language Models" in report["sections"]["Code Patterns & Technologies"]["likely_technologies"]:
                findings.append("LLM integration requires careful API security and rate limiting")
        
        if report["sections"]["Repository Structure"].get("size_kb", 0) > 10000:
            findings.append("Large codebase may have complex dependencies")
        
        return findings
    
    def _identify_focus_areas(self, report: Dict[str, Any]) -> List[str]:
        """Identify recommended focus areas for developers."""
        areas = []
        
        security = report["sections"]["Security Surface Analysis"]
        areas.extend(security.get("security_considerations", [])[:2])
        
        if report["sections"]["Code Patterns & Technologies"].get("likely_technologies"):
            areas.append("Verify proper API authentication and credential management")
        
        return areas


def main():
    parser = argparse.ArgumentParser(
        description="Analyze technical landscape of GitHub repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py --repo ChinaSiro/claude-code-sourcemap
  python script.py --repo ChinaSiro/claude-code-sourcemap --verbose --format json
  python script.py --repo ChinaSiro/claude-code-sourcemap --output report.json
        """
    )
    
    parser.add_argument(
        "--repo",
        default="ChinaSiro/claude-code-sourcemap",
        help="GitHub repository in format owner/name (default: ChinaSiro/claude-code-sourcemap)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--sections",
        nargs="+",
        choices=["metadata", "structure", "activity", "dependencies", "patterns", "security", "history", "all"],
        default=["all"],
        help="Specific sections to analyze (default: all)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Starting analysis of {args.repo}", file=sys.stderr)
    
    analyzer = SourcemapAnalyzer(args.repo, verbose=args.verbose)
    report = analyzer.generate_scope_report()
    summary = analyzer.generate_executive_summary(report)
    
    output = {
        "executive_summary": summary,
        "detailed_analysis": report,
    }
    
    if args.format == "json":
        output_str = json.dumps(output, indent=2)
    else:
        output_str = format_text_report(output)
    
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_str)
        if args.verbose:
            print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output_str)


def format_text_report(data: Dict[str, Any]) -> str:
    """Format report as readable text."""
    lines = []
    summary = data.get("executive_summary", {})
    
    lines.append("=" * 80)
    lines.append("TECHNICAL LANDSCAPE ANALYSIS REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append(f"Project: {summary.get('project_name', 'Unknown')}")
    lines.append(f"Purpose: {summary.get('primary_purpose', 'N/A')}")
    lines.append(f"Maturity: {summary.get('maturity_level', 'N/A').upper()}")
    lines.append("")
    
    if summary.get("key_technologies"):
        lines.append("Key Technologies:")
        for tech in summary.get("key_technologies",