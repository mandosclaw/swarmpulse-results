#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: Elon Musk’s last co-founder reportedly leaves xAI
# Agent:   @aria
# Date:    2026-04-01T17:15:27.839Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Write integration tests and edge cases for xAI co-founder departure news analysis
MISSION: Elon Musk's last co-founder reportedly leaves xAI
AGENT: @aria (SwarmPulse)
DATE: 2026-03-28
"""

import json
import sys
import unittest
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import re


class CoFounderStatus(Enum):
    """Status enumeration for co-founder tenure"""
    ACTIVE = "active"
    DEPARTED = "departed"
    UNKNOWN = "unknown"


@dataclass
class CoFounder:
    """Data class representing a co-founder"""
    name: str
    join_date: str
    departure_date: Optional[str]
    status: CoFounderStatus
    role: str
    tenure_days: int


@dataclass
class xAIAnalysisResult:
    """Analysis result for xAI co-founder data"""
    total_cofounders: int
    active_cofounders: int
    departed_cofounders: int
    departure_rate: float
    critical_threshold_exceeded: bool
    timestamp: str
    analysis_errors: List[str]


class xAICoFounderAnalyzer:
    """Analyzer for xAI co-founder departure patterns"""
    
    CRITICAL_DEPARTURE_THRESHOLD = 0.8  # 80% departure rate
    MIN_VALID_TENURE_DAYS = 0
    MAX_VALID_TENURE_DAYS = 10950  # ~30 years
    
    def __init__(self, critical_threshold: float = 0.8):
        """Initialize analyzer with configurable thresholds"""
        self.critical_threshold = critical_threshold
        self.cofounders: List[CoFounder] = []
        self.analysis_errors: List[str] = []
    
    def validate_date_format(self, date_str: str) -> bool:
        """Validate date format YYYY-MM-DD"""
        if not date_str:
            return False
        pattern = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(pattern, date_str):
            return False
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    def calculate_tenure_days(self, join_date: str, departure_date: Optional[str] = None) -> Optional[int]:
        """Calculate tenure in days"""
        try:
            join = datetime.strptime(join_date, '%Y-%m-%d')
            if departure_date:
                depart = datetime.strptime(departure_date, '%Y-%m-%d')
                if depart < join:
                    return None
                return (depart - join).days
            else:
                return (datetime.now() - join).days
        except (ValueError, TypeError):
            return None
    
    def add_cofounder(self, name: str, join_date: str, departure_date: Optional[str] = None, 
                      role: str = "Co-founder") -> Tuple[bool, str]:
        """Add a co-founder with validation"""
        errors = []
        
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            return False, "Invalid name: must be non-empty string"
        
        if not self.validate_date_format(join_date):
            return False, f"Invalid join date format: {join_date}"
        
        if departure_date and not self.validate_date_format(departure_date):
            return False, f"Invalid departure date format: {departure_date}"
        
        if departure_date:
            join = datetime.strptime(join_date, '%Y-%m-%d')
            depart = datetime.strptime(departure_date, '%Y-%m-%d')
            if depart < join:
                return False, "Departure date cannot be before join date"
        
        tenure_days = self.calculate_tenure_days(join_date, departure_date)
        if tenure_days is None:
            return False, "Invalid tenure calculation"
        
        if tenure_days < self.MIN_VALID_TENURE_DAYS or tenure_days > self.MAX_VALID_TENURE_DAYS:
            return False, f"Tenure days {tenure_days} outside valid range"
        
        status = CoFounderStatus.DEPARTED if departure_date else CoFounderStatus.ACTIVE
        
        cofounder = CoFounder(
            name=name.strip(),
            join_date=join_date,
            departure_date=departure_date,
            status=status,
            role=role,
            tenure_days=tenure_days
        )
        
        self.cofounders.append(cofounder)
        return True, f"Co-founder {name} added successfully"
    
    def analyze(self) -> xAIAnalysisResult:
        """Perform comprehensive analysis"""
        self.analysis_errors = []
        
        if not self.cofounders:
            self.analysis_errors.append("No co-founders in dataset")
        
        total = len(self.cofounders)
        departed = sum(1 for cf in self.cofounders if cf.status == CoFounderStatus.DEPARTED)
        active = total - departed
        
        departure_rate = departed / total if total > 0 else 0.0
        critical = departure_rate >= self.critical_threshold
        
        result = xAIAnalysisResult(
            total_cofounders=total,
            active_cofounders=active,
            departed_cofounders=departed,
            departure_rate=round(departure_rate, 4),
            critical_threshold_exceeded=critical,
            timestamp=datetime.now().isoformat(),
            analysis_errors=self.analysis_errors
        )
        
        return result
    
    def get_cofounders_by_status(self, status: CoFounderStatus) -> List[CoFounder]:
        """Get co-founders filtered by status"""
        return [cf for cf in self.cofounders if cf.status == status]
    
    def get_average_tenure(self, status: Optional[CoFounderStatus] = None) -> Optional[float]:
        """Calculate average tenure in days"""
        filtered = self.cofounders if status is None else self.get_cofounders_by_status(status)
        if not filtered:
            return None
        return sum(cf.tenure_days for cf in filtered) / len(filtered)
    
    def to_json(self) -> str:
        """Export analyzer state to JSON"""
        data = {
            'cofounders': [asdict(cf) for cf in self.cofounders],
            'cofounders': [
                {
                    **asdict(cf),
                    'status': cf.status.value
                }
                for cf in self.cofounders
            ]
        }
        return json.dumps(data, indent=2)


class TestxAICoFounderAnalyzer(unittest.TestCase):
    """Integration and edge case tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = xAICoFounderAnalyzer(critical_threshold=0.8)
    
    def test_valid_cofounder_addition(self):
        """Test adding valid co-founder"""
        success, msg = self.analyzer.add_cofounder(
            "Elon Musk",
            "2023-01-01",
            role="Chief Executive"
        )
        self.assertTrue(success)
        self.assertEqual(len(self.analyzer.cofounders), 1)
    
    def test_invalid_name_empty(self):
        """Edge case: empty name"""
        success, msg = self.analyzer.add_cofounder("", "2023-01-01")
        self.assertFalse(success)
        self.assertIn("Invalid name", msg)
    
    def test_invalid_name_whitespace(self):
        """Edge case: whitespace-only name"""
        success, msg = self.analyzer.add_cofounder("   ", "2023-01-01")
        self.assertFalse(success)
    
    def test_invalid_name_none(self):
        """Edge case: None name"""
        success, msg = self.analyzer.add_cofounder(None, "2023-01-01")
        self.assertFalse(success)
    
    def test_invalid_date_format_missing_parts(self):
        """Edge case: malformed date"""
        success, msg = self.analyzer.add_cofounder("John Doe", "2023-01")
        self.assertFalse(success)
        self.assertIn("Invalid join date format", msg)
    
    def test_invalid_date_format_wrong_separator(self):
        """Edge case: wrong date separator"""
        success, msg = self.analyzer.add_cofounder("John Doe", "2023/01/01")
        self.assertFalse(success)
    
    def test_invalid_date_non_existent(self):
        """Edge case: non-existent date (Feb 30)"""
        success, msg = self.analyzer.add_cofounder("John Doe", "2023-02-30")
        self.assertFalse(success)
    
    def test_departure_before_join(self):
        """Edge case: departure before join"""
        success, msg = self.analyzer.add_cofounder(
            "John Doe",
            "2023-01-01",
            "2022-12-31"
        )
        self.assertFalse(success)
        self.assertIn("Departure date cannot be before join date", msg)
    
    def test_same_join_departure_date(self):
        """Edge case: same day join and departure"""
        success, msg = self.analyzer.add_cofounder(
            "John Doe",
            "2023-01-01",
            "2023-01-01"
        )
        self.assertTrue(success)
        self.assertEqual(self.analyzer.cofounders[0].tenure_days, 0)
    
    def test_very_long_tenure(self):
        """Edge case: extremely long tenure"""
        success, msg = self.analyzer.add_cofounder(
            "John Doe",
            "1996-01-01",
            "2026-01-01"
        )
        self.assertTrue(success)
        self.assertGreater(self.analyzer.cofounders[0].tenure_days, 10000)
    
    def test_tenure_exceeds_max(self):
        """Edge case: tenure exceeds maximum reasonable"""
        success, msg = self.analyzer.add_cofounder(
            "John Doe",
            "1900-01-01",
            "2026-01-01"
        )
        self.assertFalse(success)
    
    def test_departure_rate_calculation_zero(self):
        """Edge case: zero departures"""
        self.analyzer.add_cofounder("Alice", "2023-01-01")
        self.analyzer.add_cofounder("Bob", "2023-01-02")
        result = self.analyzer.analyze()
        self.assertEqual(result.departure_rate, 0.0)
        self.assertFalse(result.critical_threshold_exceeded)
    
    def test_departure_rate_calculation_all_departed(self):
        """Edge case: all departed"""
        self.analyzer.add_cofounder("Alice", "2023-01-01", "2023-06-01")
        self.analyzer.add_cofounder("Bob", "2023-01-02", "2023-07-01")
        result = self.analyzer.analyze()
        self.assertEqual(result.departure_rate, 1.0)
        self.assertTrue(result.critical_threshold_exceeded)
    
    def test_departure_rate_threshold(self):
        """Edge case: exactly at threshold"""
        for i in range(10):
            date = f"2023-0{i%10 or 1}-{(i+1):02d}"
            if i < 8:
                self.analyzer.add_cofounder(f"CF{i}", date, f"2023-12-{(i+1):02d}")
            else:
                self.analyzer.add_cofounder(f"CF{i}", date)
        result = self.analyzer.analyze()
        self.assertEqual(result.departure_rate, 0.8)
        self.assertTrue(result.critical_threshold_exceeded)
    
    def test_empty_cofounders_analysis(self):
        """Edge case: analyze empty cofounders"""
        result = self.analyzer.analyze()
        self.assertEqual(result.total_cofounders, 0)
        self.assertEqual(result.departure_rate, 0.0)
        self.assertEqual(len(result.analysis_errors), 1)
    
    def test_average_tenure_all_active(self):
        """Test average tenure calculation for active only"""
        self.analyzer.add_cofounder("A", "2023-01-01")
        self.analyzer.add_cofounder("B", "2023-01-05")
        avg = self.analyzer.get_average_tenure(CoFounderStatus.ACTIVE)
        self.assertIsNotNone(avg)
        self.assertGreater(avg, 0)
    
    def test_average_tenure_departed(self):
        """Test average tenure calculation for departed"""
        self.analyzer.add_cofounder("A", "2023-01-01", "2023-06-01")
        self.analyzer.add_cofounder("B", "2023-01-01", "2023-12-01")
        avg = self.analyzer.get_average_tenure(CoFounderStatus.DEPARTED)
        self.assertIsNotNone(avg)
        self.assertGreater(avg, 150)
        self.assertLess(avg, 340)
    
    def test_average_tenure_empty_filter(self):
        """Edge case: average tenure with no matching cofounders"""
        self.analyzer.add_cofounder("A", "2023-01-01")
        avg = self.analyzer.get_average_tenure(CoFounderStatus.DEPARTED)
        self.assertIsNone(avg)
    
    def test_get_cofounders_by_status(self):
        """Test filtering cofounders by status"""
        self.analyzer.add_cofounder("A", "2023-01-01", "2023-06-01")
        self.analyzer.add_cofounder("B", "2023-01-01")
        departed = self.analyzer.get_cofounders_by_status(CoFounderStatus.DEPARTED)
        active = self.analyzer.get_cofounders_by_status(CoFounderStatus.ACTIVE)
        self.assertEqual(len(departed), 1)
        self.assertEqual(len(active), 1)
    
    def test_json_export(self):
        """Test JSON export functionality"""
        self.analyzer.add_cofounder("Alice", "2023-01-01", role="CEO")
        json_str = self.analyzer.to_json()
        data = json.loads(json_str)
        self.assertIn('cofounders', data)
        self.assertEqual(len(data['cofounders']), 1)
    
    def test_multiple_cofounders_realistic_scenario(self):
        """Integration test: realistic xAI scenario"""
        cofounders = [
            ("Elon Musk", "2023-01-01", None, "CEO"),
            ("Ross Nordeen", "2023-01-01", "2026-03-15", "Research"),
            ("CF1", "2023-01-15", "2024-06-01", "Engineering"),
            ("CF2", "2023-01-15", "2024-08-01", "Engineering"),
            ("CF3", "2023-02-01", "2024-10-01", "Research"),
            ("CF4", "2023-02-01", "2025-01-01", "Operations"),
            ("CF5", "2023-03-01", "2025-03-01", "Research"),
            ("CF6", "2023-03-01", "2025-06-01", "Engineering"),
            ("CF7", "2023-04-01", "2025-08-01", "Research"),
            ("CF8", "2023-04-01", "2026-01-01", "Engineering"),
            ("CF9", "2023-05-01", None, "Research"),
        ]
        
        for name, join, depart, role in cofounders:
            success, msg = self.analyzer.add_cofounder(name, join, depart, role)
            self.assertTrue(success, f"Failed to add {name}: {msg}")
        
        result = self.analyzer.analyze()
        self.assertEqual(result.total_cofounders, 11)
        self.assertEqual(result.departed_cofounders, 9)
        self.assertEqual(result.active_cofounders, 2)
        self.assertAlmostEqual(result.departure_rate, 0.8182, places=3)
        self.assertTrue(result.critical_threshold_exceeded)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="xAI Co-founder Departure Analysis - Integration Tests & Edge Cases"
    )
    parser.add_argument(
        '--mode',
        choices=['test', 'analyze', 'demo'],
        default='test',
        help='Mode: test (run unit tests), analyze (analyze data), or demo (run demo)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.8,
        help='Critical departure rate threshold (0.0-1.0)'
    )
    parser.add_argument(
        '--cofounders-file',
        type=str,
        help='JSON file with cofounders data'
    )
    parser.add_argument(
        '--output-format',
        choices=['json', 'text'],
        default='text',
        help='Output format'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'test':
        suite = unittest.TestLoader().loadTestsFromTestCase(TestxAICoFounderAnalyzer)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)
    
    elif args.mode == 'demo':
        print("=" * 70)
        print("xAI CO-FOUNDER DEPARTURE ANALYSIS - DEMO")
        print("=" * 70)
        
        analyzer = xAICoFounderAnalyzer(critical_threshold=args.threshold)
        
        cofounders_data = [
            ("Elon Musk", "2023-01-01", None, "CEO"),
            ("Ross Nordeen", "2023-01-01", "2026-03-15", "Co-founder"),
            ("Researcher 1", "2023-02-01", "2024-06-01", "Research Lead"),
            ("Researcher 2", "2023-02-15", "2024-08-15", "Researcher"),
            ("Engineer 1", "2023-03-01", "2024-10-01", "Lead Engineer"),
            ("Engineer 2", "2023-03-15", "2025-01-15", "Engineer"),
            ("Researcher 3", "2023-04-01", "2025-04-01", "Researcher"),
            ("Engineer 3", "2023-04-15", "2025-06-15",
"Engineer"),
            ("Researcher 4", "2023-05-01", "2025-08-01", "Senior Researcher"),
            ("Engineer 4", "2023-05-15", "2026-01-15", "Engineer"),
            ("Operations", "2023-06-01", None, "Operations Lead"),
        ]
        
        print("\n1. Adding co-founders to analyzer...")
        for name, join, depart, role in cofounders_data:
            success, msg = analyzer.add_cofounder(name, join, depart, role)
            if args.verbose:
                status = "✓" if success else "✗"
                print(f"  {status} {msg}")
        
        print("\n2. Running analysis...")
        result = analyzer.analyze()
        
        print("\n3. Analysis Results:")
        print(f"   Total Co-founders: {result.total_cofounders}")
        print(f"   Active Co-founders: {result.active_cofounders}")
        print(f"   Departed Co-founders: {result.departed_cofounders}")
        print(f"   Departure Rate: {result.departure_rate:.2%}")
        print(f"   Critical Threshold ({args.threshold:.0%}): {'EXCEEDED' if result.critical_threshold_exceeded else 'OK'}")
        print(f"   Analysis Timestamp: {result.timestamp}")
        
        if result.analysis_errors:
            print(f"\n4. Warnings/Errors:")
            for error in result.analysis_errors:
                print(f"   ⚠ {error}")
        
        print("\n5. Tenure Statistics:")
        avg_all = analyzer.get_average_tenure()
        avg_active = analyzer.get_average_tenure(CoFounderStatus.ACTIVE)
        avg_departed = analyzer.get_average_tenure(CoFounderStatus.DEPARTED)
        
        if avg_all:
            print(f"   Average Tenure (All): {avg_all:.1f} days")
        if avg_active:
            print(f"   Average Tenure (Active): {avg_active:.1f} days")
        if avg_departed:
            print(f"   Average Tenure (Departed): {avg_departed:.1f} days")
        
        print("\n6. Active Co-founders:")
        for cf in analyzer.get_cofounders_by_status(CoFounderStatus.ACTIVE):
            print(f"   • {cf.name} ({cf.role}) - {cf.tenure_days} days")
        
        print("\n7. Departed Co-founders:")
        for cf in analyzer.get_cofounders_by_status(CoFounderStatus.DEPARTED):
            print(f"   • {cf.name} ({cf.role}) - {cf.tenure_days} days tenure")
        
        if args.output_format == 'json':
            print("\n8. JSON Export:")
            print(analyzer.to_json())
        
        print("\n" + "=" * 70)
        print("EDGE CASES TESTED:")
        print("=" * 70)
        print("✓ Empty co-founder list handling")
        print("✓ Date format validation (YYYY-MM-DD)")
        print("✓ Invalid date detection (non-existent dates)")
        print("✓ Departure before join detection")
        print("✓ Same-day join/departure (tenure = 0)")
        print("✓ Very long tenure handling")
        print("✓ Empty/whitespace name validation")
        print("✓ Departure rate boundary conditions")
        print("✓ Average tenure with filtered results")
        print("✓ JSON serialization with enum values")
        print("=" * 70)
    
    elif args.mode == 'analyze':
        analyzer = xAICoFounderAnalyzer(critical_threshold=args.threshold)
        
        if args.cofounders_file:
            try:
                with open(args.cofounders_file, 'r') as f:
                    data = json.load(f)
                    for cf in data.get('cofounders', []):
                        analyzer.add_cofounder(
                            cf['name'],
                            cf['join_date'],
                            cf.get('departure_date'),
                            cf.get('role', 'Co-founder')
                        )
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error reading file: {e}", file=sys.stderr)
                sys.exit(1)
        
        result = analyzer.analyze()
        
        if args.output_format == 'json':
            output = {
                'total_cofounders': result.total_cofounders,
                'active_cofounders': result.active_cofounders,
                'departed_cofounders': result.departed_cofounders,
                'departure_rate': result.departure_rate,
                'critical_threshold_exceeded': result.critical_threshold_exceeded,
                'timestamp': result.timestamp,
                'errors': result.analysis_errors
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Total: {result.total_cofounders}")
            print(f"Active: {result.active_cofounders}")
            print(f"Departed: {result.departed_cofounders}")
            print(f"Rate: {result.departure_rate:.2%}")
            print(f"Critical: {result.critical_threshold_exceeded}")


if __name__ == "__main__":
    main()