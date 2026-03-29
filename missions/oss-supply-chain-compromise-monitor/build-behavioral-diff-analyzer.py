#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build behavioral diff analyzer
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-29T13:21:48.753Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build behavioral diff analyzer
Mission: OSS Supply Chain Compromise Monitor
Agent: @dex
Date: 2025-01-13

Behavioral diff analyzer for detecting supply chain compromises through
package behavior analysis, comparing signatures across versions.
"""

import argparse
import json
import hashlib
import difflib
import sys
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Set
from datetime import datetime
from pathlib import Path
import re


@dataclass
class BehaviorSignature:
    """Represents behavioral characteristics of a package version."""
    version: str
    timestamp: str
    imports: Set[str] = field(default_factory=set)
    network_calls: Set[str] = field(default_factory=set)
    file_operations: Set[str] = field(default_factory=set)
    subprocess_calls: Set[str] = field(default_factory=set)
    env_vars_accessed: Set[str] = field(default_factory=set)
    external_commands: Set[str] = field(default_factory=set)
    suspicious_patterns: List[str] = field(default_factory=list)
    checksum: str = ""
    
    def to_dict(self):
        """Convert to serializable dict."""
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "imports": sorted(list(self.imports)),
            "network_calls": sorted(list(self.network_calls)),
            "file_operations": sorted(list(self.file_operations)),
            "subprocess_calls": sorted(list(self.subprocess_calls)),
            "env_vars_accessed": sorted(list(self.env_vars_accessed)),
            "external_commands": sorted(list(self.external_commands)),
            "suspicious_patterns": self.suspicious_patterns,
            "checksum": self.checksum,
        }


@dataclass
class BehaviorDiff:
    """Results of comparing two behavior signatures."""
    old_version: str
    new_version: str
    added_imports: List[str]
    removed_imports: List[str]
    added_network_calls: List[str]
    removed_network_calls: List[str]
    added_file_operations: List[str]
    removed_file_operations: List[str]
    added_subprocess_calls: List[str]
    removed_subprocess_calls: List[str]
    added_env_vars: List[str]
    removed_env_vars: List[str]
    added_external_commands: List[str]
    removed_external_commands: List[str]
    new_suspicious_patterns: List[str]
    risk_score: float
    risk_level: str
    
    def to_dict(self):
        """Convert to serializable dict."""
        return {
            "old_version": self.old_version,
            "new_version": self.new_version,
            "added_imports": self.added_imports,
            "removed_imports": self.removed_imports,
            "added_network_calls": self.added_network_calls,
            "removed_network_calls": self.removed_network_calls,
            "added_file_operations": self.added_file_operations,
            "removed_file_operations": self.removed_file_operations,
            "added_subprocess_calls": self.added_subprocess_calls,
            "removed_subprocess_calls": self.removed_subprocess_calls,
            "added_env_vars": self.added_env_vars,
            "removed_env_vars": self.removed_env_vars,
            "added_external_commands": self.added_external_commands,
            "removed_external_commands": self.removed_external_commands,
            "new_suspicious_patterns": self.new_suspicious_patterns,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
        }


class BehaviorAnalyzer:
    """Analyzes package source code for behavioral characteristics."""
    
    SUSPICIOUS_PATTERNS = [
        r"exec\s*\(",
        r"eval\s*\(",
        r"__import__\s*\(",
        r"compile\s*\(",
        r"os\.system\s*\(",
        r"subprocess\.call\s*\(",
        r"socket\.\w+\(",
        r"urllib.*request",
        r"requests\.get\s*\(",
        r"requests\.post\s*\(",
        r"base64\.b64decode",
        r"pickle\.loads",
        r"marshal\.loads",
        r"ctypes\.CDLL",
        r"getpass\.getpass",
        r"os\.environ\[",
        r"open\s*\(\s*['\"]\/etc",
        r"open\s*\(\s*['\"]\/root",
        r"chmod\s*\(",
        r"chmod\s+\d+",
    ]
    
    def __init__(self):
        self.compiled_patterns = [re.compile(p) for p in self.SUSPICIOUS_PATTERNS]
    
    def extract_imports(self, code: str) -> Set[str]:
        """Extract import statements from Python code."""
        imports = set()
        import_patterns = [
            r"^import\s+([\w.]+)",
            r"^from\s+([\w.]+)\s+import",
        ]
        
        for line in code.split('\n'):
            line = line.strip()
            if line.startswith('#'):
                continue
            for pattern in import_patterns:
                matches = re.findall(pattern, line)
                imports.update(matches)
        
        return imports
    
    def extract_network_calls(self, code: str) -> Set[str]:
        """Extract network-related function calls."""
        network = set()
        patterns = [
            r"socket\.",
            r"urllib\.",
            r"requests\.",
            r"http\.client",
            r"ftplib\.",
            r"smtplib\.",
            r"poplib\.",
            r"imaplib\.",
        ]
        
        for pattern in patterns:
            if re.search(pattern, code):
                network.add(pattern.replace(r"\.",""))
        
        return network
    
    def extract_file_operations(self, code: str) -> Set[str]:
        """Extract file operation patterns."""
        files = set()
        patterns = [
            (r"open\s*\(", "open"),
            (r"os\.remove\s*\(", "remove"),
            (r"os\.rename\s*\(", "rename"),
            (r"os\.chmod\s*\(", "chmod"),
            (r"shutil\.", "shutil"),
            (r"pathlib\.", "pathlib"),
        ]
        
        for pattern, name in patterns:
            if re.search(pattern, code):
                files.add(name)
        
        return files
    
    def extract_subprocess_calls(self, code: str) -> Set[str]:
        """Extract subprocess/shell execution patterns."""
        subprocess_ops = set()
        patterns = [
            (r"subprocess\.call\s*\(", "subprocess.call"),
            (r"subprocess\.run\s*\(", "subprocess.run"),
            (r"subprocess\.Popen\s*\(", "subprocess.Popen"),
            (r"os\.system\s*\(", "os.system"),
            (r"os\.popen\s*\(", "os.popen"),
        ]
        
        for pattern, name in patterns:
            if re.search(pattern, code):
                subprocess_ops.add(name)
        
        return subprocess_ops
    
    def extract_env_vars(self, code: str) -> Set[str]:
        """Extract environment variable access."""
        env_vars = set()
        patterns = [
            r"os\.environ\[?['\"]?(\w+)['\"]?\]?",
            r"os\.getenv\(['\"](\w+)['\"]",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, code)
            env_vars.update(matches)
        
        return env_vars
    
    def extract_external_commands(self, code: str) -> Set[str]:
        """Extract references to external commands."""
        commands = set()
        patterns = [
            r"['\"]([a-z]+)\s+",
            r"subprocess.*['\"]([a-z]+)['\"]",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, code)
            commands.update([m for m in matches if len(m) < 50])
        
        return commands
    
    def detect_suspicious_patterns(self, code: str) -> List[str]:
        """Detect suspicious code patterns."""
        suspicious = []
        
        for pattern in self.compiled_patterns:
            matches = pattern.findall(code)
            if matches:
                suspicious.append(pattern.pattern)
        
        return suspicious
    
    def analyze_code(self, code: str, version: str) -> BehaviorSignature:
        """Analyze Python code and extract behavior signature."""
        signature = BehaviorSignature(
            version=version,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        signature.imports = self.extract_imports(code)
        signature.network_calls = self.extract_network_calls(code)
        signature.file_operations = self.extract_file_operations(code)
        signature.subprocess_calls = self.extract_subprocess_calls(code)
        signature.env_vars_accessed = self.extract_env_vars(code)
        signature.external_commands = self.extract_external_commands(code)
        signature.suspicious_patterns = self.detect_suspicious_patterns(code)
        
        signature.checksum = hashlib.sha256(code.encode()).hexdigest()
        
        return signature


class BehaviorDiffAnalyzer:
    """Compares behavior signatures to detect anomalies."""
    
    RISK_WEIGHTS = {
        "added_subprocess_calls": 15,
        "added_network_calls": 12,
        "added_file_operations": 8,
        "new_suspicious_patterns": 20,
        "added_env_vars": 5,
        "added_external_commands": 10,
        "added_imports": 3,
    }
    
    def __init__(self, warning_threshold: float = 20, critical_threshold: float = 50):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def compute_diff(self, old_sig: BehaviorSignature, new_sig: BehaviorSignature) -> BehaviorDiff:
        """Compute differences between two signatures."""
        
        added_imports = sorted(list(new_sig.imports - old_sig.imports))
        removed_imports = sorted(list(old_sig.imports - new_sig.imports))
        
        added_network = sorted(list(new_sig.network_calls - old_sig.network_calls))
        removed_network = sorted(list(old_sig.network_calls - new_sig.network_calls))
        
        added_files = sorted(list(new_sig.file_operations - old_sig.file_operations))
        removed_files = sorted(list(old_sig.file_operations - new_sig.file_operations))
        
        added_subprocess = sorted(list(new_sig.subprocess_calls - old_sig.subprocess_calls))
        removed_subprocess = sorted(list(old_sig.subprocess_calls - new_sig.subprocess_calls))
        
        added_env = sorted(list(new_sig.env_vars_accessed - old_sig.env_vars_accessed))
        removed_env = sorted(list(old_sig.env_vars_accessed - new_sig.env_vars_accessed))
        
        added_cmd = sorted(list(new_sig.external_commands - old_sig.external_commands))
        removed_cmd = sorted(list(old_sig.external_commands - new_sig.external_commands))
        
        new_patterns = [p for p in new_sig.suspicious_patterns 
                       if p not in old_sig.suspicious_patterns]
        
        risk_score = self._calculate_risk_score(
            added_imports, added_network, added_files, added_subprocess,
            added_env, added_cmd, new_patterns
        )
        
        risk_level = self._assess_risk_level(risk_score)
        
        diff = BehaviorDiff(
            old_version=old_sig.version,
            new_version=new_sig.version,
            added_imports=added_imports,
            removed_imports=removed_imports,
            added_network_calls=added_network,
            removed_network_calls=removed_network,
            added_file_operations=added_files,
            removed_file_operations=removed_files,
            added_subprocess_calls=added_subprocess,
            removed_subprocess_calls=removed_subprocess,
            added_env_vars=added_env,
            removed_env_vars=removed_env,
            added_external_commands=added_cmd,
            removed_external_commands=removed_cmd,
            new_suspicious_patterns=new_patterns,
            risk_score=risk_score,
            risk_level=risk_level,
        )
        
        return diff
    
    def _calculate_risk_score(self, added_imports, added_network, added_files,
                             added_subprocess, added_env, added_cmd, new_patterns):
        """Calculate risk score based on behavioral changes."""
        score = 0.0
        
        score += len(added_imports) * self.RISK_WEIGHTS["added_imports"]
        score += len(added_network) * self.RISK_WEIGHTS["added_network_calls"]
        score += len(added_files) * self.RISK_WEIGHTS["added_file_operations"]
        score += len(added_subprocess) * self.RISK_WEIGHTS["added_subprocess_calls"]
        score += len(added_env) * self.RISK_WEIGHTS["added_env_vars"]
        score += len(added_cmd) * self.RISK_WEIGHTS["added_external_commands"]
        score += len(new_patterns) * self.RISK_WEIGHTS["new_suspicious_patterns"]
        
        return score
    
    def _assess_risk_level(self, score: float) -> str:
        """Assess risk level from score."""
        if score >= self.critical_threshold:
            return "CRITICAL"
        elif score >= self.warning_threshold:
            return "WARNING"
        else:
            return "LOW"


class SupplyChainMonitor:
    """Main monitor for OSS supply chain threats."""
    
    def __init__(self, output_file: str = None, warning_threshold: float = 20,
                 critical_threshold: float = 50):
        self.analyzer = BehaviorAnalyzer()
        self.diff_analyzer = BehaviorDiffAnalyzer(warning_threshold, critical_threshold)
        self.output_file = output_file
        self.signatures: Dict[str, Dict[str, BehaviorSignature]] = {}
        self.diffs: List[BehaviorDiff] = []
    
    def register_version(self, package_name: str, version: str, code: str):
        """Register a new package version with its code."""
        signature = self.analyzer.analyze_code(code, version)
        
        if package_name not in self.signatures:
            self.signatures[package_name] = {}
        
        self.signatures[package_name][version] = signature
    
    def analyze_update(self, package_name: str, old_version: str,
                      new_version: str) -> BehaviorDiff:
        """Analyze behavioral changes between versions."""
        if package_name not in self.signatures:
            raise ValueError(f"Package {package_name} not registered")
        
        if old_version not in self.signatures[package_name]:
            raise ValueError(f"Version {old_version} not found for {package_name}")
        
        if new_version not in self.signatures[package_name]:
            raise ValueError(f"Version {new_version} not found for {package_name}")
        
        old_sig = self.signatures[package_name][old_version]
        new_