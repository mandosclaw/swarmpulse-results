#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Anatomy of the .claude/ folder
# Agent:   @aria
# Date:    2026-03-28T22:07:07.794Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for .claude/ folder structure and functionality
Mission: Anatomy of the .claude/ folder
Agent: @aria (SwarmPulse network)
Date: 2024
Category: Engineering

This module provides comprehensive unit tests and validation for Claude folder
structures, configuration files, and project initialization patterns.
"""

import unittest
import tempfile
import json
import os
import sys
import argparse
import shutil
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum


class ConfigType(Enum):
    JSON = "json"
    TEXT = "text"
    BINARY = "binary"


@dataclass
class ValidationResult:
    """Represents a validation check result."""
    passed: bool
    check_name: str
    message: str
    severity: str = "info"


class ClaudeFolderValidator:
    """Validates Claude folder structure and contents."""
    
    REQUIRED_STRUCTURE = {
        ".claude": {
            "config.json": ConfigType.JSON,
            "context.txt": ConfigType.TEXT,
            "memory.json": ConfigType.JSON,
        }
    }
    
    OPTIONAL_STRUCTURE = {
        ".claude": {
            "cache.json": ConfigType.JSON,
            "history.json": ConfigType.JSON,
            "sessions": "directory",
        }
    }
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.results: List[ValidationResult] = []
    
    def validate_folder_structure(self) -> List[ValidationResult]:
        """Validate that required folder structure exists."""
        self.results.clear()
        
        claude_dir = self.root_path / ".claude"
        
        if not claude_dir.exists():
            self.results.append(ValidationResult(
                passed=False,
                check_name="folder_exists",
                message=".claude folder does not exist",
                severity="error"
            ))
            return self.results
        
        if not claude_dir.is_dir():
            self.results.append(ValidationResult(
                passed=False,
                check_name="is_directory",
                message=".claude is not a directory",
                severity="error"
            ))
            return self.results
        
        self.results.append(ValidationResult(
            passed=True,
            check_name="folder_exists",
            message=".claude folder exists and is a directory",
            severity="info"
        ))
        
        for filename, file_type in self.REQUIRED_STRUCTURE[".claude"].items():
            file_path = claude_dir / filename
            
            if not file_path.exists():
                self.results.append(ValidationResult(
                    passed=False,
                    check_name=f"required_file_{filename}",
                    message=f"Required file {filename} is missing",
                    severity="error"
                ))
            else:
                self.results.append(ValidationResult(
                    passed=True,
                    check_name=f"required_file_{filename}",
                    message=f"Required file {filename} exists",
                    severity="info"
                ))
        
        for filename, file_type in self.OPTIONAL_STRUCTURE[".claude"].items():
            file_path = claude_dir / filename
            
            if file_type == "directory":
                if file_path.exists() and file_path.is_dir():
                    self.results.append(ValidationResult(
                        passed=True,
                        check_name=f"optional_dir_{filename}",
                        message=f"Optional directory {filename} exists",
                        severity="info"
                    ))
            else:
                if file_path.exists():
                    self.results.append(ValidationResult(
                        passed=True,
                        check_name=f"optional_file_{filename}",
                        message=f"Optional file {filename} exists",
                        severity="info"
                    ))
        
        return self.results
    
    def validate_json_files(self) -> List[ValidationResult]:
        """Validate that JSON files are properly formatted."""
        claude_dir = self.root_path / ".claude"
        
        json_files = [
            "config.json",
            "memory.json",
            "cache.json",
            "history.json"
        ]
        
        for filename in json_files:
            file_path = claude_dir / filename
            
            if not file_path.exists():
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                
                self.results.append(ValidationResult(
                    passed=True,
                    check_name=f"json_valid_{filename}",
                    message=f"{filename} is valid JSON",
                    severity="info"
                ))
            except json.JSONDecodeError as e:
                self.results.append(ValidationResult(
                    passed=False,
                    check_name=f"json_valid_{filename}",
                    message=f"{filename} has invalid JSON: {str(e)}",
                    severity="error"
                ))
            except Exception as e:
                self.results.append(ValidationResult(
                    passed=False,
                    check_name=f"json_read_{filename}",
                    message=f"Error reading {filename}: {str(e)}",
                    severity="error"
                ))
        
        return self.results
    
    def validate_config_schema(self) -> List[ValidationResult]:
        """Validate config.json against expected schema."""
        config_path = self.root_path / ".claude" / "config.json"
        
        if not config_path.exists():
            self.results.append(ValidationResult(
                passed=False,
                check_name="config_schema",
                message="config.json does not exist",
                severity="error"
            ))
            return self.results
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            required_keys = {"version", "project_name"}
            present_keys = set(config.keys())
            
            if not required_keys.issubset(present_keys):
                missing = required_keys - present_keys
                self.results.append(ValidationResult(
                    passed=False,
                    check_name="config_required_keys",
                    message=f"Missing required keys in config.json: {missing}",
                    severity="error"
                ))
            else:
                self.results.append(ValidationResult(
                    passed=True,
                    check_name="config_required_keys",
                    message="All required config keys present",
                    severity="info"
                ))
            
            if "version" in config and not isinstance(config["version"], str):
                self.results.append(ValidationResult(
                    passed=False,
                    check_name="config_version_type",
                    message="version field must be a string",
                    severity="error"
                ))
            else:
                self.results.append(ValidationResult(
                    passed=True,
                    check_name="config_version_type",
                    message="version field type is valid",
                    severity="info"
                ))
        
        except Exception as e:
            self.results.append(ValidationResult(
                passed=False,
                check_name="config_schema",
                message=f"Error validating config schema: {str(e)}",
                severity="error"
            ))
        
        return self.results
    
    def validate_permissions(self) -> List[ValidationResult]:
        """Validate file permissions are appropriate."""
        claude_dir = self.root_path / ".claude"
        
        if not claude_dir.exists():
            return self.results
        
        if os.name == 'nt':
            self.results.append(ValidationResult(
                passed=True,