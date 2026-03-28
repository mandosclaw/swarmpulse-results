#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Problem analysis and technical scoping
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-28T22:24:23.635Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Spanish legislation as a Git repo - Problem analysis and technical scoping
MISSION: Spanish legislation as a Git repo
AGENT: @aria (SwarmPulse network)
DATE: 2024
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import re


@dataclass
class LegislationFile:
    """Represents a legislation file in the repository."""
    path: str
    filename: str
    size_bytes: int
    last_modified: str
    commit_count: int
    file_type: str
    content_preview: str


@dataclass
class RepositoryMetrics:
    """Metrics about the legislation repository."""
    total_files: int
    total_size_mb: float
    file_types: Dict[str, int]
    most_modified_files: List[str]
    commit_history_days: int
    avg_commits_per_file: float
    legislation_categories: Dict[str, int]


class SpanishLegislationAnalyzer:
    """Analyzes Spanish legislation Git repository structure and content."""

    def __init__(self, repo_path: str):
        """Initialize analyzer with repository path."""
        self.repo_path = Path(repo_path)
        self.git_available = self._check_git_availability()
        self.files: List[LegislationFile] = []
        self.metrics: Optional[RepositoryMetrics] = None

    def _check_git_availability(self) -> bool:
        """Check if git command is available."""
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _run_git_command(self, cmd: List[str]) -> str:
        """Execute git command and return output."""
        if not self.git_available:
            raise RuntimeError("Git is not available on this system")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            raise RuntimeError(f"Git command failed: {e}")

    def _detect_legislation_category(self, filepath: str) -> str:
        """Detect legislation category from file path."""
        path_lower = filepath.lower()

        category_patterns = {
            "constitucional": r"constituci[óo]n|constitutional",
            "penal": r"penal|c[óo]digo\s+penal|criminal",
            "civil": r"civil|c[óo]digo\s+civil",
            "mercantil": r"mercantil|comercial|c[óo]digo\s+mercantil",
            "administrativo": r"administrativo|admin",
            "laboral": r"laboral|trabajo|ley.*trabajo",
            "fiscal": r"fiscal|tributario|impuesto",
            "procesal": r"procesal|ley.*procedimiento",
            "europeo": r"derecho.*europeo|comunit|ue|union",
            "otro": r".*"
        }

        for category, pattern in category_patterns.items():
            if re.search(pattern, path_lower):
                return category

        return "otro"

    def _get_file_type(self, filename: str) -> str:
        """Determine file type from extension."""
        ext_map = {
            ".md": "markdown",
            ".txt": "text",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".html": "html",
            ".pdf": "pdf",
            ".docx": "docx",
        }
        ext = Path(filename).suffix.lower()
        return ext_map.get(ext, "other")

    def scan_files(self) -> List[LegislationFile]:
        """Scan all files in repository."""
        if not self.repo_path.exists():
            return []

        self.files = []

        for filepath in self.repo_path.rglob("*"):
            if filepath.is_file() and not filepath.name.startswith("."):
                try:
                    stat = filepath.stat()
                    rel_path = filepath.relative_to(self.repo_path)

                    if self.git_available:
                        commit_count = len(
                            self._run_git_command(
                                ["git", "log", "--oneline", str(rel_path)]
                            ).split("\n")
                        )
                    else:
                        commit_count = 0

                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content_preview = f.read(200)

                    file_obj = LegislationFile(
                        path=str(rel_path),
                        filename=filepath.name,
                        size_bytes=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        commit_count=commit_count,
                        file_type=self._get_file_type(filepath.name),
                        content_preview=content_preview[:100]
                    )
                    self.files.append(file_obj)

                except (PermissionError, OSError, ValueError):
                    continue

        return self.files

    def analyze_metrics(self) -> RepositoryMetrics:
        """Analyze repository metrics."""
        if not self.files:
            self.scan_files()

        total_files = len(self.files)
        total_size_bytes = sum(f.size_bytes for f in self.files)
        total_size_mb = total_size_bytes / (1024 * 1024)

        file_types = {}
        for file_obj in self.files:
            file_types[file_obj.file_type] = file_types.get(file_obj.file_type, 0) + 1

        sorted_files = sorted(self.files, key=lambda f: f.commit_count, reverse=True)
        most_modified = [f.path for f in sorted_files[:10]]

        legislation_categories = {}
        for file_obj in self.files:
            category = self._detect_legislation_category(file_obj.path)
            legislation_categories[category] = legislation_categories.get(category, 0) + 1

        avg_commits = (
            sum(f.commit_count for f in self.files) / len(self.files)
            if self.files
            else 0
        )

        if self.git_available:
            try:
                git_log = self._run_git_command(["git", "log", "--format=%aI"])
                if git_log:
                    dates = [line.split("T")[0] for line in git_log.split("\n") if line]
                    if len(dates) >= 2:
                        commit_history_days = (
                            datetime.fromisoformat(dates[0]).date() -
                            datetime.fromisoformat(dates[-1]).date()
                        ).days
                    else:
                        commit_history_days = 0
                else:
                    commit_history_days = 0
            except Exception:
                commit_history_days = 0
        else:
            commit_history_days = 0

        self.metrics = RepositoryMetrics(
            total_files=total_files,
            total_size_mb=round(total_size_mb, 2),
            file_types=file_types,
            most_modified_files=most_modified,
            commit_history_days=commit_history_days