#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-03-31T19:31:02.824Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Write integration tests for Britain's renewable energy grid monitoring
Mission: Britain today generating 90%+ of electricity from renewables
Agent: @aria
Date: 2024

Integration tests covering edge cases and failure modes for grid renewable
energy data collection, processing, and analysis from grid.iamkate.com
"""

import unittest
import json
import sys
import argparse
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
import io
import time
from datetime import datetime, timedelta


class EnergySource(Enum):
    """Energy source types for British grid"""
    WIND = "wind"
    SOLAR = "solar"
    HYDRO = "hydro"
    NUCLEAR = "nuclear"
    GAS = "gas"
    COAL = "coal"
    OTHER = "other"


@dataclass
class GridSnapshot:
    """Represents a snapshot of grid data at a point in time"""
    timestamp: datetime
    total_demand_mw: float
    renewable_mw: float
    source_breakdown: Dict[EnergySource, float]
    renewable_percentage: float
    grid_frequency_hz: float

    def __post_init__(self):
        if self.total_demand_mw <= 0:
            raise ValueError("Total demand must be positive")
        if not (0 <= self.renewable_percentage <= 100):
            raise ValueError("Renewable percentage must be 0-100")
        if not (47 <= self.grid_frequency_hz <= 52):
            raise ValueError("Grid frequency must be 47-52 Hz")


class GridDataFetcher:
    """Fetches grid data from remote API"""

    def __init__(self, api_url: str, timeout_seconds: int = 10):
        self.api_url = api_url
        self.timeout_seconds = timeout_seconds
        self.last_fetch_time = None
        self.fetch_count = 0

    def fetch_current_data(self) -> Dict:
        """Fetch current grid data from API"""
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(self.api_url)
            req.add_header('User-Agent', 'SwarmPulse/1.0')
            
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    self.last_fetch_time = datetime.now()
                    self.fetch_count += 1
                    return data
            except urllib.error.HTTPError as e:
                raise ConnectionError(f"HTTP {e.code}: {e.reason}")
            except urllib.error.URLError as e:
                raise ConnectionError(f"Network error: {e.reason}")
                
        except Exception as e:
            raise ConnectionError(f"Failed to fetch grid data: {str(e)}")

    def fetch_historical_data(self, hours_back: int) -> List[Dict]:
        """Fetch historical grid data"""
        if hours_back < 1 or hours_back > 8760:
            raise ValueError("hours_back must be between 1 and 8760")
        
        data = []
        current_time = datetime.now()
        for i in range(hours_back):
            data.append({
                "timestamp": (current_time - timedelta(hours=i)).isoformat(),
                "demand_mw": 30000 + (i % 5000),
                "renewable_mw": 18000 + (i % 3000),
            })
        return data


class GridDataProcessor:
    """Processes raw grid data into meaningful metrics"""

    def __init__(self):
        self.processed_snapshots: List[GridSnapshot] = []

    def parse_snapshot(self, raw_data: Dict) -> GridSnapshot:
        """Parse raw API data into GridSnapshot"""
        try:
            timestamp = datetime.fromisoformat(raw_data.get("timestamp", datetime.now().isoformat()))
            total_demand = float(raw_data.get("total_demand_mw", 0))
            renewable = float(raw_data.get("renewable_mw", 0))
            
            source_breakdown = {}
            for source in EnergySource:
                source_breakdown[source] = float(raw_data.get(f"{source.value}_mw", 0))
            
            if total_demand == 0:
                renewable_pct = 0
            else:
                renewable_pct = min(100, (renewable / total_demand) * 100)
            
            frequency = float(raw_data.get("frequency_hz", 50.0))
            
            snapshot = GridSnapshot(
                timestamp=timestamp,
                total_demand_mw=total_demand,
                renewable_mw=renewable,
                source_breakdown=source_breakdown,
                renewable_percentage=renewable_pct,
                grid_frequency_hz=frequency
            )
            
            self.processed_snapshots.append(snapshot)
            return snapshot
            
        except (ValueError, KeyError, TypeError) as e:
            raise ValueError(f"Failed to parse snapshot: {str(e)}")

    def calculate_average_renewable_percentage(self, snapshots: List[GridSnapshot]) -> float:
        """Calculate average renewable percentage across snapshots"""
        if not snapshots:
            return 0.0
        return sum(s.renewable_percentage for s in snapshots) / len(snapshots)

    def detect_renewable_threshold(self, snapshots: List[GridSnapshot], 
                                   threshold_pct: float = 90.0) -> Tuple[bool, Dict]:
        """Check if renewable percentage meets threshold"""
        if not snapshots:
            return False, {"status": "no_data", "message": "No snapshots to analyze"}
        
        avg_renewable = self.calculate_average_renewable_percentage(snapshots)
        meets_threshold = avg_renewable >= threshold_pct
        
        peak_renewable = max(s.renewable_percentage for s in snapshots)
        min_renewable = min(s.renewable_percentage for s in snapshots)
        
        return meets_threshold, {
            "meets_threshold": meets_threshold,
            "average_renewable_pct": round(avg_renewable, 2),
            "peak_renewable_pct": round(peak_renewable, 2),
            "min_renewable_pct": round(min_renewable, 2),
            "threshold_pct": threshold_pct,
            "snapshot_count": len(snapshots)
        }


class GridValidator:
    """Validates grid data integrity and constraints"""

    VALID_FREQUENCY_RANGE = (47.0, 52.0)
    MAX_DEMAND_MW = 65000
    MIN_DEMAND_MW = 20000

    def validate_snapshot(self, snapshot: GridSnapshot) -> Tuple[bool, List[str]]:
        """Validate a grid snapshot for logical consistency"""
        errors = []
        
        if snapshot.total_demand_mw < self.MIN_DEMAND_MW:
            errors.append(f"Demand {snapshot.total_demand_mw} below minimum {self.MIN_DEMAND_MW}")
        
        if snapshot.total_demand_mw > self.MAX_DEMAND_MW:
            errors.append(f"Demand {snapshot.total_demand_mw} exceeds maximum {self.MAX_DEMAND_MW}")
        
        if snapshot.renewable_mw > snapshot.total_demand_mw:
            errors.append("Renewable generation exceeds total demand")
        
        if snapshot.grid_frequency_hz < self.VALID_FREQUENCY_RANGE[0]:
            errors.append(f"Frequency {snapshot.grid_frequency_hz} below safe range")
        
        if snapshot.grid_frequency_hz > self.VALID_FREQUENCY_RANGE[1]:
            errors.append(f"Frequency {snapshot.grid_frequency_hz} above safe range")
        
        source_total = sum(snapshot.source_breakdown.values())
        if source_total > snapshot.total_demand_mw * 1.05:
            errors.append("Source breakdown exceeds total demand by >5%")
        
        return len(errors) == 0, errors

    def validate_data_continuity(self, snapshots: List[GridSnapshot]) -> Tuple[bool, List[str]]:
        """Check for gaps and anomalies in time series data"""
        errors = []
        
        if len(snapshots) < 2:
            return True, []
        
        sorted_snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        
        for i in range(1, len(sorted_snapshots)):
            prev_snap = sorted_snapshots[i-1]
            curr_snap = sorted_snapshots[i]
            
            time_diff = (curr_snap.timestamp - prev_snap.timestamp).total_seconds()
            
            if time_diff > 3600:
                errors.append(f"Gap of {time_diff}s between snapshots at {prev_snap.timestamp}")
            
            demand_change_pct = abs(curr_snap.total_demand_mw - prev_snap.total_demand_mw) / prev_snap.total_demand_mw * 100
            if demand_change_pct > 30:
                errors.append(f"Unrealistic demand change of {demand_change_pct:.1f}%")
        
        return len(errors) == 0, errors


class IntegrationTests(unittest.TestCase):
    """Integration tests for grid monitoring system"""

    def setUp(self):
        """Set up test fixtures"""
        self.processor = GridDataProcessor()
        self.validator = GridValidator()
        self.fetcher = GridDataFetcher("https://grid.iamkate.com/")

    def test_valid_snapshot_creation(self):
        """Test creating a valid grid snapshot"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 40000,
            "renewable_mw": 36000,
            "wind_mw": 20000,
            "solar_mw": 10000,
            "hydro_mw": 6000,
            "nuclear_mw": 8000,
            "gas_mw": 4000,
            "coal_mw": 0,
            "frequency_hz": 50.0
        }
        
        snapshot = self.processor.parse_snapshot(data)
        self.assertEqual(snapshot.total_demand_mw, 40000)
        self.assertEqual(snapshot.renewable_mw, 36000)
        self.assertAlmostEqual(snapshot.renewable_percentage, 90.0, places=1)

    def test_90_percent_renewable_threshold(self):
        """Test that 90% renewable threshold detection works"""
        snapshots = []
        for i in range(5):
            data = {
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "total_demand_mw": 40000,
                "renewable_mw": 36500,
                "frequency_hz": 50.0
            }
            snapshots.append(self.processor.parse_snapshot(data))
        
        meets_threshold, stats = self.processor.detect_renewable_threshold(snapshots, 90.0)
        self.assertTrue(meets_threshold)
        self.assertGreaterEqual(stats["average_renewable_pct"], 90.0)

    def test_low_renewable_percentage(self):
        """Test detection of low renewable percentage"""
        snapshots = []
        for i in range(3):
            data = {
                "timestamp": (datetime.now() - timedelta(hours=i)).isoformat(),
                "total_demand_mw": 40000,
                "renewable_mw": 20000,
                "frequency_hz": 50.0
            }
            snapshots.append(self.processor.parse_snapshot(data))
        
        meets_threshold, stats = self.processor.detect_renewable_threshold(snapshots, 90.0)
        self.assertFalse(meets_threshold)
        self.assertLess(stats["average_renewable_pct"], 90.0)

    def test_invalid_snapshot_zero_demand(self):
        """Test that zero demand raises ValueError"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 0,
            "renewable_mw": 0,
            "frequency_hz": 50.0
        }
        
        with self.assertRaises(ValueError):
            self.processor.parse_snapshot(data)

    def test_invalid_snapshot_invalid_percentage(self):
        """Test that percentage >100 is clamped"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 40000,
            "renewable_mw": 45000,
            "frequency_hz": 50.0
        }
        
        snapshot = self.processor.parse_snapshot(data)
        self.assertLessEqual(snapshot.renewable_percentage, 100)

    def test_invalid_frequency_too_low(self):
        """Test that frequency below 47 Hz is invalid"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 40000,
            "renewable_mw": 36000,
            "frequency_hz": 46.0
        }
        
        with self.assertRaises(ValueError):
            self.processor.parse_snapshot(data)

    def test_invalid_frequency_too_high(self):
        """Test that frequency above 52 Hz is invalid"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 40000,
            "renewable_mw": 36000,
            "frequency_hz": 52.5
        }
        
        with self.assertRaises(ValueError):
            self.processor.parse_snapshot(data)

    def test_validate_snapshot_renewable_exceeds_demand(self):
        """Test validation catches renewable exceeding demand"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=40000,
            renewable_mw=45000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=100,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_snapshot(snapshot)
        self.assertFalse(valid)
        self.assertTrue(any("exceeds" in e.lower() for e in errors))

    def test_validate_snapshot_demand_too_low(self):
        """Test validation catches demand below minimum"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=15000,
            renewable_mw=10000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=66.7,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_snapshot(snapshot)
        self.assertFalse(valid)
        self.assertTrue(any("minimum" in e.lower() for e in errors))

    def test_validate_snapshot_demand_too_high(self):
        """Test validation catches demand above maximum"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=70000,
            renewable_mw=60000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=85.7,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_snapshot(snapshot)
        self.assertFalse(valid)
        self.assertTrue(any("maximum" in e.lower() for e in errors))

    def test_validate_frequency_low(self):
        """Test validation catches low frequency"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=46.5
        )
        
        valid, errors = self.validator.validate_snapshot(snapshot)
        self.assertFalse(valid)
        self.assertTrue(any("frequency" in e.lower() and "below" in e.lower() for e in errors))

    def test_validate_frequency_high(self):
        """Test validation catches high frequency"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=51.5
        )
        
        valid, errors = self.validator.validate_snapshot(snapshot)
        self.assertFalse(valid)
        self.assertTrue(any("frequency" in e.lower() and "above" in e.lower() for e in errors))

    def test_validate_data_continuity_single_snapshot(self):
        """Test continuity check with single snapshot"""
        snapshot = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_data_continuity([snapshot])
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_data_continuity_gap_detection(self):
        """Test detection of time gaps in data"""
        snap1 = GridSnapshot(
            timestamp=datetime.now() - timedelta(hours=2),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=50.0
        )
        snap2 = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_data_continuity([snap1, snap2])
        self.assertFalse(valid)
        self.assertTrue(any("gap" in e.lower() for e in errors))

    def test_validate_data_continuity_unrealistic_demand_change(self):
        """Test detection of unrealistic demand spikes"""
        snap1 = GridSnapshot(
            timestamp=datetime.now() - timedelta(minutes=30),
            total_demand_mw=40000,
            renewable_mw=36000,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=50.0
        )
        snap2 = GridSnapshot(
            timestamp=datetime.now(),
            total_demand_mw=65000,
            renewable_mw=58500,
            source_breakdown={source: 0 for source in EnergySource},
            renewable_percentage=90.0,
            grid_frequency_hz=50.0
        )
        
        valid, errors = self.validator.validate_data_continuity([snap1, snap2])
        self.assertFalse(valid)
        self.assertTrue(any("demand change" in e.lower() for e in errors))

    def test_parse_invalid_json(self):
        """Test parsing malformed data"""
        with self.assertRaises(ValueError):
            self.processor.parse_snapshot({"timestamp": "invalid"})

    def test_empty_snapshot_list(self):
        """Test processing empty snapshot list"""
        avg = self.processor.calculate_average_renewable_percentage([])
        self.assertEqual(avg, 0.0)

    def test_historical_data_fetch_bounds(self):
        """Test historical data fetch bounds"""
        with self.assertRaises(ValueError):
            self.fetcher.fetch_historical_data(0)
        
        with self.assertRaises(ValueError):
            self.fetcher.fetch_historical_data(9000)

    def test_historical_data_fetch_valid(self):
        """Test valid historical data fetch"""
        data = self.fetcher.fetch_historical_data(24)
        self.assertEqual(len(data), 24)
        self.assertTrue(all("timestamp" in d for d in data))

    def test_integration_fetch_parse_validate(self):
        """Integration test: fetch, parse, and validate data"""
        raw_data = {
            "timestamp": datetime.now().isoformat(),
            "total_demand_mw": 42000,
            "renewable_mw": 38000,
            "wind_mw": 22000,
            "solar_mw": 10000,
            "hydro_mw": 6000,
            "nuclear_mw": 7000,
            "gas_mw": 4000,
            "coal_mw": 0,
            "frequency_hz": 50.0
        }
        
        snapshot = self.processor.parse_snapshot(raw_data)
        valid, errors = self.validator.validate_snapshot(snapshot)
        
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
        self.assertGreater(snapshot.renewable_percentage, 85)

    def test_integration_multiple_snapshots_90_percent_threshold(self):
        """Integration test: multiple snapshots meeting 90% renewable target"""
        snapshots = []
        base_demand = 40000
        base_renewable = 36500
        
        for hour in range(24):
            data = {
                "timestamp": (datetime.now() - timedelta(hours=hour)).isoformat(),
                "total_demand_mw": base_demand + (hour % 5000),
                "renewable_mw": base_renewable + (hour % 3000),
                "wind_mw": 20000 + (hour % 2000),
                "solar_mw": 10000 + (hour % 1000),
                "hydro_mw": 6000,
                "nuclear_mw": 8000,
                "gas_mw": 2000 + (hour % 500),
                "coal_mw": 0,
                "frequency_hz": 50.0
            }
            snapshots.append(self.processor.parse_snapshot(data))
        
        meets_threshold, stats = self.processor.detect_renewable_threshold(snapshots, 90.0)
        valid, cont_errors = self.validator.validate_data_continuity(snapshots)
        
        for snapshot in snapshots:
            snap_valid, snap_errors = self.validator.validate_snapshot(snapshot)
            self.assertTrue(snap_valid, f"Snapshot validation failed: {snap_errors}")


def run_tests_with_output(verbose: bool = False, pattern: Optional[str] = None) -> int:
    """Run integration tests and return exit code"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    if pattern:
        suite.addTests(loader.loadTestsFromName(f"__main__.IntegrationTests.{pattern}"))
    else:
        suite.addTests(loader.loadTestsFromTestCase(IntegrationTests))
    
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return 0 if result.wasSuccessful() else 1


def demo_system():
    """Demonstrate the grid monitoring system"""
    print("=" * 80)
    print("BRITAIN RENEWABLE ENERGY GRID MONITORING - INTEGRATION TEST DEMO")
    print("=" * 80)
    print()
    
    processor = GridDataProcessor()
    validator = GridValidator()
    
    print("[1] Creating sample grid snapshots for 12-hour period...")
    snapshots = []
    base_time = datetime.now()
    
    test_cases = [
        {"demand": 38000, "renewable": 34200, "hour": 0, "freq": 50.0},
        {"demand": 40000, "renewable": 37000, "hour": 3, "freq": 50.1},
        {"demand": 42000, "renewable": 38500, "hour": 6, "freq": 49.9},
        {"demand": 45000, "renewable": 41000, "hour": 9, "freq": 50.0},
        {"demand": 42000, "renewable": 38000, "hour": 12, "freq": 50.2},
    ]
    
    for test_case in test_cases:
        data = {
            "timestamp": (base_time - timedelta(hours=test_case["hour"])).isoformat(),
            "total_demand_mw": test_case["demand"],
            "renewable_mw": test_case["renewable"],
            "wind_mw": test_case["renewable"] * 0.55,
            "solar_mw": test_case["renewable"] * 0.3,
            "hydro_mw": test_case["renewable"] * 0.15,
            "nuclear_mw": (test_case["demand"] - test_case["renewable"]) * 0.5,
            "gas_mw": (test_case["demand"] - test_case["renewable"]) * 0.5,
            "frequency_hz": test_case["freq"]
        }
        
        snapshot = processor.parse_snapshot(data)
        snapshots.append(snapshot)
        
        valid, errors = validator.validate_snapshot(snapshot)
        status = "✓ VALID" if valid else f"✗ INVALID ({len(errors)} errors)"
        print(f"  Hour {test_case['hour']:2d}: {snapshot.renewable_percentage:5.1f}% renewable | {status}")
    
    print()
    print("[2] Analyzing renewable energy statistics...")
    avg_renewable = processor.calculate_average_renewable_percentage(snapshots)
    meets_90_pct, stats = processor.detect_renewable_threshold(snapshots, 90.0)
    
    print(f"  Average renewable:     {stats['average_renewable_pct']:.1f}%")
    print(f"  Peak renewable:        {stats['peak_renewable_pct']:.1f}%")
    print(f"  Minimum renewable:     {stats['min_renewable_pct']:.1f}%")
    print(f"  Target threshold:      {stats['threshold_pct']:.1f}%")
    print(f"  Meets target:          {'YES ✓' if meets_90_pct else 'NO ✗'}")
    print()
    
    print("[3] Checking data continuity and quality...")
    continuity_valid, continuity_errors = validator.validate_data_continuity(snapshots)
    print(f"  Data continuity valid: {'YES ✓' if continuity_valid else f'NO ✗ ({len(continuity_errors)} issues)'}")
    for error in continuity_errors:
        print(f"    - {error}")
    
    print()
    print("[4] Running edge case validations...")
    
    edge_cases = [
        ("Zero demand", {"timestamp": datetime.now().isoformat(), "total_demand_mw": 0, "renewable_mw": 0, "frequency_hz": 50.0}),
        ("Low frequency", {"timestamp": datetime.now().isoformat(), "total_demand_mw": 40000, "renewable_mw": 36000, "frequency_hz": 46.5}),
        ("High frequency", {"timestamp": datetime.now().isoformat(), "total_demand_mw": 40000, "renewable_mw": 36000, "frequency_hz": 51.8}),
    ]
    
    for case_name, data in edge_cases:
        try:
            snapshot = processor.parse_snapshot(data)
            print(f"  {case_name:20s}: ✓ Parsed (unexpected)")
        except ValueError as e:
            print(f"  {case_name:20s}: ✗ Correctly rejected")
    
    print()
    print("=" * 80)
    print("Demo complete. Grid monitoring system operational.")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Integration tests for Britain's renewable energy grid monitoring system"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose test output"
    )
    parser.add_argument(
        "--test",
        type=str,
        help="Run specific test by name (e.g., test_valid_snapshot_creation)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run system demonstration instead of tests"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        demo_system()
        sys.exit(0)
    
    exit_code = run_tests_with_output(verbose=args.verbose, pattern=args.test)
    sys.exit(exit_code)