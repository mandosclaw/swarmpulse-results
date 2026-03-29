#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-03-29T09:17:41.143Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Add tests and validation
MISSION: Founder of GitLab battles cancer by founding companies
AGENT: @aria (SwarmPulse)
DATE: 2024

This module implements comprehensive unit and integration tests for a 
company founding validation system, inspired by the founder's resilience 
in battling cancer while building companies.
"""

import unittest
import json
import argparse
import sys
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum


class CompanyStatus(Enum):
    """Company status enumeration."""
    FOUNDED = "founded"
    ACTIVE = "active"
    PIVOT = "pivot"
    ACQUIRED = "acquired"
    CLOSED = "closed"


@dataclass
class Company:
    """Company data model."""
    name: str
    founded_year: int
    status: str
    industry: str
    founders: List[str]
    employees: int = 1
    revenue_millions: Optional[float] = None
    description: str = ""

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate company data."""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("Company name cannot be empty")
        
        if self.founded_year < 1900 or self.founded_year > datetime.now().year:
            errors.append(f"Founded year must be between 1900 and {datetime.now().year}")
        
        if self.status not in [s.value for s in CompanyStatus]:
            errors.append(f"Status must be one of: {[s.value for s in CompanyStatus]}")
        
        if not self.industry or len(self.industry.strip()) == 0:
            errors.append("Industry cannot be empty")
        
        if not self.founders or len(self.founders) == 0:
            errors.append("At least one founder required")
        
        if self.employees < 1:
            errors.append("Employees must be at least 1")
        
        if self.revenue_millions is not None and self.revenue_millions < 0:
            errors.append("Revenue cannot be negative")
        
        return len(errors) == 0, errors


class CompanyValidator:
    """Validator for company data."""
    
    def __init__(self, strict_mode: bool = False):
        """Initialize validator."""
        self.strict_mode = strict_mode
        self.validation_results = []
    
    def validate_single(self, company: Company) -> Dict:
        """Validate a single company."""
        is_valid, errors = company.validate()
        result = {
            "company": company.name,
            "valid": is_valid,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results.append(result)
        return result
    
    def validate_batch(self, companies: List[Company]) -> Dict:
        """Validate multiple companies."""
        results = []
        valid_count = 0
        
        for company in companies:
            result = self.validate_single(company)
            results.append(result)
            if result["valid"]:
                valid_count += 1
        
        return {
            "total": len(companies),
            "valid": valid_count,
            "invalid": len(companies) - valid_count,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def validate_founder_consistency(self, companies: List[Company]) -> Dict:
        """Check founder consistency across companies."""
        founder_map = {}
        
        for company in companies:
            for founder in company.founders:
                if founder not in founder_map:
                    founder_map[founder] = []
                founder_map[founder].append(company.name)
        
        serial_founders = {f: cs for f, cs in founder_map.items() if len(cs) > 1}
        
        return {
            "total_unique_founders": len(founder_map),
            "serial_founders_count": len(serial_founders),
            "serial_founders": serial_founders,
            "timestamp": datetime.now().isoformat()
        }


class CompanyDataGenerator:
    """Generate sample company data for testing."""
    
    @staticmethod
    def create_valid_company(
        name: str = "TechStartup",
        year: int = 2023,
        founders: Optional[List[str]] = None
    ) -> Company:
        """Create a valid company instance."""
        if founders is None:
            founders = ["John Doe"]
        
        return Company(
            name=name,
            founded_year=year,
            status=CompanyStatus.ACTIVE.value,
            industry="Technology",
            founders=founders,
            employees=10,
            revenue_millions=5.5,
            description="A sample tech company"
        )
    
    @staticmethod
    def create_invalid_companies() -> List[Company]:
        """Create invalid company instances for testing."""
        invalid_companies = []
        
        # Empty name
        invalid_companies.append(Company(
            name="",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane Doe"]
        ))
        
        # Invalid year
        invalid_companies.append(Company(
            name="BadYear Corp",
            founded_year=2050,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane Doe"]
        ))
        
        # Invalid status
        invalid_companies.append(Company(
            name="BadStatus Inc",
            founded_year=2023,
            status="nonexistent_status",
            industry="Tech",
            founders=["Jane Doe"]
        ))
        
        # No founders
        invalid_companies.append(Company(
            name="NoFounders Ltd",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=[]
        ))
        
        # Negative employees
        invalid_companies.append(Company(
            name="NegativeEmp Corp",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane Doe"],
            employees=-5
        ))
        
        return invalid_companies


class TestCompanyModel(unittest.TestCase):
    """Test cases for Company model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = CompanyDataGenerator()
    
    def test_valid_company_creation(self):
        """Test creating a valid company."""
        company = self.generator.create_valid_company()
        self.assertIsNotNone(company)
        self.assertEqual(company.name, "TechStartup")
        self.assertEqual(company.founded_year, 2023)
    
    def test_valid_company_validation(self):
        """Test validation of a valid company."""
        company = self.generator.create_valid_company()
        is_valid, errors = company.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_company_with_multiple_founders(self):
        """Test company with multiple founders."""
        company = self.generator.create_valid_company(
            name="MultiFounder Inc",
            founders=["Alice", "Bob", "Charlie"]
        )
        is_valid, errors = company.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(company.founders), 3)
    
    def test_invalid_empty_name(self):
        """Test validation fails for empty name."""
        company = Company(
            name="",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane"]
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertIn("Company name cannot be empty", errors)
    
    def test_invalid_future_year(self):
        """Test validation fails for future founding year."""
        company = Company(
            name="FutureComp",
            founded_year=2050,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane"]
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Founded year" in e for e in errors))
    
    def test_invalid_status(self):
        """Test validation fails for invalid status."""
        company = Company(
            name="BadStatus",
            founded_year=2023,
            status="invalid_status",
            industry="Tech",
            founders=["Jane"]
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Status must be one of" in e for e in errors))
    
    def test_no_founders(self):
        """Test validation fails when no founders provided."""
        company = Company(
            name="NoFounders",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=[]
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertIn("At least one founder required", errors)
    
    def test_negative_employees(self):
        """Test validation fails for negative employees."""
        company = Company(
            name="NegativeEmp",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane"],
            employees=-5
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Employees must be at least 1" in e for e in errors))
    
    def test_negative_revenue(self):
        """Test validation fails for negative revenue."""
        company = Company(
            name="NegativeRev",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane"],
            revenue_millions=-10.0
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Revenue cannot be negative" in e for e in errors))


class TestCompanyValidator(unittest.TestCase):
    """Test cases for CompanyValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = CompanyValidator()
        self.generator = CompanyDataGenerator()
    
    def test_validate_single_valid_company(self):
        """Test validation of single valid company."""
        company = self.generator.create_valid_company()
        result = self.validator.validate_single(company)
        self.assertTrue(result["valid"])
        self.assertEqual(len(result["errors"]), 0)
    
    def test_validate_single_invalid_company(self):
        """Test validation of single invalid company."""
        company = Company(
            name="",
            founded_year=2023,
            status=CompanyStatus.ACTIVE.value,
            industry="Tech",
            founders=["Jane"]
        )
        result = self.validator.validate_single(company)
        self.assertFalse(result["valid"])
        self.assertGreater(len(result["errors"]), 0)
    
    def test_validate_batch_mixed(self):
        """Test batch validation with mixed valid/invalid companies."""
        companies = [
            self.generator.create_valid_company(name="Company A"),
            self.generator.create_valid_company(name="Company B"),
            Company(name="", founded_year=2023, status=CompanyStatus.ACTIVE.value, 
                   industry="Tech", founders=["Jane"])
        ]
        
        result = self.validator.validate_batch(companies)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["valid"], 2)
        self.assertEqual(result["invalid"], 1)
    
    def test_founder_consistency_serial_founder(self):
        """Test identification of serial founders."""
        companies = [
            self.generator.create_valid_company(
                name="Company A", founders=["Sytse Sijbrandij"]
            ),
            self.generator.create_valid_company(
                name="Company B", founders=["Sytse Sijbrandij", "Co-founder"]
            ),
            self.generator.create_valid_company(
                name="Company C", founders=["Other Founder"]
            )
        ]
        
        result = self.validator.validate_founder_consistency(companies)
        self.assertEqual(result["total_unique_founders"], 3)
        self.assertEqual(result["serial_founders_count"], 1)
        self.assertIn("Sytse Sijbrandij", result["serial_founders"])
        self.assertEqual(len(result["serial_founders"]["Sytse Sijbrandij"]), 2)
    
    def test_validation_results_tracking(self):
        """Test that validation results are tracked."""
        companies = [
            self.generator.create_valid_company(name="Company A"),
            self.generator.create_valid_company(name="Company B")
        ]
        
        self.validator.validate_batch(companies)
        self.assertEqual(len(self.validator.validation_results), 2)


class TestDataGeneration(unittest.TestCase):
    """Test cases for test data generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = CompanyDataGenerator()
    
    def test_generate_valid_company(self):
        """Test generating valid company."""
        company = self.generator.create_valid_company()
        is_valid, errors = company.validate()
        self.assertTrue(is_valid)
    
    def test_generate_invalid_companies(self):
        """Test generating invalid companies."""
        invalid = self.generator.create_invalid_companies()
        self.assertEqual(len(invalid), 5)
        
        for company in invalid:
            is_valid, errors = company.validate()
            self.assertFalse(is_valid)
            self.assertGreater(len(errors), 0)
    
    def test_generate_custom_company(self):
        """Test generating company with custom parameters."""
        company = self.generator.create_valid_company(
            name="CustomCorp",
            year=2020,
            founders=["Founder1", "Founder2"]
        )
        self.assertEqual(company.name, "CustomCorp")
        self.assertEqual(company.founded_year, 2020)
        self.assertEqual(len(company.founders), 2)


class TestIntegration(unittest.TestCase):
    """Integration tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = CompanyValidator()
        self.generator = CompanyDataGenerator()
    
    def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        companies = [
            self.generator.create_valid_company(
                name="GitLab",
                year=2013,
                founders=["Sytse Sijbrandij", "Dmitriy Zaporozhets"]
            ),
            self.generator.create_valid_company(
                name="Gittab",
                year=2023,
                founders=["Sytse Sijbrandij"]
            ),
            self.generator.create_valid_company(
                name="HealthTech",
                year=2022,
                founders=["Jane Researcher"]
            )
        ]
        
        # Validate all companies
        batch_result = self.validator.validate_batch(companies)
        self.assertEqual(batch_result["valid"], 3)
        
        # Check founder patterns
        founder_result = self.validator.validate_founder_consistency(companies)
        self.assertEqual(founder_result["serial_founders_count"], 1)
        self.assertIn("Sytse Sijbrandij", founder_result["serial_founders"])
    
    def test_json_serialization(self):
        """Test JSON