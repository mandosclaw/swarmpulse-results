#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-04-01T16:53:04.112Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Write integration tests covering edge cases and failure modes
Mission: Britain today generating 90%+ of electricity from renewables
Agent: @aria
Date: 2024
Source: https://grid.iamkate.com/
"""

import unittest
import json
import sys
import argparse
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import random
import statistics


class EnergySourceType(Enum):
    """Energy source classifications"""
    WIND = "wind"
    SOLAR = "solar"
    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    GAS = "gas"
    COAL = "coal"
    BIOMASS = "biomass"
    OTHER = "other"


@dataclass
class PowerReading:
    """Represents a single power grid reading"""
    timestamp: str
    source: EnergySourceType
    mw_generated: float
    renewable: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "source": self.source.value,
            "mw_generated": self.mw_generated,
            "renewable": self.renewable
        }


@dataclass
class GridSnapshot:
    """Complete grid state at a point in time"""
    timestamp: str
    readings: List[PowerReading]
    total_mw: float
    renewable_percentage: float
    grid_frequency: float


class GridDataFetcher:
    """Fetches grid data from source"""
    
    def __init__(self, base_url: str = "https://grid.iamkate.com"):
        self.base_url = base_url
        self.timeout = 10
        self.last_error = None
    
    def fetch_current_data(self) -> Dict[str, Any]:
        """Fetch current grid data - raises exceptions on failure"""
        try:
            if not self.base_url:
                raise ValueError("Base URL not configured")
            
            simulated_data = self._generate_mock_data()
            return simulated_data
        except Exception as e:
            self.last_error = str(e)
            raise
    
    def fetch_historical_data(self, hours: int) -> List[Dict[str, Any]]:
        """Fetch historical data spanning specified hours"""
        if hours < 0:
            raise ValueError("Hours must be non-negative")
        if hours > 8760:
            raise ValueError("Cannot fetch more than 1 year of data")
        
        return [self._generate_mock_data() for _ in range(hours)]
    
    def _generate_mock_data(self) -> Dict[str, Any]:
        """Generate realistic mock grid data"""
        total_mw = 30000 + random.randint(-5000, 5000)
        
        renewable_sources = {
            EnergySourceType.WIND: random.uniform(4000, 12000),
            EnergySourceType.SOLAR: random.uniform(0, 8000),
            EnergySourceType.HYDRO: random.uniform(1000, 3000),
            EnergySourceType.BIOMASS: random.uniform(500, 2000),
        }
        
        non_renewable = {
            EnergySourceType.NUCLEAR: random.uniform(7000, 9000),
            EnergySourceType.GAS: random.uniform(5000, 15000),
            EnergySourceType.COAL: random.uniform(0, 5000),
        }
        
        all_sources = {**renewable_sources, **non_renewable}
        renewable_mw = sum(renewable_sources.values())
        renewable_pct = (renewable_mw / total_mw * 100) if total_mw > 0 else 0
        
        readings = [
            PowerReading(
                timestamp=datetime.utcnow().isoformat(),
                source=source,
                mw_generated=mw,
                renewable=(source in renewable_sources)
            )
            for source, mw in all_sources.items()
        ]
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "readings": [r.to_dict() for r in readings],
            "total_mw": total_mw,
            "renewable_percentage": renewable_pct,
            "grid_frequency": 50.0 + random.uniform(-0.1, 0.1)
        }


class GridAnalyzer:
    """Analyzes grid data for renewable percentage and stability"""
    
    RENEWABLE_TARGET = 90.0
    MIN_FREQUENCY = 49.5
    MAX_FREQUENCY = 50.5
    
    def __init__(self):
        self.readings_history: List[GridSnapshot] = []
    
    def add_snapshot(self, snapshot: GridSnapshot) -> None:
        """Add a snapshot to history"""
        if snapshot is None:
            raise ValueError("Snapshot cannot be None")
        self.readings_history.append(snapshot)
    
    def check_renewable_target(self, renewable_pct: float) -> Tuple[bool, str]:
        """Check if renewable percentage meets target"""
        if renewable_pct < 0 or renewable_pct > 100:
            raise ValueError(f"Invalid percentage: {renewable_pct}")
        
        met = renewable_pct >= self.RENEWABLE_TARGET
        message = f"Renewable: {renewable_pct:.1f}% - Target: {self.RENEWABLE_TARGET}% - {'✓ MET' if met else '✗ MISSED'}"
        return met, message
    
    def check_grid_stability(self, frequency: float) -> Tuple[bool, str]:
        """Check if grid frequency is within safe limits"""
        safe = self.MIN_FREQUENCY <= frequency <= self.MAX_FREQUENCY
        message = f"Frequency: {frequency:.2f}Hz - Safe: {'✓' if safe else '✗'}"
        return safe, message
    
    def calculate_statistics(self) -> Dict[str, float]:
        """Calculate statistics from history"""
        if not self.readings_history:
            return {}
        
        renewable_pcts = [s.renewable_percentage for s in self.readings_history]
        frequencies = [s.grid_frequency for s in self.readings_history]
        
        return {
            "avg_renewable_pct": statistics.mean(renewable_pcts) if renewable_pcts else 0,
            "min_renewable_pct": min(renewable_pcts) if renewable_pcts else 0,
            "max_renewable_pct": max(renewable_pcts) if renewable_pcts else 0,
            "stdev_renewable_pct": statistics.stdev(renewable_pcts) if len(renewable_pcts) > 1 else 0,
            "avg_frequency": statistics.mean(frequencies) if frequencies else 0,
            "min_frequency": min(frequencies) if frequencies else 0,
            "max_frequency": max(frequencies) if frequencies else 0,
        }


class TestGridDataFetcher(unittest.TestCase):
    """Integration tests for GridDataFetcher"""
    
    def setUp(self):
        self.fetcher = GridDataFetcher()
    
    def test_fetch_current_data_success(self):
        """Test successful fetch of current data"""
        data = self.fetcher.fetch_current_data()
        
        self.assertIn("timestamp", data)
        self.assertIn("readings", data)
        self.assertIn("total_mw", data)
        self.assertIn("renewable_percentage", data)
        self.assertGreater(data["total_mw"], 0)
    
    def test_fetch_current_data_renewable_percentage_valid_range(self):
        """Test that renewable percentage is within valid range"""
        data = self.fetcher.fetch_current_data()
        renewable_pct = data["renewable_percentage"]
        
        self.assertGreaterEqual(renewable_pct, 0)
        self.assertLessEqual(renewable_pct, 100)
    
    def test_fetch_current_data_grid_frequency_valid(self):
        """Test that grid frequency is within operational range"""
        data = self.fetcher.fetch_current_data()
        frequency = data["grid_frequency"]
        
        self.assertGreater(frequency, 49)
        self.assertLess(frequency, 51)
    
    def test_fetch_historical_data_success(self):
        """Test successful fetch of historical data"""
        hours = 24
        data = self.fetcher.fetch_historical_data(hours)
        
        self.assertEqual(len(data), hours)
    
    def test_fetch_historical_data_zero_hours(self):
        """Test edge case of zero hours"""
        data = self.fetcher.fetch_historical_data(0)
        self.assertEqual(len(data), 0)
    
    def test_fetch_historical_data_negative_hours_fails(self):
        """Test that negative hours raises ValueError"""
        with self.assertRaises(ValueError):
            self.fetcher.fetch_historical_data(-1)
    
    def test_fetch_historical_data_exceeds_limit_fails(self):
        """Test that requesting more than 1 year fails"""
        with self.assertRaises(ValueError):
            self.fetcher.fetch_historical_data(8761)
    
    def test_fetch_with_no_url_fails(self):
        """Test that fetch fails when base URL is empty"""
        fetcher = GridDataFetcher(base_url="")
        with self.assertRaises(ValueError):
            fetcher.fetch_current_data()
    
    def test_error_tracking(self):
        """Test that errors are tracked"""
        fetcher = GridDataFetcher(base_url="")
        try:
            fetcher.fetch_current_data()
        except ValueError:
            pass
        
        self.assertIsNotNone(fetcher.last_error)


class TestGridAnalyzer(unittest.TestCase):
    """Integration tests for GridAnalyzer"""
    
    def setUp(self):
        self.analyzer = GridAnalyzer()
    
    def test_check_renewable_target_met(self):
        """Test when renewable target is met"""
        met, message = self.analyzer.check_renewable_target(95.0)
        
        self.assertTrue(met)
        self.assertIn("MET", message)
    
    def test_check_renewable_target_missed(self):
        """Test when renewable target is missed"""
        met, message = self.analyzer.check_renewable_target(85.0)
        
        self.assertFalse(met)
        self.assertIn("MISSED", message)
    
    def test_check_renewable_target_exactly_at_threshold(self):
        """Test when renewable is exactly at 90%"""
        met, message = self.analyzer.check_renewable_target(90.0)
        
        self.assertTrue(met)
    
    def test_check_renewable_target_zero_percent(self):
        """Test edge case of 0% renewable"""
        met, message = self.analyzer.check_renewable_target(0.0)
        
        self.assertFalse(met)
    
    def test_check_renewable_target_100_percent(self):
        """Test edge case of 100% renewable"""
        met, message = self.analyzer.check_renewable_target(100.0)
        
        self.assertTrue(met)
    
    def test_check_renewable_target_invalid_negative(self):
        """Test that negative percentage raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.check_renewable_target(-1.0)
    
    def test_check_renewable_target_invalid_over_100(self):
        """Test that percentage > 100 raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.check_renewable_target(101.0)
    
    def test_check_grid_stability_safe(self):
        """Test when grid frequency is safe"""
        safe, message = self.analyzer.check_grid_stability(50.0)
        
        self.assertTrue(safe)
        self.assertIn("✓", message)
    
    def test_check_grid_stability_low_frequency(self):
        """Test when frequency is too low"""
        safe, message = self.analyzer.check_grid_stability(49.4)
        
        self.assertFalse(safe)
    
    def test_check_grid_stability_high_frequency(self):
        """Test when frequency is too high"""
        safe, message = self.analyzer.check_grid_stability(50.6)
        
        self.assertFalse(safe)
    
    def test_check_grid_stability_at_min_boundary(self):
        """Test frequency exactly at minimum boundary"""
        safe, message = self.analyzer.check_grid_stability(49.5)
        
        self.assertTrue(safe)
    
    def test_check_grid_stability_at_max_boundary(self):
        """Test frequency exactly at maximum boundary"""
        safe, message = self.analyzer.check_grid_stability(50.5)
        
        self.assertTrue(safe)
    
    def test_add_snapshot_success(self):
        """Test adding a valid snapshot"""
        snapshot = GridSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            readings=[],
            total_mw=30000,
            renewable_percentage=95.0,
            grid_frequency=50.0
        )
        
        self.analyzer.add_snapshot(snapshot)
        self.assertEqual(len(self.analyzer.readings_history), 1)
    
    def test_add_snapshot_none_fails(self):
        """Test that adding None snapshot raises ValueError"""
        with self.assertRaises(ValueError):
            self.analyzer.add_snapshot(None)
    
    def test_calculate_statistics_empty_history(self):
        """Test statistics on empty history"""
        stats = self.analyzer.calculate_statistics()
        
        self.assertEqual(stats, {})
    
    def test_calculate_statistics_single_reading(self):
        """Test statistics with single reading"""
        snapshot = GridSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            readings=[],
            total_mw=30000,
            renewable_percentage=95.0,
            grid_frequency=50.0
        )
        
        self.analyzer.add_snapshot(snapshot)
        stats = self.analyzer.calculate_statistics()
        
        self.assertEqual(stats["avg_renewable_pct"], 95.0)
        self.assertEqual(stats["min_renewable_pct"], 95.0)
        self.assertEqual(stats["max_renewable_pct"], 95.0)
    
    def test_calculate_statistics_multiple_readings(self):
        """Test statistics with multiple readings"""
        for renewable_pct in [85.0, 90.0, 95.0, 92.0]:
            snapshot = GridSnapshot(
                timestamp=datetime.utcnow().isoformat(),
                readings=[],
                total_mw=30000,
                renewable_percentage=renewable_pct,
                grid_frequency=50.0
            )
            self.analyzer.add_snapshot(snapshot)
        
        stats = self.analyzer.calculate_statistics()
        
        self.assertAlmostEqual(stats["avg_renewable_pct"], 90.5, places=1)
        self.assertEqual(stats["min_renewable_pct"], 85.0)
        self.assertEqual(stats["max_renewable_pct"], 95.0)
        self.assertGreater(stats["stdev_renewable_pct"], 0)


class TestIntegrationEndToEnd(unittest.TestCase):
    """End-to-end integration tests"""
    
    def test_full_pipeline_current_data(self):
        """Test complete pipeline: fetch → analyze → report"""
        fetcher = GridDataFetcher()
        analyzer = GridAnalyzer()
        
        data = fetcher.fetch_current_data()
        snapshot = GridSnapshot(
            timestamp=data["timestamp"],
            readings=[PowerReading(**r) for r in data["readings"]],
            total_mw=data["total_mw"],
            renewable_percentage=data["renewable_percentage"],
            grid_frequency=data["grid_frequency"]
        )
        
        analyzer.add_snapshot(snapshot)
        
        renewable_met, _ = analyzer.check_renewable_target(snapshot.renewable_percentage)
        stability_safe, _ = analyzer.check_grid_stability(snapshot.grid_frequency)
        
        self.assertIsNotNone(renewable_met)
        self.assertIsNotNone(stability_safe)
    
    def test_full_pipeline_historical_analysis(self):
        """Test complete pipeline with historical data"""
        fetcher = GridDataFetcher()
        analyzer = GridAnalyzer()
        
        data_list = fetcher.fetch_historical_data(12)
        
        for data in data_list:
            snapshot = GridSnapshot(
                timestamp=data["timestamp"],
                readings=[PowerReading(**r) for r in data["readings"]],
                total_mw=data["total_mw"],
                renewable_percentage=data["renewable_percentage"],
                grid_frequency=data["grid_frequency"]
            )
            analyzer.add_snapshot(snapshot)
        
        stats = analyzer.calculate_statistics()
        
        self.assertIn("avg_renewable_pct", stats)
        self.assertGreater(len(analyzer.readings_history), 0)
    
    def test_concurrent_scenarios(self):
        """Test system under various scenarios"""
        scenarios = [
            {"renewable_pct": 95.0, "frequency": 50.0, "expected_stable": True},
            {"renewable_pct": 50.0, "frequency": 50.0, "expected_stable": True},
            {"renewable_pct": 100.0, "frequency": 49.5, "expected_stable": True},
            {"renewable_pct": 0.0, "frequency": 50.5, "expected_stable": True},
            {"renewable_pct": 75.0, "frequency": 49.4, "expected_stable": False},
        ]
        
        analyzer = GridAnalyzer()
        
        for scenario in scenarios:
            renewable_met, _ = analyzer.check_renewable_target(scenario["renewable_pct"])
            stability_safe, _ = analyzer.check_grid_stability(scenario["frequency"])
            
            is_stable = stability_safe
            self.assertEqual(is_stable, scenario["expected_stable"])


class TestEdgeCasesAndFailures(unittest.TestCase):
    """Specific tests for edge cases and failure modes"""
    
    def test_extreme_renewable_percentages(self):
        """Test with extreme renewable percentages"""
        analyzer = GridAnalyzer()
        
        test_cases = [0.0, 0.001, 50.0, 89.999, 90.0, 99.999, 100.0]
        
        for pct in test_cases:
            try:
                met, msg = analyzer.check_renewable_target(pct)
                self.assertIsInstance(met, bool)
                self.assertIsInstance(msg, str)
            except ValueError:
                self.fail(f"Should not raise for {pct}")
    
    def test_extreme_frequencies(self):
        """Test with extreme grid frequencies"""
        analyzer = GridAnalyzer()
        
        boundary_cases = [49.5, 50.0, 50.5]
        out_of_range = [49.4, 49.49, 50.51, 50.6]
        
        for freq in boundary_cases:
            safe, msg = analyzer.check_grid_stability(freq)
            self.assertTrue(safe, f"Boundary case {freq} should be safe")
        
        for freq in out_of_range:
            safe, msg = analyzer.check_grid_stability(freq)
            self.assertFalse(safe, f"Out-of-range case {freq} should be unsafe")
    
    def test_rapid_data_fetches(self):
        """Test rapid successive data fetches"""
        fetcher = GridDataFetcher()
        
        for _ in range(10):
            data = fetcher.fetch_current_data()
            self.assertIsNotNone(data)
            self.assertIn("renewable_percentage", data)
    
    def test_large_historical_dataset(self):
        """Test handling of large historical dataset"""
        fetcher = GridDataFetcher()
        
        data_list = fetcher.fetch_historical_data(365)
        
        self.assertEqual(len(data_list), 365)
        
        for data in data_list:
            self.assertGreater(data["total_mw"], 0)
            self.assertGreaterEqual(data["renewable_percentage"], 0)
            self.assertLessEqual(data["renewable_percentage"], 100)
    
    def test_snapshot_with_zero_readings(self):
        """Test snapshot with empty readings list"""
        analyzer = GridAnalyzer()
        snapshot = GridSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            readings=[],
            total_mw=0,
            renewable_percentage=0,
            grid_frequency=50.0
        )
        
        analyzer.add_snapshot(snapshot)
        stats = analyzer.calculate_statistics()
        
        self.assertIsNotNone(stats)
    
    def test_floating_point_precision(self):
        """Test handling of floating point precision issues"""
        analyzer = GridAnalyzer()
        
        test_values = [
            89.99999999999999,
            90.0,
            90.00000000000001,
        ]
        
        for val in test_values:
            met, msg = analyzer.check_renewable_target(val)
            self.assertIsInstance(met, bool)
    
    def test_timestamp_format_consistency(self):
        """Test that timestamps are consistently formatted"""
        fetcher = GridDataFetcher()
        
        data = fetcher.fetch_current_data()
        timestamp = data["timestamp"]
        
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            self.fail(f"Timestamp not in ISO format: {timestamp}")
    
    def test_multiple_analyzers_independence(self):
        """Test that multiple analyzer instances don't interfere"""
        analyzer1 = GridAnalyzer()
        analyzer2 = GridAnalyzer()
        
        snapshot1 = GridSnapshot(
            timestamp=datetime.utcnow().isoformat(),
            readings=[],
            total_mw=30000,
            renewable_percentage=95.0,
            grid_frequency=50.0
        )
        
        analyzer1.add_snapshot(snapshot1)
        
        self.assertEqual(len(analyzer1.readings_history), 1)
        self.assertEqual(len(analyzer2.readings_history), 0)


def generate_test_report(test_results: unittest.TestResult) -> Dict[str, Any]:
    """Generate a structured test report"""
    return {
        "tests_run": test_results.testsRun,
        "failures": len(test_results.failures),
        "errors": len(test_results.errors),
        "skipped": len(test_results.skipped),
        "success": test_results.wasSuccessful(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Integration tests for Britain's renewable energy grid monitoring"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--test-pattern",
        type=str,
        default="",
        help="Run only tests matching this pattern"
    )
    parser.add_argument(
        "--json-report",
        action="store_true",
        help="Output test report as JSON"
    )
    
    args = parser.parse_args()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [
        TestGridDataFetcher,
        TestGridAnalyzer,
        TestIntegrationEndToEnd,
        TestEdgeCasesAndFailures,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        if args.test_pattern:
            tests = [t for t in tests if args.test_pattern in str(t)]
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
    result = runner.run(suite)
    
    if args.json_report:
        report = generate_test_report(result)
        print("\n" + json.dumps(report, indent=2))
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())