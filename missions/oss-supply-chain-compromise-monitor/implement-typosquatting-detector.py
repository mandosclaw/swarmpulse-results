#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement typosquatting detector
# Mission: OSS Supply Chain Compromise Monitor
# Agent:   @dex
# Date:    2026-03-28T22:05:23.606Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement typosquatting detector
MISSION: OSS Supply Chain Compromise Monitor
AGENT: @dex
DATE: 2024

Typosquatting detector for open-source packages with similarity analysis,
behavioral diffing, and registry stream monitoring capabilities.
"""

import argparse
import json
import sys
import re
import difflib
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import urllib.request
import urllib.error


class TyposquattingDetector:
    """Detects potential typosquatting attacks in OSS packages."""
    
    COMMON_TYPOS = {
        'a': ['e', 'o', 's'],
        'e': ['a', 'i', 'o'],
        'i': ['e', 'o', 'u'],
        'o': ['a', 'e', 'i', 'u'],
        'u': ['o', 'i'],
        'l': ['1', 'i'],
        '1': ['l', 'i'],
        '0': ['o'],
        's': ['z', 'c'],
    }
    
    KEYBOARD_NEIGHBORS = {
        'a': ['q', 'w', 's', 'z'],
        'b': ['v', 'g', 'h', 'n'],
        'c': ['x', 'd', 'f', 'v'],
        'd': ['s', 'e', 'r', 'f', 'x', 'c'],
        'e': ['w', 'r', 'd', 's'],
        'f': ['d', 'r', 't', 'g', 'c', 'v'],
        'g': ['f', 't', 'y', 'h', 'v', 'b'],
        'h': ['g', 'y', 'u', 'j', 'b', 'n'],
        'i': ['u', 'o', 'k', 'l'],
        'j': ['h', 'u', 'i', 'k', 'n', 'm'],
        'k': ['j', 'i', 'o', 'l', 'm'],
        'l': ['k', 'o', 'p'],
        'm': ['n', 'j', 'k'],
        'n': ['b', 'h', 'j', 'm'],
        'o': ['i', 'p', 'k', 'l'],
        'p': ['o', 'l'],
        'q': ['w', 'a'],
        'r': ['e', 't', 'f', 'd'],
        's': ['a', 'w', 'e', 'd', 'x', 'z'],
        't': ['r', 'y', 'g', 'f'],
        'u': ['y', 'i', 'j', 'k'],
        'v': ['c', 'f', 'g', 'b'],
        'w': ['q', 'e', 's', 'a'],
        'x': ['z', 's', 'd', 'c'],
        'y': ['t', 'u', 'h', 'g'],
        'z': ['a', 's', 'x'],
    }
    
    def __init__(self, legitimate_packages: List[str] = None, 
                 similarity_threshold: float = 0.75,
                 max_edit_distance: int = 3):
        """
        Initialize the typosquatting detector.
        
        Args:
            legitimate_packages: List of known legitimate package names
            similarity_threshold: Minimum similarity score (0-1) to flag as suspicious
            max_edit_distance: Maximum edit distance to consider as potential typo
        """
        self.legitimate_packages = set(legitimate_packages or [])
        self.similarity_threshold = similarity_threshold
        self.max_edit_distance = max_edit_distance
        self.detection_cache = {}
    
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def sequence_matcher_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity ratio using SequenceMatcher."""
        return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
    
    def is_keyboard_typo(self, legitimate: str, suspicious: str) -> bool:
        """Check if suspicious name could be a keyboard typo of legitimate name."""
        if len(legitimate) != len(suspicious):
            return False
        
        changes = 0
        for i, (c1, c2) in enumerate(zip(legitimate.lower(), suspicious.lower())):
            if c1 != c2:
                changes += 1
                if c2 not in self.KEYBOARD_NEIGHBORS.get(c1, []):
                    return False
                if changes > 1:
                    return False
        
        return changes == 1
    
    def is_vowel_swap(self, legitimate: str, suspicious: str) -> bool:
        """Check if names differ only by vowel substitution."""
        if len(legitimate) != len(suspicious):
            return False
        
        vowels = set('aeiou')
        differences = 0
        
        for c1, c2 in zip(legitimate.lower(), suspicious.lower()):
            if c1 != c2:
                differences += 1
                if not (c1 in vowels and c2 in vowels):
                    return False
                if differences > 2:
                    return False
        
        return differences > 0
    
    def is_character_swap(self, legitimate: str, suspicious: str) -> bool:
        """Check if names differ by adjacent character swap."""
        if len(legitimate) != len(suspicious):
            return False
        
        for i in range(len(legitimate) - 1):
            if (legitimate[i:i+2] == suspicious[i+1:i-1:-1] and
                legitimate[:i] == suspicious[:i] and
                legitimate[i+2:] == suspicious[i+2:]):
                return True
        
        return False
    
    def is_missing_character(self, legitimate: str, suspicious: str) -> bool:
        """Check if suspicious is legitimate with one character removed."""
        if len(legitimate) - len(suspicious) != 1:
            return False
        
        for i in range(len(legitimate)):
            if legitimate[:i] + legitimate[i+1:] == suspicious:
                return True
        
        return False
    
    def is_extra_character(self, legitimate: str, suspicious: str) -> bool:
        """Check if suspicious is legitimate with one extra character."""
        return self.is_missing_character(suspicious, legitimate)
    
    def is_homograph_attack(self, legitimate: str, suspicious: str) -> bool:
        """Check for homograph attacks using lookalike characters."""
        lookalikes = {
            'l': ['1', 'i', '|'],
            '0': ['o'],
            '1': ['l', 'i'],