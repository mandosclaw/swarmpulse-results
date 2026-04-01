#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-04-01T17:18:43.193Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Add tests and validation for GitLab founder's cancer-fighting company initiatives
MISSION: Founder of GitLab battles cancer by founding companies
AGENT: @aria in SwarmPulse network
DATE: 2024
CATEGORY: Engineering

This module provides unit and integration tests covering scenarios related to
validating company information, health initiative tracking, and data integrity.
"""

import unittest
import json
import sys
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple
from abc import ABC, abstractmethod


class CompanyType(Enum):
    """Types of companies founded"""
    HEALTHCARE = "healthcare"
    CANCER_RESEARCH = "cancer_research"
    BIOTECH = "biotech"
    TECHNOLOGY = "technology"
    PHARMACEUTICAL = "pharmaceutical"


@dataclass
class Company:
    """Represents a company founded"""
    name: str
    founded_year: int
    company_type: CompanyType
    mission: str
    employees: int
    funding_usd: float
    is_active: bool
    cancer_focused: bool

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate company data"""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("Company name cannot be empty")
        
        if self.founded_year < 1900 or self.founded_year > datetime.now().year:
            errors.append(f"Founded year {self.founded_year} is invalid")
        
        if self.employees < 0:
            errors.append("Employee count cannot be negative")
        
        if self.funding_usd < 0:
            errors.append("Funding amount cannot be negative")
        
        if self.cancer_focused and self.company_type not in [
            CompanyType.CANCER_RESEARCH,
            CompanyType.BIOTECH,
            CompanyType.PHARMACEUTICAL,
            CompanyType.HEALTHCARE
        ]:
            errors.append("Cancer-focused company should have relevant type")
        
        return len(errors) == 0, errors

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['company_type'] = self.company_type.value
        return data


@dataclass
class Founder:
    """Represents a founder"""
    name: str
    primary_company: str
    companies_founded: List[str]
    cancer_initiative: bool
    years_active: int

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate founder data"""
        errors = []
        
        if not self.name or len(self.name.strip()) == 0:
            errors.append("Founder name cannot be empty")
        
        if not self.primary_company:
            errors.append("Primary company must be specified")
        
        if not isinstance(self.companies_founded, list):
            errors.append("Companies founded must be a list")
        
        if self.years_active < 0 or self.years_active > 100:
            errors.append("Years active must be between 0 and 100")
        
        if self.cancer_initiative and len(self.companies_founded) < 1:
            errors.append("Cancer initiative founder must have founded at least one company")
        
        return len(errors) == 0, errors

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class CompanyRegistry:
    """Registry for managing companies"""
    
    def __init__(self):
        self.companies: Dict[str, Company] = {}
    
    def add_company(self, company: Company) -> Tuple[bool, str]:
        """Add a company to registry"""
        is_valid, errors = company.validate()
        
        if not is_valid:
            return False, f"Validation failed: {'; '.join(errors)}"
        
        if company.name in self.companies:
            return False, f"Company '{company.name}' already exists"
        
        self.companies[company.name] = company
        return True, f"Company '{company.name}' added successfully"
    
    def get_company(self, name: str) -> Optional[Company]:
        """Get company by name"""
        return self.companies.get(name)
    
    def remove_company(self, name: str) -> Tuple[bool, str]:
        """Remove company from registry"""
        if name not in self.companies:
            return False, f"Company '{name}' not found"
        
        del self.companies[name]
        return True, f"Company '{name}' removed successfully"
    
    def get_cancer_focused_companies(self) -> List[Company]:
        """Get all cancer-focused companies"""
        return [c for c in self.companies.values() if c.cancer_focused]
    
    def get_companies_by_type(self, company_type: CompanyType) -> List[Company]:
        """Get companies by type"""
        return [c for c in self.companies.values() if c.company_type == company_type]
    
    def get_total_funding(self) -> float:
        """Get total funding across all companies"""
        return sum(c.funding_usd for c in self.companies.values())
    
    def get_total_employees(self) -> int:
        """Get total employees across all companies"""
        return sum(c.employees for c in self.companies.values())
    
    def list_all(self) -> List[Dict]:
        """List all companies"""
        return [c.to_dict() for c in self.companies.values()]
    
    def health_check(self) -> Dict:
        """Perform registry health check"""
        return {
            'total_companies': len(self.companies),
            'cancer_focused_count': len(self.get_cancer_focused_companies()),
            'total_funding_usd': self.get_total_funding(),
            'total_employees': self.get_total_employees(),
            'active_companies': sum(1 for c in self.companies.values() if c.is_active),
            'timestamp': datetime.now().isoformat()
        }


class FounderRegistry:
    """Registry for managing founders"""
    
    def __init__(self):
        self.founders: Dict[str, Founder] = {}
    
    def add_founder(self, founder: Founder) -> Tuple[bool, str]:
        """Add a founder to registry"""
        is_valid, errors = founder.validate()
        
        if not is_valid:
            return False, f"Validation failed: {'; '.join(errors)}"
        
        if founder.name in self.founders:
            return False, f"Founder '{founder.name}' already exists"
        
        self.founders[founder.name] = founder
        return True, f"Founder '{founder.name}' added successfully"
    
    def get_founder(self, name: str) -> Optional[Founder]:
        """Get founder by name"""
        return self.founders.get(name)
    
    def get_cancer_initiative_founders(self) -> List[Founder]:
        """Get all founders with cancer initiatives"""
        return [f for f in self.founders.values() if f.cancer_initiative]
    
    def list_all(self) -> List[Dict]:
        """List all founders"""
        return [f.to_dict() for f in self.founders.values()]


class TestCompanyValidation(unittest.TestCase):
    """Test company validation"""
    
    def test_valid_company(self):
        """Test creating a valid company"""
        company = Company(
            name="CancerTech Inc",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Advancing cancer research through technology",
            employees=50,
            funding_usd=5000000,
            is_active=True,
            cancer_focused=True
        )
        is_valid, errors = company.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_company_empty_name(self):
        """Test company with empty name"""
        company = Company(
            name="",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Mission",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=True
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("name" in e.lower() for e in errors))
    
    def test_company_invalid_year(self):
        """Test company with invalid founded year"""
        company = Company(
            name="TestCorp",
            founded_year=2050,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("year" in e.lower() for e in errors))
    
    def test_company_negative_employees(self):
        """Test company with negative employees"""
        company = Company(
            name="BadCorp",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=-5,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("employee" in e.lower() for e in errors))
    
    def test_company_negative_funding(self):
        """Test company with negative funding"""
        company = Company(
            name="BadFunding",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=10,
            funding_usd=-1000000,
            is_active=True,
            cancer_focused=False
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("funding" in e.lower() for e in errors))
    
    def test_cancer_focused_type_mismatch(self):
        """Test cancer-focused company with wrong type"""
        company = Company(
            name="WrongType",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=True
        )
        is_valid, errors = company.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("type" in e.lower() for e in errors))


class TestFounderValidation(unittest.TestCase):
    """Test founder validation"""
    
    def test_valid_founder(self):
        """Test creating a valid founder"""
        founder = Founder(
            name="John Doe",
            primary_company="GitLab",
            companies_founded=["GitLab", "CancerTech"],
            cancer_initiative=True,
            years_active=20
        )
        is_valid, errors = founder.validate()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_founder_empty_name(self):
        """Test founder with empty name"""
        founder = Founder(
            name="",
            primary_company="Company",
            companies_founded=["Company"],
            cancer_initiative=False,
            years_active=10
        )
        is_valid, errors = founder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("name" in e.lower() for e in errors))
    
    def test_founder_no_primary_company(self):
        """Test founder without primary company"""
        founder = Founder(
            name="Test",
            primary_company="",
            companies_founded=["Company"],
            cancer_initiative=False,
            years_active=10
        )
        is_valid, errors = founder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("primary" in e.lower() for e in errors))
    
    def test_founder_invalid_years_active(self):
        """Test founder with invalid years active"""
        founder = Founder(
            name="Test",
            primary_company="Company",
            companies_founded=["Company"],
            cancer_initiative=False,
            years_active=150
        )
        is_valid, errors = founder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("years" in e.lower() for e in errors))
    
    def test_cancer_initiative_no_companies(self):
        """Test cancer initiative founder with no companies"""
        founder = Founder(
            name="Test",
            primary_company="Company",
            companies_founded=[],
            cancer_initiative=True,
            years_active=10
        )
        is_valid, errors = founder.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("cancer" in e.lower() or "founded" in e.lower() for e in errors))


class TestCompanyRegistry(unittest.TestCase):
    """Test company registry operations"""
    
    def setUp(self):
        """Set up test registry"""
        self.registry = CompanyRegistry()
    
    def test_add_valid_company(self):
        """Test adding a valid company"""
        company = Company(
            name="TestCorp",
            founded_year=2020,
            company_type=CompanyType.HEALTHCARE,
            mission="Healthcare",
            employees=50,
            funding_usd=5000000,
            is_active=True,
            cancer_focused=False
        )
        success, message = self.registry.add_company(company)
        self.assertTrue(success)
        self.assertIn("added successfully", message)
        self.assertEqual(len(self.registry.companies), 1)
    
    def test_add_duplicate_company(self):
        """Test adding duplicate company"""
        company = Company(
            name="Duplicate",
            founded_year=2020,
            company_type=CompanyType.HEALTHCARE,
            mission="Test",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company)
        success, message = self.registry.add_company(company)
        self.assertFalse(success)
        self.assertIn("already exists", message)
    
    def test_get_company(self):
        """Test retrieving a company"""
        company = Company(
            name="GetTest",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company)
        retrieved = self.registry.get_company("GetTest")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "GetTest")
    
    def test_remove_company(self):
        """Test removing a company"""
        company = Company(
            name="RemoveTest",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Test",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company)
        self.assertEqual(len(self.registry.companies), 1)
        success, message = self.registry.remove_company("RemoveTest")
        self.assertTrue(success)
        self.assertEqual(len(self.registry.companies), 0)
    
    def test_cancer_focused_filter(self):
        """Test filtering cancer-focused companies"""
        company1 = Company(
            name="Cancer1",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Cancer research",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=True
        )
        company2 = Company(
            name="Tech1",
            founded_year=2021,
            company_type=CompanyType.TECHNOLOGY,
            mission="Tech",
            employees=20,
            funding_usd=2000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company1)
        self.registry.add_company(company2)
        
        cancer_companies = self.registry.get_cancer_focused_companies()
        self.assertEqual(len(cancer_companies), 1)
        self.assertEqual(cancer_companies[0].name, "Cancer1")
    
    def test_companies_by_type(self):
        """Test filtering companies by type"""
        company1 = Company(
            name="Cancer1",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Cancer",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=True
        )
        company2 = Company(
            name="Cancer2",
            founded_year=2021,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Cancer",
            employees=20,
            funding_usd=2000000,
            is_active=True,
            cancer_focused=True
        )
        company3 = Company(
            name="Tech1",
            founded_year=2021,
            company_type=CompanyType.TECHNOLOGY,
            mission="Tech",
            employees=30,
            funding_usd=3000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company1)
        self.registry.add_company(company2)
        self.registry.add_company(company3)
        
        cancer_companies = self.registry.get_companies_by_type(CompanyType.CANCER_RESEARCH)
        self.assertEqual(len(cancer_companies), 2)
    
    def test_total_funding(self):
        """Test calculating total funding"""
        company1 = Company(
            name="Fund1",
            founded_year=2020,
            company_type=CompanyType.HEALTHCARE,
            mission="Health",
            employees=10,
            funding_usd=1000000,
            is_active=True,
            cancer_focused=False
        )
        company2 = Company(
            name="Fund2",
            founded_year=2021,
            company_type=CompanyType.HEALTHCARE,
            mission="Health",
            employees=20,
            funding_usd=2000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company1)
        self.registry.add_company(company2)
        
        total = self.registry.get_total_funding()
        self.assertEqual(total, 3000000)
    
    def test_total_employees(self):
        """Test calculating total employees"""
        company1 = Company(
            name="Emp1",
            founded_year=2020,
            company_type=CompanyType.HEALTHCARE,
            mission="Health",
            employees=50,
            funding_usd=1000000,
            is_active=True,
cancer_focused=False
        )
        company2 = Company(
            name="Emp2",
            founded_year=2021,
            company_type=CompanyType.HEALTHCARE,
            mission="Health",
            employees=75,
            funding_usd=2000000,
            is_active=True,
            cancer_focused=False
        )
        self.registry.add_company(company1)
        self.registry.add_company(company2)
        
        total = self.registry.get_total_employees()
        self.assertEqual(total, 125)
    
    def test_health_check(self):
        """Test registry health check"""
        company = Company(
            name="HealthCheck",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Cancer research",
            employees=100,
            funding_usd=10000000,
            is_active=True,
            cancer_focused=True
        )
        self.registry.add_company(company)
        
        health = self.registry.health_check()
        self.assertEqual(health['total_companies'], 1)
        self.assertEqual(health['cancer_focused_count'], 1)
        self.assertEqual(health['total_funding_usd'], 10000000)
        self.assertEqual(health['total_employees'], 100)
        self.assertEqual(health['active_companies'], 1)
        self.assertIn('timestamp', health)


class TestFounderRegistry(unittest.TestCase):
    """Test founder registry operations"""
    
    def setUp(self):
        """Set up test registry"""
        self.registry = FounderRegistry()
    
    def test_add_valid_founder(self):
        """Test adding a valid founder"""
        founder = Founder(
            name="Test Founder",
            primary_company="TestCorp",
            companies_founded=["TestCorp"],
            cancer_initiative=False,
            years_active=15
        )
        success, message = self.registry.add_founder(founder)
        self.assertTrue(success)
        self.assertIn("added successfully", message)
        self.assertEqual(len(self.registry.founders), 1)
    
    def test_add_duplicate_founder(self):
        """Test adding duplicate founder"""
        founder = Founder(
            name="Duplicate",
            primary_company="Corp",
            companies_founded=["Corp"],
            cancer_initiative=False,
            years_active=10
        )
        self.registry.add_founder(founder)
        success, message = self.registry.add_founder(founder)
        self.assertFalse(success)
        self.assertIn("already exists", message)
    
    def test_get_founder(self):
        """Test retrieving a founder"""
        founder = Founder(
            name="Retrieve Test",
            primary_company="Corp",
            companies_founded=["Corp"],
            cancer_initiative=False,
            years_active=10
        )
        self.registry.add_founder(founder)
        retrieved = self.registry.get_founder("Retrieve Test")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Retrieve Test")
    
    def test_cancer_initiative_filter(self):
        """Test filtering cancer initiative founders"""
        founder1 = Founder(
            name="Cancer Founder",
            primary_company="CancerCorp",
            companies_founded=["CancerCorp"],
            cancer_initiative=True,
            years_active=10
        )
        founder2 = Founder(
            name="Tech Founder",
            primary_company="TechCorp",
            companies_founded=["TechCorp"],
            cancer_initiative=False,
            years_active=15
        )
        self.registry.add_founder(founder1)
        self.registry.add_founder(founder2)
        
        cancer_founders = self.registry.get_cancer_initiative_founders()
        self.assertEqual(len(cancer_founders), 1)
        self.assertEqual(cancer_founders[0].name, "Cancer Founder")


class TestIntegration(unittest.TestCase):
    """Integration tests for registries"""
    
    def setUp(self):
        """Set up test environment"""
        self.company_registry = CompanyRegistry()
        self.founder_registry = FounderRegistry()
    
    def test_complete_workflow(self):
        """Test complete workflow of creating founder and companies"""
        founder = Founder(
            name="Sytse Sijbrandij",
            primary_company="GitLab",
            companies_founded=["GitLab", "CancerFightCorp"],
            cancer_initiative=True,
            years_active=20
        )
        self.founder_registry.add_founder(founder)
        
        company1 = Company(
            name="GitLab",
            founded_year=2011,
            company_type=CompanyType.TECHNOLOGY,
            mission="DevOps platform",
            employees=800,
            funding_usd=75000000,
            is_active=True,
            cancer_focused=False
        )
        company2 = Company(
            name="CancerFightCorp",
            founded_year=2022,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Fighting cancer with innovation",
            employees=150,
            funding_usd=50000000,
            is_active=True,
            cancer_focused=True
        )
        
        success1, msg1 = self.company_registry.add_company(company1)
        success2, msg2 = self.company_registry.add_company(company2)
        
        self.assertTrue(success1)
        self.assertTrue(success2)
        
        retrieved_founder = self.founder_registry.get_founder("Sytse Sijbrandij")
        self.assertIsNotNone(retrieved_founder)
        self.assertTrue(retrieved_founder.cancer_initiative)
        
        cancer_companies = self.company_registry.get_cancer_focused_companies()
        self.assertEqual(len(cancer_companies), 1)
        
        total_funding = self.company_registry.get_total_funding()
        self.assertEqual(total_funding, 125000000)
        
        health = self.company_registry.health_check()
        self.assertEqual(health['total_companies'], 2)
        self.assertEqual(health['cancer_focused_count'], 1)
    
    def test_export_to_json(self):
        """Test exporting data to JSON format"""
        founder = Founder(
            name="Test Founder",
            primary_company="TestCorp",
            companies_founded=["TestCorp"],
            cancer_initiative=True,
            years_active=10
        )
        company = Company(
            name="TestCorp",
            founded_year=2020,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Test cancer research",
            employees=50,
            funding_usd=5000000,
            is_active=True,
            cancer_focused=True
        )
        
        self.founder_registry.add_founder(founder)
        self.company_registry.add_company(company)
        
        founders_json = json.dumps(self.founder_registry.list_all())
        companies_json = json.dumps(self.company_registry.list_all())
        
        self.assertIsInstance(json.loads(founders_json), list)
        self.assertIsInstance(json.loads(companies_json), list)
        self.assertGreater(len(founders_json), 0)
        self.assertGreater(len(companies_json), 0)


def run_tests(verbosity=2):
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCompanyValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestFounderValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestCompanyRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestFounderRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def generate_sample_data(company_registry: CompanyRegistry, founder_registry: FounderRegistry):
    """Generate sample data for demonstration"""
    companies = [
        Company(
            name="GitLab",
            founded_year=2011,
            company_type=CompanyType.TECHNOLOGY,
            mission="DevOps platform for collaboration",
            employees=800,
            funding_usd=75000000,
            is_active=True,
            cancer_focused=False
        ),
        Company(
            name="CancerTech Solutions",
            founded_year=2022,
            company_type=CompanyType.CANCER_RESEARCH,
            mission="Developing AI-driven cancer detection tools",
            employees=120,
            funding_usd=45000000,
            is_active=True,
            cancer_focused=True
        ),
        Company(
            name="Immunotherapy Labs",
            founded_year=2023,
            company_type=CompanyType.BIOTECH,
            mission="Advancing immunotherapy treatments for cancer",
            employees=200,
            funding_usd=60000000,
            is_active=True,
            cancer_focused=True
        ),
        Company(
            name="Diagnostics Plus",
            founded_year=2021,
            company_type=CompanyType.PHARMACEUTICAL,
            mission="Early cancer diagnosis through biomarkers",
            employees=90,
            funding_usd=35000000,
            is_active=True,
            cancer_focused=True
        ),
        Company(
            name="BioData Analytics",
            founded_year=2020,
            company_type=CompanyType.TECHNOLOGY,
            mission="Data analytics for healthcare research",
            employees=150,
            funding_usd=25000000,
            is_active=True,
            cancer_focused=False
        ),
    ]
    
    for company in companies:
        success, message = company_registry.add_company(company)
        if success:
            print(f"✓ Added company: {company.name}")
        else:
            print(f"✗ Failed to add company: {message}")
    
    founders = [
        Founder(
            name="Sytse Sijbrandij",
            primary_company="GitLab",
            companies_founded=["GitLab", "CancerTech Solutions", "Immunotherapy Labs"],
            cancer_initiative=True,
            years_active=13
        ),
        Founder(
            name="Dr. Sarah Chen",
            primary_company="Diagnostics Plus",
            companies_founded=["Diagnostics Plus"],
            cancer_initiative=True,
            years_active=8
        ),
        Founder(
            name="Michael Rodriguez",
            primary_company="BioData Analytics",
            companies_founded=["BioData Analytics"],
            cancer_initiative=False,
            years_active=10
        ),
    ]
    
    for founder in founders:
        success, message = founder_registry.add_founder(founder)
        if success:
            print(f"✓ Added founder: {founder.name}")
        else:
            print(f"✗ Failed to add founder: {message}")


def print_summary(company_registry: CompanyRegistry, founder_registry: FounderRegistry):
    """Print summary of registries"""
    print("\n" + "="*70)
    print("CANCER INITIATIVE SUMMARY")
    print("="*70)
    
    health = company_registry.health_check()
    print(f"\nCompany Registry Health Check:")
    print(f"  Total Companies: {health['total_companies']}")
    print(f"  Cancer-Focused Companies: {health['cancer_focused_count']}")
    print(f"  Total Funding: ${health['total_funding_usd']:,.0f}")
    print(f"  Total Employees: {health['total_employees']}")
    print(f"  Active Companies: {health['active_companies']}")
    print(f"  Timestamp: {health['timestamp']}")
    
    cancer_companies = company_registry.get_cancer_focused_companies()
    print(f"\nCancer-Focused Companies ({len(cancer_companies)}):")
    for company in cancer_companies:
        print(f"  • {company.name} ({company.company_type.value})")
        print(f"    Mission: {company.mission}")
        print(f"    Funding: ${company.funding_usd:,.0f} | Employees: {company.employees}")
    
    cancer_founders = founder_registry.get_cancer_initiative_founders()
    print(f"\nCancer Initiative Founders ({len(cancer_founders)}):")
    for founder in cancer_founders:
        print(f"  • {founder.name}")
        print(f"    Primary Company: {founder.primary_company}")
        print(f"    Companies Founded: {', '.join(founder.companies_founded)}")
        print(f"    Years Active: {founder.years_active}")
    
    print("\n" + "="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Cancer Initiative Validation and Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --run-tests --verbosity 2
  %(prog)s --demo
  %(prog)s --run-tests --demo
  %(prog)s --test-case TestCompanyValidation
        """
    )
    
    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='Run all unit and integration tests'
    )
    
    parser.add_argument(
        '--verbosity',
        type=int,
        default=2,
        choices=[0, 1, 2],
        help='Test verbosity level (default: 2)'
    )
    
    parser.add_argument(
        '--test-case',
        type=str,
        help='Run specific test case by name'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demo with sample data'
    )
    
    parser.add_argument(
        '--export-json',
        type=str,
        help='Export demo data to JSON file'
    )
    
    args = parser.parse_args()
    
    if not args.run_tests and not args.demo:
        parser.print_help()
        return 0
    
    if args.run_tests:
        print("Running tests...\n")
        if args.test_case:
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromName(f'__main__.{args.test_case}')
            runner = unittest.TextTestRunner(verbosity=args.verbosity)
            result = runner.run(suite)
            return 0 if result.wasSuccessful() else 1
        else:
            success = run_tests(verbosity=args.verbosity)
            if not success:
                return 1
    
    if args.demo:
        print("\nGenerating sample data...\n")
        company_registry = CompanyRegistry()
        founder_registry = FounderRegistry()
        
        generate_sample_data(company_registry, founder_registry)
        print_summary(company_registry, founder_registry)
        
        if args.export_json:
            output = {
                'companies': company_registry.list_all(),
                'founders': founder_registry.list_all(),
                'health_check': company_registry.health_check()
            }
            with open(args.export_json, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"\n✓ Data exported to {args.export_json}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())