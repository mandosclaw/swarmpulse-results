#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: vladartym/always-fit-resume: A resume builder that auto-scales font size and line spacing to always fit on one page. Pow
# Agent:   @aria
# Date:    2026-03-30T10:43:01.509Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for always-fit-resume
Mission: vladartym/always-fit-resume - Resume builder with auto-scaling font
Category: Engineering
Agent: @aria (SwarmPulse)
Date: 2024
"""

import argparse
import json
import sys
import unittest
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from typing import Dict, List, Optional, Tuple


class ValidationLevel(Enum):
    STRICT = "strict"
    NORMAL = "normal"
    RELAXED = "relaxed"


@dataclass
class TextMetrics:
    width: float
    height: float
    line_count: int
    character_count: int


class FontScalingValidator:
    """Validates font scaling logic for resume content."""
    
    def __init__(self, page_width: float = 8.5, page_height: float = 11.0,
                 margin: float = 0.5, validation_level: str = "normal"):
        self.page_width = page_width
        self.page_height = page_height
        self.margin = margin
        self.content_width = page_width - (2 * margin)
        self.content_height = page_height - (2 * margin)
        self.validation_level = ValidationLevel(validation_level)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_content_fits(self, text: str, font_size: float, 
                            line_spacing: float) -> bool:
        """Check if content fits on single page with given font size and spacing."""
        if not text or not text.strip():
            self.errors.append("Content is empty")
            return False
        
        lines = text.split('\n')
        calculated_height = self._calculate_height(len(lines), font_size, line_spacing)
        
        if calculated_height > self.content_height:
            self.errors.append(
                f"Content height {calculated_height:.2f}in exceeds "
                f"available {self.content_height:.2f}in"
            )
            return False
        
        max_line_width = max(len(line) for line in lines)
        if max_line_width * (font_size * 0.6) > self.content_width:
            self.errors.append(
                f"Longest line exceeds page width at font size {font_size}pt"
            )
            return False
        
        return True
    
    def _calculate_height(self, line_count: int, font_size: float, 
                         line_spacing: float) -> float:
        """Calculate total height needed for content."""
        line_height = font_size * line_spacing / 72.0
        return line_count * line_height
    
    def find_optimal_scaling(self, text: str, initial_font_size: float = 12,
                           initial_line_spacing: float = 1.5) -> Tuple[float, float]:
        """Find optimal font size and line spacing to fit content."""
        if not text or not text.strip():
            self.errors.append("Cannot scale empty content")
            return initial_font_size, initial_line_spacing
        
        font_size = initial_font_size
        line_spacing = initial_line_spacing
        lines = text.split('\n')
        
        max_iterations = 100
        iteration = 0
        
        while iteration < max_iterations:
            if self.validate_content_fits(text, font_size, line_spacing):
                return font_size, line_spacing
            
            if font_size < 6:
                self.errors.append(
                    f"Cannot fit content even at minimum font size 6pt"
                )
                return font_size, line_spacing
            
            font_size -= 0.5
            line_spacing = max(1.0, line_spacing - 0.05)
            iteration += 1
        
        self.warnings.append(
            f"Reached maximum iterations ({max_iterations}) while scaling"
        )
        return font_size, line_spacing
    
    def validate_structure(self, resume_dict: Dict) -> bool:
        """Validate resume structure and content."""
        required_fields = ["name", "content"]
        
        for field in required_fields:
            if field not in resume_dict:
                self.errors.append(f"Missing required field: {field}")
                return False
        
        if not isinstance(resume_dict["name"], str) or not resume_dict["name"].strip():
            self.errors.append("Name must be a non-empty string")
            return False
        
        if not isinstance(resume_dict["content"], str):
            self.errors.append("Content must be a string")
            return False
        
        if self.validation_level == ValidationLevel.STRICT:
            if len(resume_dict["name"]) > 100:
                self.errors.append("Name exceeds 100 characters")
                return False
            
            if len(resume_dict["content"]) > 50000:
                self.errors.append("Content exceeds 50000 characters")
                return False
        
        return True
    
    def measure_text(self, text: str) -> TextMetrics:
        """Estimate text metrics for given content."""
        if not text:
            return TextMetrics(0.0, 0.0, 0, 0)
        
        lines = text.split('\n')
        max_chars = max(len(line) for line in lines) if lines else 0
        total_chars = len(text)
        
        estimated_width = max_chars * 0.6
        estimated_height = len(lines) * 0.25
        
        return TextMetrics(
            width=estimated_width,
            height=estimated_height,
            line_count=len(lines),
            character_count=total_chars
        )
    
    def clear_errors(self):
        """Clear error and warning lists."""
        self.errors = []
        self.warnings = []
    
    def get_report(self) -> Dict:
        """Get validation report as dictionary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "is_valid": len(self.errors) == 0,
            "page_dimensions": {
                "width": self.page_width,
                "height": self.page_height,
                "margin": self.margin,
                "content_width": self.content_width,
                "content_height": self.content_height
            },
            "validation_level": self.validation_level.value
        }


class TestFontScalingValidator(unittest.TestCase):
    """Unit tests for FontScalingValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = FontScalingValidator()
    
    def test_validate_content_fits_basic(self):
        """Test basic content fitting validation."""
        text = "John Doe\nSoftware Engineer\n\nExperience:\nCompany A - 2020-2024"
        result = self.validator.validate_content_fits(text, 12, 1.5)
        self.assertTrue(result)
    
    def test_validate_content_fits_overflow(self):
        """Test validation when content overflows."""
        long_text = "x" * 1000 + "\n" * 100
        result = self.validator.validate_content_fits(long_text, 12, 1.5)
        self.assertFalse(result)
        self.assertTrue(len(self.validator.errors) > 0)
    
    def test_validate_content_fits_empty(self):
        """Test validation of empty content."""
        self.validator.clear_errors()
        result = self.validator.validate_content_fits("", 12, 1.5)
        self.assertFalse(result)
        self.assertIn("empty", self.validator.errors[0].lower())
    
    def test_find_optimal_scaling(self):
        """Test finding optimal font and line spacing."""
        text = "Name\n" + "Experience\n" * 15
        font_size, line_spacing = self.validator.find_optimal_scaling(text)
        self.assertGreater(font_size, 0)
        self.assertGreater(line_spacing, 0)
        self.assertLessEqual(font_size, 12)
    
    def test_validate_structure_valid(self):
        """Test structure validation with valid resume."""
        resume = {
            "name": "John Doe",
            "content": "Software Engineer with 5 years experience"
        }
        result = self.validator.validate_structure(resume)
        self.assertTrue(result)
    
    def test_validate_structure_missing_name(self):
        """Test structure validation with missing name."""
        self.validator.clear_errors()
        resume = {"content": "Some content"}
        result = self.validator.validate_structure(resume)
        self.assertFalse(result)
        self.assertIn("name", self.validator.errors[0].lower())
    
    def test_validate_structure_missing_content(self):
        """Test structure validation with missing content."""
        self.validator.clear_errors()
        resume = {"name": "John Doe"}
        result = self.validator.validate_structure(resume)
        self.assertFalse(result)
        self.assertIn("content", self.validator.errors[0].lower())
    
    def test_validate_structure_empty_name(self):
        """Test structure validation with empty name."""
        self.validator.clear_errors()
        resume = {"name": "", "content": "Content"}
        result = self.validator.validate_structure(resume)
        self.assertFalse(result)
    
    def test_measure_text(self):
        """Test text measurement."""
        text = "Line 1\nLine 2\nLine 3"
        metrics = self.validator.measure_text(text)
        self.assertEqual(metrics.line_count, 3)
        self.assertGreater(metrics.character_count, 0)
        self.assertGreater(metrics.width, 0)
    
    def test_measure_text_empty(self):
        """Test text measurement with empty string."""
        metrics = self.validator.measure_text("")
        self.assertEqual(metrics.line_count, 0)
        self.assertEqual(metrics.character_count, 0)
        self.assertEqual(metrics.width, 0.0)
    
    def test_get_report(self):
        """Test report generation."""
        self.validator.clear_errors()
        self.validator.errors.append("Test error")
        report = self.validator.get_report()
        self.assertFalse(report["is_valid"])
        self.assertEqual(len(report["errors"]), 1)
        self.assertIn("page_dimensions", report)
    
    def test_calculate_height(self):
        """Test height calculation."""
        height = self.validator._calculate_height(10, 12, 1.5)
        self.assertGreater(height, 0)
        self.assertLess(height, self.validator.content_height)
    
    def test_validation_level_strict(self):
        """Test strict validation level."""
        strict_validator = FontScalingValidator(validation_level="strict")
        resume = {
            "name": "x" * 101,
            "content": "Test content"
        }
        result = strict_validator.validate_structure(resume)
        self.assertFalse(result)
    
    def test_validation_level_relaxed(self):
        """Test relaxed validation level."""
        relaxed_validator = FontScalingValidator(validation_level="relaxed")
        resume = {
            "name": "x" * 101,
            "content": "Test content"
        }
        result = relaxed_validator.validate_structure(resume)
        self.assertTrue(result)


class ResumeValidator:
    """High-level resume validation and scaling orchestrator."""
    
    def __init__(self, validation_level: str = "normal"):
        self.validator = FontScalingValidator(validation_level=validation_level)
        self.results: List[Dict] = []
    
    def validate_and_scale(self, resume_dict: Dict) -> Dict:
        """Validate resume structure and find optimal scaling."""
        self.validator.clear_errors()
        
        result = {
            "resume_name": resume_dict.get("name", "Unknown"),
            "structure_valid": False,
            "scaling_optimal": False,
            "font_size": 12,
            "line_spacing": 1.5,
            "metrics": None,
            "validation_report": None
        }
        
        if not self.validator.validate_structure(resume_dict):
            result["validation_report"] = self.validator.get_report()
            self.results.append(result)
            return result
        
        result["structure_valid"] = True
        
        content = resume_dict.get("content", "")
        metrics = self.validator.measure_text(content)
        result["metrics"] = {
            "lines": metrics.line_count,
            "characters": metrics.character_count,
            "width": metrics.width,
            "height": metrics.height
        }
        
        font_size, line_spacing = self.validator.find_optimal_scaling(content)
        result["font_size"] = font_size
        result["line_spacing"] = line_spacing
        result["scaling_optimal"] = len(self.validator.errors) == 0
        result["validation_report"] = self.validator.get_report()
        
        self.results.append(result)
        return result
    
    def get_summary(self) -> Dict:
        """Get validation summary for all processed resumes."""
        total = len(self.results)
        valid_structures = sum(1 for r in self.results if r["structure_valid"])
        optimal_scaling = sum(1 for r in self.results if r["scaling_optimal"])
        
        return {
            "total_resumes": total,
            "valid_structures": valid_structures,
            "optimal_scaling": optimal_scaling,
            "success_rate": valid_structures / total if total > 0 else 0,
            "results": self.results
        }


class TestResumeValidator(unittest.TestCase):
    """Integration tests for ResumeValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = ResumeValidator()
    
    def test_validate_and_scale_valid_resume(self):
        """Test validation and scaling of valid resume."""
        resume = {
            "name": "Jane Smith",
            "content": "Senior Developer\n\nExperience:\nCompany A (2020-2024)\nCompany B (2018-2020)"
        }
        result = self.validator.validate_and_scale(resume)
        self.assertTrue(result["structure_valid"])
        self.assertGreater(result["font_size"], 0)
        self.assertGreater(result["line_spacing"], 0)
    
    def test_validate_and_scale_invalid_resume(self):
        """Test validation of invalid resume."""
        resume = {"content": "Missing name field"}
        result = self.validator.validate_and_scale(resume)
        self.assertFalse(result["structure_valid"])
    
    def test_validate_and_scale_multiple(self):
        """Test validation of multiple resumes."""
        resumes = [
            {
                "name": "John Doe",
                "content": "Developer\nExperience at Company A"
            },
            {
                "name": "Jane Smith",
                "content": "Designer\nExperience at Company B"
            }
        ]
        for resume in resumes:
            self.validator.validate_and_scale(resume)
        
        summary = self.validator.get_summary()
        self.assertEqual(summary["total_resumes"], 2)
        self.assertGreaterEqual(summary["valid_structures"], 1)
    
    def test_get_summary(self):
        """Test summary generation."""
        resume = {
            "name": "Test User",
            "content": "Test content"
        }
        self.validator.validate_and_scale(resume)
        summary = self.validator.get_summary()