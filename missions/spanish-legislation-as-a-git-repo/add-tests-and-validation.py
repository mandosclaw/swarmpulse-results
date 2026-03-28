#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-28T22:24:42.635Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for Spanish legislation Git repo
Mission: Spanish legislation as a Git repo
Agent: @aria (SwarmPulse network)
Date: 2025-01-20
"""

import unittest
import json
import tempfile
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import argparse


class SpanishLegislationValidator:
    """Validates Spanish legislation documents and Git repository structure."""
    
    VALID_DOCUMENT_TYPES = {
        'ley': 'Ley (Law)',
        'real_decreto': 'Real Decreto (Royal Decree)',
        'orden': 'Orden (Order)',
        'circular': 'Circular',
        'resolucion': 'Resolución (Resolution)',
        'decreto': 'Decreto (Decree)'
    }
    
    VALID_STATUSES = ['vigente', 'derogada', 'modificada', 'en_trámite']
    
    def __init__(self):
        self.validation_results = []
        self.errors = []
        self.warnings = []
    
    def validate_document_structure(self, doc: Dict[str, Any]) -> bool:
        """Validate a Spanish legislation document structure."""
        required_fields = ['id', 'titulo', 'tipo', 'estado', 'fecha_publicacion']
        
        for field in required_fields:
            if field not in doc:
                self.errors.append(f"Missing required field: {field}")
                return False
        
        if not isinstance(doc['id'], str) or not doc['id'].strip():
            self.errors.append("ID must be a non-empty string")
            return False
        
        if not re.match(r'^[A-Z]{1,3}-\d{4}-\d{1,5}$', doc['id']):
            self.warnings.append(f"ID '{doc['id']}' does not match expected format")
        
        if doc['tipo'] not in self.VALID_DOCUMENT_TYPES:
            self.errors.append(f"Invalid document type: {doc['tipo']}")
            return False
        
        if doc['estado'] not in self.VALID_STATUSES:
            self.errors.append(f"Invalid status: {doc['estado']}")
            return False
        
        return True
    
    def validate_date_format(self, date_string: str) -> bool:
        """Validate date format (YYYY-MM-DD)."""
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            self.errors.append(f"Invalid date format: {date_string}")
            return False
    
    def validate_article_numbering(self, articles: List[Dict[str, Any]]) -> bool:
        """Validate that articles are numbered sequentially."""
        if not articles:
            return True
        
        expected_numbers = set(range(1, len(articles) + 1))
        actual_numbers = set()
        
        for article in articles:
            if 'numero' not in article:
                self.errors.append("Article missing 'numero' field")
                return False
            actual_numbers.add(article['numero'])
        
        if expected_numbers != actual_numbers:
            missing = expected_numbers - actual_numbers
            extra = actual_numbers - expected_numbers
            if missing:
                self.warnings.append(f"Missing article numbers: {missing}")
            if extra:
                self.warnings.append(f"Extra article numbers: {extra}")
            return False
        
        return True
    
    def validate_references(self, doc: Dict[str, Any]) -> bool:
        """Validate that referenced documents exist in cross-references."""
        if 'referencias' not in doc:
            return True
        
        if not isinstance(doc['referencias'], list):
            self.errors.append("Referencias must be a list")
            return False
        
        for ref in doc['referencias']:
            if not isinstance(ref, dict) or 'id' not in ref:
                self.errors.append("Invalid reference structure")
                return False
        
        return True
    
    def validate_repo_structure(self, repo_path: str) -> bool:
        """Validate the repository structure."""
        required_dirs = ['.git', 'docs', 'leyes']
        repo = Path(repo_path)
        
        if not repo.exists():
            self.errors.append(f"Repository path does not exist: {repo_path}")
            return False
        
        for required_dir in required_dirs:
            dir_path = repo / required_dir
            if not dir_path.exists():
                self.warnings.append(f"Expected directory not found: {required_dir}")
        
        return len(self.errors) == 0
    
    def clear(self):
        """Clear validation results."""
        self.validation_results = []
        self.errors = []
        self.warnings = []


class SpanishLegislationTests(unittest.TestCase):
    """Unit tests for Spanish legislation validation."""
    
    def setUp(self):
        self.validator = SpanishLegislationValidator()
    
    def tearDown(self):
        self.validator.clear()
    
    def test_valid_document_structure(self):
        """Test validation of a valid document structure."""
        doc = {
            'id': 'LOO-2023-00001',
            'titulo': 'Ley Orgánica de Transparencia',
            'tipo': 'ley',
            'estado': 'vigente',
            'fecha_publicacion': '2023-01-15',
            'referencias': []
        }
        result = self.validator.validate_document_structure(doc)
        self.assertTrue(result)
        self.assertEqual(len(self.validator.errors), 0)
    
    def test_missing_required_field(self):
        """Test validation fails with missing required field."""
        doc = {
            'id': 'LOO-2023-00001',
            'tipo': 'ley',
            'estado': 'vigente'
        }
        result = self.validator.validate_document_structure(doc)
        self.assertFalse(result)
        self.assertGreater(len(self.validator.errors), 0)
    
    def test_invalid_document_type(self):
        """Test validation fails with invalid document type."""
        doc = {
            'id': 'LOO-2023-00001',
            'titulo': 'Test Law',
            'tipo': 'invalid_type',
            'estado': 'vigente',
            'fecha_publicacion': '2023-01-15'
        }
        result = self.validator.validate_document_structure(doc)
        self.assertFalse(result)
    
    def test_invalid_status(self):
        """Test validation fails with invalid status."""
        doc = {
            'id': 'LOO-2023-00001',
            'titulo': 'Test Law',
            'tipo': 'ley',
            'estado': 'invalid_status',
            'fecha_publicacion': '2023-01-15'
        }
        result = self.validator.validate_document_structure(doc)
        self.assertFalse(result)
    
    def test_valid_date_format(self):
        """Test validation of valid date format."""
        result = self.validator.validate_date_format('2023-01-15')
        self.assertTrue(result)
    
    def test_invalid_date_format(self):
        """Test validation fails with invalid date format."""
        result = self.validator.validate_date_format('15/01/2023')
        self.assertFalse(result)
        self.assertGreater(len(self.validator.errors), 0)
    
    def test_sequential_article_numbering(self):
        """Test validation of sequential article numbering."""
        articles = [
            {'numero': 1,