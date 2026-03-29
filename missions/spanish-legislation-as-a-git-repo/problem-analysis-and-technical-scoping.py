#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Problem analysis and technical scoping
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-29T20:50:09.615Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Problem analysis and technical scoping for Spanish legislation as a Git repo
Mission: Engineering - Spanish legislation as a Git repo
Agent: @aria (SwarmPulse network)
Date: 2024
Source: https://github.com/EnriqueLop/legalize-es (HN score: 618)

This tool performs deep-dive technical analysis and scoping of the Spanish legislation
Git repository structure, identifying key metrics, dependencies, documentation quality,
and architectural patterns.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import re


class LegislationRepoAnalyzer:
    """Analyzes Spanish legislation Git repository structure and content."""

    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "repo_path": str(self.repo_path),
            "metrics": {},
            "structure": {},
            "documentation": {},
            "code_quality": {},
            "dependencies": {},
            "findings": []
        }

    def analyze_repo_structure(self):
        """Analyze repository directory structure and file distribution."""
        if not self.repo_path.exists():
            self.analysis_results["findings"].append(
                {"severity": "error", "message": f"Repository path not found: {self.repo_path}"}
            )
            return

        file_types = defaultdict(int)
        directory_distribution = defaultdict(int)
        total_files = 0
        total_dirs = 0

        for item in self.repo_path.rglob("*"):
            if ".git" in item.parts:
                continue

            if item.is_file():
                total_files += 1
                suffix = item.suffix or "no_extension"
                file_types[suffix] += 1
                parent_dir = item.parent.name or "root"
                directory_distribution[parent_dir] += 1

            elif item.is_dir():
                total_dirs += 1

        self.analysis_results["structure"] = {
            "total_files": total_files,
            "total_directories": total_dirs,
            "file_types": dict(sorted(file_types.items(), key=lambda x: x[1], reverse=True)),
            "directory_distribution": dict(sorted(directory_distribution.items(), key=lambda x: x[1], reverse=True)[:10])
        }

    def analyze_documentation(self):
        """Analyze documentation quality and coverage."""
        doc_files = []
        doc_patterns = [
            "README*", "CONTRIBUTING*", "LICENSE*", "CHANGELOG*",
            "INSTALL*", "GUIDE*", "TUTORIAL*", "DOCUMENTATION*"
        ]

        for pattern in doc_patterns:
            doc_files.extend(self.repo_path.glob(f"**/{pattern}"))

        readme_count = len(list(self.repo_path.glob("**/README*")))
        license_exists = len(list(self.repo_path.glob("**/LICENSE*"))) > 0

        doc_content_size = 0
        for doc_file in doc_files:
            if doc_file.is_file():
                try:
                    doc_content_size += doc_file.stat().st_size
                except (OSError, PermissionError):
                    pass

        self.analysis_results["documentation"] = {
            "readme_files": readme_count,
            "license_present": license_exists,
            "total_doc_files": len(doc_files),
            "documentation_size_bytes": doc_content_size,
            "has_contributing_guide": any("CONTRIB" in str(f).upper() for f in doc_files),
            "has_changelog": any("CHANGELOG" in str(f).upper() for f in doc_files)
        }

        if readme_count == 0:
            self.analysis_results["findings"].append(
                {"severity": "warning", "message": "No README file found in repository"}
            )

        if not license_exists:
            self.analysis_results["findings"].append(
                {"severity": "warning", "message": "No LICENSE file found in repository"}
            )

    def analyze_git_history(self):
        """Analyze Git commit history and activity."""
        try:
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                self.analysis_results["findings"].append(
                    {"severity": "info", "message": "Not a Git repository or .git directory not accessible"}
                )
                return

            commit_count = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-list", "--count", "HEAD"],
                capture_output=True, text=True, timeout=10
            )

            if commit_count.returncode == 0:
                count = int(commit_count.stdout.strip())
                self.analysis_results["metrics"]["commit_count"] = count

            log_output = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--format=%an|%ai"],
                capture_output=True, text=True, timeout=10
            )

            if log_output.returncode == 0:
                contributors = set()
                dates = []
                for line in log_output.stdout.strip().split("\n"):
                    if "|" in line:
                        author, date_str = line.split("|", 1)
                        contributors.add(author.strip())
                        try:
                            dates.append(datetime.fromisoformat(date_str.strip().replace(" +", "+").split("+")[0]))
                        except (ValueError, IndexError):
                            pass

                self.analysis_results["metrics"]["unique_contributors"] = len(contributors)

                if dates:
                    dates.sort()
                    self.analysis_results["metrics"]["first_commit"] = dates[0].isoformat()
                    self.analysis_results["metrics"]["last_commit"] = dates[-1].isoformat()
                    days_active = (dates[-1] - dates[0]).days
                    self.analysis_results["metrics"]["repository_age_days"] = days_active

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            self.analysis_results["findings"].append(
                {"severity": "info", "message": f"Could not analyze Git history: {str(e)[:100]}"}
            )

    def analyze_code_quality(self):
        """Analyze code quality indicators."""
        code_files = defaultdict(int)
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        code_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rb", ".rs"}
        comment_patterns = {
            ".py": r"^\s*#",
            ".js": r"^\s*//|^\s*/\*",
            ".java": r"^\s*//|^\s*/\*",
            ".cpp": r"^\s*//|^\s*/\*"
        }

        for file_path in self.repo_path.rglob("*"):
            if ".git" in file_path.parts or not file_path.is_file():
                continue

            if file_path.suffix in code_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            if line.strip() == "":
                                blank_lines += 1
                            elif file_path.suffix in comment_patterns:
                                if re.match(comment_patterns[file_path.suffix], line):
                                    comment_lines += 1
                                else:
                                    code_lines += 1
                            else:
                                code_lines += 1
                    code_files[file_path.suffix] += 1
                except (OSError, PermissionError):
                    pass

        self.analysis_results["code_quality"] = {
            "code_files_by_type": dict(code_files),
            "total_code_lines": code_lines,
            "total_comment_lines": comment_lines,
            "total_blank_lines": blank_lines,
            "comment_ratio": round(comment_lines / max(code_lines, 1), 3) if code_lines > 0 else 0
        }

        if comment_lines / max(code_lines + comment_lines, 1) < 0.05:
            self.analysis_results["findings"].append(
                {"severity": "warning", "message": "Low comment-to-code ratio suggests potential documentation gaps"}
            )

    def analyze_dependencies(self):
        """Analyze project dependencies and requirements."""
        dependency_files = {
            "requirements.txt": "Python (pip)",
            "setup.py": "Python (setuptools)",
            "pyproject.toml": "Python (modern)",
            "package.json": "JavaScript (npm)",
            "Gemfile": "Ruby (bundler)",
            "go.mod": "Go",
            "Cargo.toml": "Rust",
            "pom.xml": "Java (Maven)",
            "build.gradle": "Java (Gradle)"
        }

        found_dependencies = {}
        dependency_counts = {}

        for dep_file, language in dependency_files.items():
            files = list(self.repo_path.glob(f"**/{dep_file}"))
            if files:
                found_dependencies[dep_file] = language
                try:
                    for file_path in files:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if dep_file == "requirements.txt":
                                deps = [line.strip() for line in content.split("\n") if line.strip() and not line.startswith("#")]
                                dependency_counts[dep_file] = len(deps)
                            elif dep_file == "package.json":
                                try:
                                    data = json.loads(content)
                                    deps = len(data.get("dependencies", {})) + len(data.get("devDependencies", {}))
                                    dependency_counts[dep_file] = deps
                                except json.JSONDecodeError:
                                    pass
                except (OSError, PermissionError):
                    pass

        self.analysis_results["dependencies"] = {
            "dependency_files_found": found_dependencies,
            "dependency_counts": dependency_counts,
            "languages_detected": list(set(found_dependencies.values()))
        }

    def identify_legislation_specific_patterns(self):
        """Identify patterns specific to legislation repositories."""
        legislation_indicators = {
            "legislation_files": 0,
            "legal_documents": 0,
            "regulatory_sections": 0
        }

        legal_keywords = [
            "decreto", "ley", "articulo", "disposicion", "reglamento",
            "norma", "legislacion", "codigo", "estatuto", "ordenanza",
            "real", "BOE", "DOUE"
        ]

        legal_extensions = {".md", ".txt", ".pdf", ".html", ".xml", ".rst"}

        for file_path in self.repo_path.rglob("*"):
            if ".git" in file_path.parts or not file_path.is_file():
                continue

            if file_path.suffix in legal_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        for keyword in legal_keywords:
                            if keyword in content:
                                legislation_indicators["legislation_files"] += 1
                                break
                        if "articulo" in content or "disposicion" in content:
                            legislation_indicators["legal_documents"] += 1
                        legislation_indicators["regulatory_sections"] += content.count("articulo")
                except (OSError, PermissionError):
                    pass

        self.analysis_results["legislation_analysis"] = legislation_indicators

    def generate_scope_summary(self):
        """Generate technical scope summary."""
        scope = {
            "project_maturity": self._assess_maturity(),
            "documentation_quality": self._assess_documentation_quality(),
            "complexity_level": self._assess_complexity(),
            "maintenance_status": self._assess_maintenance_status(),
            "scope_recommendations": self._generate_recommendations()
        }
        self.analysis_results["scope_summary"] = scope

    def _assess_maturity(self):
        """Assess project maturity level."""
        metrics = self.analysis_results["metrics"]
        commits = metrics.get("commit_count", 0)
        age = metrics.get("repository_age_days", 0)

        if commits > 100 and age > 365:
            return "Mature"
        elif commits > 20 and age > 90:
            return "Growing"
        elif commits > 0:
            return "Early Stage"
        else:
            return "Uninitialized"

    def _assess_documentation_quality(self):
        """Assess documentation quality."""
        doc = self.analysis_results["documentation"]
        score = 0

        if doc.get("readme_files", 0) > 0:
            score += 25
        if doc.get("license_present"):
            score += 25
        if doc.get("has_contributing_guide"):
            score += 25
        if doc.get("has_changelog"):
            score += 25

        if score >= 75:
            return "Excellent"
        elif score >= 50:
            return "Good"
        elif score >= 25:
            return "Fair"
        else:
            return "Poor"

    def _assess_complexity(self):
        """Assess project complexity."""
        structure = self.analysis_results["structure"]
        files = structure.get("total_files", 0)

        if files > 500:
            return "High"
        elif files > 100:
            return "Medium"
        else:
            return "Low"

    def _assess_maintenance_status(self):
        """Assess maintenance status."""
        try:
            metrics = self.analysis_results["metrics"]
            if "last_commit" not in metrics:
                return "Unknown"

            last_commit = datetime.fromisoformat(metrics["last_commit"])
            days_since_last = (datetime.now() - last_commit).days

            if days_since_last < 30:
                return "Actively Maintained"
            elif days_since_last < 90:
                return "Regularly Maintained"
            elif days_since_last < 365:
                return "Occasionally Maintained"
            else:
                return "Stale"
        except (KeyError, ValueError):
            return "Unknown"

    def _generate_recommendations(self):
        """Generate technical scope recommendations."""
        recommendations = []

        if not self.analysis_results["documentation"].get("has_contributing_guide"):
            recommendations.append("Create CONTRIBUTING.md to clarify contribution guidelines")

        if self.analysis_results["code_quality"].get("comment_ratio", 0) < 0.1:
            recommendations.append("Increase inline code documentation and comments")

        if self._assess_maintenance_status() in ["Stale", "Occasionally Maintained"]:
            recommendations.append("Consider updating maintenance processes and timeline")

        code_files = self.analysis_results["code_quality"].get("code_files_by_type", {})
        if len(code_files) > 3:
            recommendations.append("Consider consolidating language usage or clarifying multi-language architecture")

        return recommendations

    def run_full_analysis(self):
        """Execute complete analysis pipeline."""
        self.analyze_repo_structure()
        self.analyze_documentation()
        self.analyze_git_history()
        self.analyze_code_quality()
        self.analyze_dependencies()
        self.identify_legislation_specific_patterns()
        self.generate_scope_summary()
        return self.analysis_results


def create_sample_repo(repo_path):
    """Create a sample repository structure for demonstration."""
    repo_path = Path(repo_path)
    repo_path.mkdir(parents=True, exist_ok=True)

    structure = {
        "README.md": "# Spanish Legislation Repository\n\nThis repository contains Spanish legislative documents.",
        "LICENSE":