#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Anatomy of the .claude/ folder
# Agent:   @aria
# Date:    2026-03-28T22:07:08.554Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Anatomy of the .claude/ folder - Core Functionality Implementation
Mission: Engineering
Agent: @aria
Date: 2024

This implementation provides a comprehensive tool to analyze and document
the structure and contents of the .claude/ configuration folder, commonly
used by Claude AI integrations and projects.
"""

import os
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
from datetime import datetime


class FileType(Enum):
    """Enumeration of file types found in .claude/ folder"""
    CONFIG = "config"
    MODEL = "model"
    CACHE = "cache"
    LOG = "log"
    METADATA = "metadata"
    CREDENTIAL = "credential"
    OTHER = "other"


@dataclass
class FileInfo:
    """Information about a file in the .claude/ folder"""
    path: str
    name: str
    size: int
    type: FileType
    is_binary: bool
    hash: str
    readable: bool
    last_modified: float
    permissions: str


@dataclass
class FolderAnalysis:
    """Complete analysis of .claude/ folder"""
    root_path: str
    total_files: int
    total_size: int
    analysis_timestamp: str
    files: List[FileInfo]
    folder_structure: Dict[str, Any]
    statistics: Dict[str, Any]
    errors: List[str]


class ClaudeFolderAnalyzer:
    """Analyzer for .claude/ folder structure and contents"""

    FILE_TYPE_INDICATORS = {
        FileType.CONFIG: ['.yaml', '.yml', '.json', '.toml', '.conf', 'config', 'settings'],
        FileType.MODEL: ['.bin', '.pt', '.ckpt', '.pth', 'model', 'weights'],
        FileType.CACHE: ['cache', '.cache', 'tmp', 'temp'],
        FileType.LOG: ['.log', 'log', 'debug', 'error'],
        FileType.METADATA: ['meta', 'info', '.meta', 'manifest', '.manifest'],
        FileType.CREDENTIAL: ['key', 'token', 'secret', 'auth', 'credential', '.env'],
    }

    BINARY_EXTENSIONS = {
        '.bin', '.pkl', '.pt', '.pth', '.ckpt', '.safetensors',
        '.jpg', '.png', '.gif', '.zip', '.tar', '.gz', '.db'
    }

    def __init__(self, folder_path: str, verbose: bool = False):
        """Initialize the analyzer with a folder path"""
        self.folder_path = Path(folder_path)
        self.verbose = verbose
        self.errors: List[str] = []

    def detect_file_type(self, file_path: Path) -> FileType:
        """Detect file type based on name and extension"""
        name_lower = file_path.name.lower()
        suffix_lower = file_path.suffix.lower()

        for file_type, indicators in self.FILE_TYPE_INDICATORS.items():
            for indicator in indicators:
                if indicator in name_lower or indicator == suffix_lower:
                    return file_type

        return FileType.OTHER

    def is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary"""
        if file_path.suffix.lower() in self.BINARY_EXTENSIONS:
            return True

        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(512)
                if b'\x00' in chunk:
                    return True
        except (IOError, OSError):
            pass

        return False

    def calculate_hash(self, file_path: Path, is_binary: bool) -> str:
        """Calculate SHA256 hash of file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()[:16]
        except (IOError, OSError) as e:
            self.errors.append(f"Hash calculation failed for {file_path}: {str(e)}")
            return "unknown"

    def get_file_permissions(self, file_path: Path) -> str:
        """Get file permissions in readable format"""
        try:
            import stat
            st = file_path.stat()
            mode = st.st_mode
            return oct(stat.S_IMODE(mode))[2:]
        except (IOError, OSError):
            return "unknown"

    def analyze_file(self, file_path: Path) -> Optional[FileInfo]:
        """Analyze a single file"""
        try:
            stat_info = file_path.stat()
            is_binary = self.is_binary_file(file_path)
            file_type = self.detect_file_type(file_path)
            file_hash = self.calculate_hash(file_path, is_binary)
            readable = os.access(file_path, os.R_OK)
            permissions = self.get_file_permissions(file_path)

            return FileInfo(
                path=str(file_path.relative_to(self.folder_path)),
                name=file_path.name,
                size=stat_info.st_size,
                type=file_type,
                is_binary=is_binary,
                hash=file_hash,
                readable=readable,
                last_modified=stat_info.st_mtime,
                permissions=permissions
            )
        except (IOError, OSError) as e:
            self.errors.append(f"Failed to analyze {file_path}: {str(e)}")
            return None

    def build_folder_structure(self, path: Path, max_depth: int = 10, current_depth: int = 0) -> Dict[str, Any]:
        """Recursively build folder structure"""
        if current_depth >= max_depth:
            return {}

        structure = {}
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    structure[item.name] = {
                        'type': 'directory',
                        'contents': self.build_folder_structure(item, max_depth, current_depth + 1)
                    }
                else:
                    structure[item.name] = {
                        'type': 'file',
                        'size': item.stat().st_size
                    }
        except (IOError, OSError) as e:
            self.errors.append(f"Failed to read directory {path}: {str(e)}")

        return structure

    def calculate_statistics(self, files: List[FileInfo]) -> Dict[str, Any]:
        """Calculate statistics about the files"""
        if not files:
            return {
                'total_files': 0,
                'total_size': 0,
                'avg_size': 0,
                'binary_files': 0,
                'readable_files': 0,
                'by_type': {},
                'largest_files': []
            }

        stats = {
            'total_files': len(files),
            'total_size': sum(f.size for f in files),
            'avg_size': sum(f.size for f in files) // len(files) if files else 0,
            'binary_files': sum(1 for f in files if f.is_binary),
            'readable_files': sum(1 for f in files if f.readable),
            'by_type': {},
            'largest_files': []
        }

        for file_type in FileType:
            count = sum(1 for f in files if f.type == file_type)
            size = sum(f.size for f in files if f.type == file_type)
            stats['by_type'][file_type.value] = {'count': count,