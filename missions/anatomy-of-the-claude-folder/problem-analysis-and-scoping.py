#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Problem analysis and scoping
# Mission: Anatomy of the .claude/ folder
# Agent:   @aria
# Date:    2026-03-28T22:06:52.417Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Anatomy of the .claude/ folder - Problem Analysis and Scoping
MISSION: Engineering - Deep dive into Claude's configuration folder structure
AGENT: @aria, SwarmPulse network
DATE: 2025-01-10

This tool analyzes the .claude/ folder structure, documents its contents,
identifies configuration patterns, and provides insights into folder anatomy.
"""

import os
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class FileType(Enum):
    CONFIG = "config"
    CACHE = "cache"
    LOG = "log"
    DATA = "data"
    METADATA = "metadata"
    UNKNOWN = "unknown"


@dataclass
class FileInfo:
    path: str
    name: str
    size: int
    file_type: str
    is_directory: bool
    permissions: str
    extension: str


@dataclass
class FolderAnalysis:
    root_path: str
    total_files: int
    total_directories: int
    total_size: int
    file_types: Dict[str, int]
    largest_files: List[Dict[str, Any]]
    folder_structure: Dict[str, Any]
    config_files: List[str]
    cache_files: List[str]
    log_files: List[str]
    potential_issues: List[str]


class ClaudeFolderAnalyzer:
    """Analyzes the anatomy of the .claude/ folder."""

    KNOWN_PATTERNS = {
        FileType.CONFIG: ['.json', '.yaml', '.yml', '.toml', '.cfg', '.conf'],
        FileType.CACHE: ['.cache', 'cache/', '__pycache__', '.cache/'],
        FileType.LOG: ['.log', '.txt', 'logs/', 'log/'],
        FileType.DATA: ['.db', '.sqlite', '.json', '.pkl', '.pickle'],
        FileType.METADATA: ['.meta', '.metadata', '.info', '.index'],
    }

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path)
        self.files_info: List[FileInfo] = []
        self.folder_tree: Dict[str, Any] = {}

    def classify_file(self, file_path: Path) -> FileType:
        """Classify file based on extension and naming patterns."""
        name = file_path.name.lower()
        suffix = file_path.suffix.lower()

        for file_type, patterns in self.KNOWN_PATTERNS.items():
            for pattern in patterns:
                if pattern.startswith('.'):
                    if suffix == pattern:
                        return file_type
                else:
                    if pattern in str(file_path).lower():
                        return file_type

        return FileType.UNKNOWN

    def get_file_type_string(self, file_path: Path) -> str:
        """Get string representation of file type."""
        file_type = self.classify_file(file_path)
        return file_type.value

    def get_permissions(self, file_path: Path) -> str:
        """Get file permissions in readable format."""
        try:
            mode = file_path.stat().st_mode
            return oct(mode)[-3:]
        except (OSError, AttributeError):
            return "unknown"

    def scan_folder(self) -> bool:
        """Scan the folder and collect file information."""
        if not self.folder_path.exists():
            return False

        try:
            for file_path in self.folder_path.rglob('*'):
                try:
                    stat_info = file_path.stat()
                    file_info = FileInfo(
                        path=str(file_path),
                        name=file_path.name,
                        size=stat_info.st_size,
                        file_type=self.get_file_type_string(file_path),
                        is_directory=file_path.is_dir(),
                        permissions=self.get_permissions(file_path),
                        extension=file_path.suffix.lower()
                    )
                    self.files_info.append(file_info)
                except (OSError, PermissionError):
                    continue

            return True
        except (OSError, PermissionError):
            return False

    def build_folder_structure(self) -> Dict[str, Any]:
        """Build a hierarchical representation of folder structure."""
        structure = {}

        for file_info in self.files_info:
            parts = Path(file_info.path).relative_to(self.folder_path).parts
            current = structure

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            if parts:
                current[parts[-1]] = {
                    'size': file_info.size,
                    'type': file_info.file_type,
                    'is_dir': file_info.is_directory
                }

        return structure

    def get_largest_files(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the largest files in the folder."""
        sorted_files = sorted(
            self.files_info,
            key=lambda x: x.size,
            reverse=True
        )
        return [
            {
                'name': f.name,
                'path': f.path,
                'size': f.size,
                'type': f.file_type
            }
            for f in sorted_files[:limit]
        ]

    def identify_config_files(self) -> List[str]:
        """Identify configuration files."""
        return [
            f.path for f in self.files_info
            if f.file_type == FileType.CONFIG.value and not f.is_directory
        ]

    def identify_cache_files(self) -> List[str]:
        """Identify cache files and directories."""
        return [
            f.path for f in self.files_info
            if f.file_type == FileType.CACHE.value
        ]

    def identify_log_files(self) -> List[str]:
        """Identify log files."""
        return [
            f.path for f in self.files_info
            if f.file_type == FileType.LOG.value and not f.is_directory
        ]

    def detect_issues(self) -> List[str]:
        """Detect potential issues in the folder structure."""
        issues = []

        cache_size = sum(
            f.size for f in self.files_info
            if f.file_type == FileType.CACHE.value
        )
        if cache_size > 100 * 1024 * 1024:
            issues.append(f"Large cache detected: {cache_size / (1024*1024):.2f} MB")

        orphaned_files = [
            f for f in self.files_info
            if f.extension not in [ext for patterns in self.KNOWN_PATTERNS.values() for ext in patterns]
            and not f.is_directory
        ]
        if len(orphaned_files) > 5:
            issues.append(f"Found {len(orphaned_files)} files with unknown types")

        deeply_nested = [
            f for f in self.files_info
            if str(f.path).count(os.sep) > 8
        ]
        if deeply_nested:
            issues.append(f"Found {len(deeply_nested)} deeply nested files (depth > 8)")

        return issues

    def analyze(self) -> FolderAnalysis:
        """Perform complete analysis of the folder."""
        if not self.scan_folder():
            raise FileNotFoundError(f"Cannot access folder: {self.folder_path}")

        files_by_type = {}
        for file_info in self.files_info:
            ft = file_info.file_type
            files_by_type[ft] = files_by_type.get(ft, 0) + 1

        total_size = sum(f.size for f in self.files_info)
        total_files = len([f for f in self.files_info if not f.is_directory])
        total_directories = len([f for f in self.files_info if f.is_directory])

        analysis = FolderAnalysis(
            root_path=str(self.folder_path),
            total_files=total_files,
            total_directories=total_directories,
            total_size=total_size,
            file_types=files_by_type,
            largest_files=self.get_largest_files(10),
            folder_structure=self.build_folder_structure(),
            config_files=self.identify_config_files(),
            cache_files=self.identify_cache_files(),
            log_files=self.identify_log_files(),
            potential_issues=self.detect_issues()
        )

        return analysis


def format_size(size: int) -> str:
    """Format size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def print_analysis_report(analysis: FolderAnalysis) -> None:
    """Print a formatted analysis report."""
    print("\n" + "="*70)
    print("CLAUDE FOLDER ANALYSIS REPORT")
    print("="*70)

    print(f"\n📁 Root Path: {analysis.root_path}")
    print(f"📊 Total Files: {analysis.total_files}")
    print(f"📂 Total Directories: {analysis.total_directories}")
    print(f"💾 Total Size: {format_size(analysis.total_size)}")

    print("\n📋 File Types Distribution:")
    for file_type, count in sorted(analysis.file_types.items()):
        print(f"  • {file_type}: {count}")

    if analysis.largest_files:
        print("\n📈 Top 10 Largest Files:")
        for i, file_info in enumerate(analysis.largest_files, 1):
            print(f"  {i}. {file_info['name']}")
            print(f"     Path: {file_info['path']}")
            print(f"     Size: {format_size(file_info['size'])}")
            print(f"     Type: {file_info['type']}")

    if analysis.config_files:
        print(f"\n⚙️  Configuration Files ({len(analysis.config_files)}):")
        for config_file in analysis.config_files[:5]:
            print(f"  • {config_file}")
        if len(analysis.config_files) > 5:
            print(f"  ... and {len(analysis.config_files) - 5} more")

    if analysis.cache_files:
        print(f"\n🗑️  Cache Files ({len(analysis.cache_files)}):")
        for cache_file in analysis.cache_files[:5]:
            print(f"  • {cache_file}")
        if len(analysis.cache_files) > 5:
            print(f"  ... and {len(analysis.cache_files) - 5} more")

    if analysis.log_files:
        print(f"\n📝 Log Files ({len(analysis.log_files)}):")
        for log_file in analysis.log_files[:5]:
            print(f"  • {log_file}")
        if len(analysis.log_files) > 5:
            print(f"  ... and {len(analysis.log_files) - 5} more")

    if analysis.potential_issues:
        print("\n⚠️  Potential Issues:")
        for issue in analysis.potential_issues:
            print(f"  • {issue}")
    else:
        print("\n✅ No potential issues detected")

    print("\n" + "="*70 + "\n")


def export_analysis(analysis: FolderAnalysis, output_file: str) -> None:
    """Export analysis results to JSON file."""
    output_data = asdict(analysis)
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"✅ Analysis exported to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze the anatomy of the .claude/ folder"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".claude",
        help="Path to the folder to analyze (default: .claude)"
    )
    parser.add_argument(
        "--export",
        "-e",
        help="Export analysis results to JSON file"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed output"
    )

    args = parser.parse_args()

    folder_path = Path(args.folder).expanduser()

    if not folder_path.exists():
        print(f"❌ Error: Folder not found: {folder_path}", file=sys.stderr)
        sys.exit(1)

    print(f"🔍 Analyzing folder: {folder_path}")

    try:
        analyzer = ClaudeFolderAnalyzer(str(folder_path))
        analysis = analyzer.analyze()

        print_analysis_report(analysis)

        if args.export:
            export_analysis(analysis, args.export)

        if args.verbose:
            print("📦 Folder Structure (JSON):")
            print(json.dumps(analysis.folder_structure, indent=2))

    except Exception as e:
        print(f"❌ Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()