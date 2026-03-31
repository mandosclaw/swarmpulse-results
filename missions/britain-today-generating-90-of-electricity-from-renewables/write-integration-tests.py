#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests
# Mission: Britain today generating 90%+ of electricity from renewables
# Agent:   @aria
# Date:    2026-03-31T19:33:04.087Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration Tests for Britain Renewable Electricity Generation Monitoring
Mission: Britain today generating 90%+ of electricity from renewables
Category: AI/ML
Agent: @aria
Date: 2024
Task: Write integration tests covering edge cases and failure modes
"""

import unittest
import json
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
import argparse
import random


class RenewableEnergyDataFetcher:
    """Fetches and validates renewable energy generation data"""
    
    def __init__(self, api_endpoint=None, timeout=10):
        self.api_endpoint = api_endpoint or "https://grid.iamkate.com/api/generation"
        self.timeout = timeout
        self.last_fetch_time = None
        self.cache = {}
    
    def fetch_current_generation(self):
        """Fetch current generation data"""
        try:
            import urllib.request
            import json
            
            req = urllib.request.Request(self.api_endpoint)
            req.add_header('User-Agent', 'RenewableEnergyMonitor/1.0')
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode())
                self.last_fetch_time = datetime.now()
                self.cache['last_data'] = data
                return data
        except Exception as e:
            raise ConnectionError(f"Failed to fetch data: {str(e)}")
    
    def calculate_renewable_percentage(self, generation_data):
        """Calculate percentage of electricity from renewables"""
        if not generation_data or 'sources' not in generation_data:
            raise ValueError("Invalid generation data format")
        
        sources = generation_data.get('sources', {})
        renewable_types = ['wind', 'solar', 'hydro', 'biomass', 'wave', 'tidal']
        
        total_generation = sum(sources.values())
        if total_generation == 0:
            raise ValueError("Total generation cannot be zero")
        
        renewable_generation = sum(
            sources.get(source, 0) for source in renewable_types
        )
        
        percentage = (renewable_generation / total_generation) * 100
        return round(percentage, 2)
    
    def validate_data_freshness(self, timestamp_str):
        """Validate that data is recent (within 30 minutes)"""
        try:
            data_time = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - data_time
            max_age = timedelta(minutes=30)
            return age <= max_age
        except Exception:
            return False


class RenewableEnergyMonitor:
    """Monitors renewable energy generation and alerts on thresholds"""
    
    def __init__(self, target_percentage=90.0, alert_threshold=85.0):
        self.target_percentage = target_percentage
        self.alert_threshold = alert_threshold
        self.alerts = []
        self.history = []
    
    def check_generation(self, current_percentage):
        """Check current generation against thresholds"""
        if current_percentage < 0 or current_percentage > 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'percentage': current_percentage,
            'status': 'optimal' if current_percentage >= self.target_percentage else 'acceptable',
            'alert': False,
            'message': ''
        }
        
        if current_percentage >= self.target_percentage:
            result['status'] = 'optimal'
            result['message'] = f'Target achieved: {current_percentage}% >= {self.target_percentage}%'
        elif current_percentage >= self.alert_threshold:
            result['status'] = 'acceptable'
            result['message'] = f'Above alert threshold: {current_percentage}%'
        else:
            result['status'] = 'alert'
            result['alert'] = True
            result['message'] = f'Below alert threshold: {current_percentage}% < {self.alert_threshold}%'
            self.alerts.append(result)
        
        self.history.append(result)
        return result
    
    def get_statistics(self):
        """Calculate statistics from history"""
        if not self.history:
            return None
        
        percentages = [h['percentage'] for h in self.history]
        return {
            'count': len(percentages),
            'average': round(sum(percentages) / len(percentages), 2),
            'min': min(percentages),
            'max': max(percentages),
            'alerts_triggered': len(self.alerts)
        }


class TestRenewableEnergyFetcher(unittest.TestCase):
    """Test suite for RenewableEnergyDataFetcher"""
    
    def setUp(self):
        self.fetcher = RenewableEnergyDataFetcher()
    
    def test_calculate_renewable_percentage_valid_data(self):
        """Test calculation with valid generation data"""
        data = {
            'sources': {
                'wind': 50,
                'solar': 30,
                'gas': 15,
                'coal': 5
            }
        }
        percentage = self.fetcher.calculate_renewable_percentage(data)
        self.assertEqual(percentage, 80.0)
    
    def test_calculate_renewable_percentage_100_percent_renewable(self):
        """Test when all generation is from renewables"""
        data = {
            'sources': {
                'wind': 40,
                'solar': 35,
                'hydro': 25
            }
        }
        percentage = self.fetcher.calculate_renewable_percentage(data)
        self.assertEqual(percentage, 100.0)
    
    def test_calculate_renewable_percentage_zero_renewable(self):
        """Test when no renewable generation"""
        data = {
            'sources': {
                'gas': 50,
                'coal': 50,
                'nuclear': 0
            }
        }
        percentage = self.fetcher.calculate_renewable_percentage(data)
        self.assertEqual(percentage, 0.0)
    
    def test_calculate_renewable_percentage_with_unknown_sources(self):
        """Test calculation ignores unknown renewable types"""
        data = {
            'sources': {
                'wind': 50,
                'solar': 30,
                'fusion': 10,
                'gas': 10
            }
        }
        percentage = self.fetcher.calculate_renewable_percentage(data)
        self.assertEqual(percentage, 80.0)
    
    def test_calculate_renewable_percentage_zero_total_generation(self):
        """Test error handling for zero total generation"""
        data = {'sources': {}}
        with self.assertRaises(ValueError):
            self.fetcher.calculate_renewable_percentage(data)
    
    def test_calculate_renewable_percentage_missing_sources_key(self):
        """Test error handling for missing sources key"""
        data = {}
        with self.assertRaises(ValueError):
            self.fetcher.calculate_renewable_percentage(data)
    
    def test_calculate_renewable_percentage_none_data(self):
        """Test error handling for None input"""
        with self.assertRaises(ValueError):
            self.fetcher.calculate_renewable_percentage(None)
    
    def test_validate_data_freshness_recent_data(self):
        """Test validation of recent data"""
        recent_time = (datetime.now() - timedelta(minutes=10)).isoformat()
        self.assertTrue(self.fetcher.validate_data_freshness(recent_time))
    
    def test_validate_data_freshness_old_data(self):
        """Test validation fails for stale data"""
        old_time = (datetime.now() - timedelta(minutes=45)).isoformat()
        self.assertFalse(self.fetcher.validate_data_freshness(old_time))
    
    def test_validate_data_freshness_exactly_30_minutes(self):
        """Test boundary condition at 30 minutes"""
        boundary_time = (datetime.now() - timedelta(minutes=30)).isoformat()
        self.assertTrue(self.fetcher.validate_data_freshness(boundary_time))
    
    def test_validate_data_freshness_invalid_timestamp(self):
        """Test error handling for invalid timestamp"""
        self.assertFalse(self.fetcher.validate_data_freshness("invalid"))
    
    @patch('urllib.request.urlopen')
    def test_fetch_current_generation_success(self, mock_urlopen):
        """Test successful data fetch"""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            'wind': 40,
            'solar': 30
        }).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        result = self.fetcher.fetch_current_generation()
        self.assertIsNotNone(result)
    
    @patch('urllib.request.urlopen')
    def test_fetch_current_generation_timeout(self, mock_urlopen):
        """Test timeout handling"""
        mock_urlopen.side_effect = Exception("Connection timeout")
        with self.assertRaises(ConnectionError):
            self.fetcher.fetch_current_generation()


class TestRenewableEnergyMonitor(unittest.TestCase):
    """Test suite for RenewableEnergyMonitor"""
    
    def setUp(self):
        self.monitor = RenewableEnergyMonitor(target_percentage=90.0, alert_threshold=85.0)
    
    def test_check_generation_optimal(self):
        """Test optimal generation state"""
        result = self.monitor.check_generation(95.0)
        self.assertEqual(result['status'], 'optimal')
        self.assertFalse(result['alert'])
    
    def test_check_generation_acceptable(self):
        """Test acceptable generation state"""
        result = self.monitor.check_generation(87.5)
        self.assertEqual(result['status'], 'acceptable')
        self.assertFalse(result['alert'])
    
    def test_check_generation_alert(self):
        """Test alert state triggered"""
        result = self.monitor.check_generation(80.0)
        self.assertEqual(result['status'], 'alert')
        self.assertTrue(result['alert'])
    
    def test_check_generation_boundary_target(self):
        """Test boundary at target percentage"""
        result = self.monitor.check_generation(90.0)
        self.assertEqual(result['status'], 'optimal')
    
    def test_check_generation_boundary_alert(self):
        """Test boundary at alert threshold"""
        result = self.monitor.check_generation(85.0)
        self.assertEqual(result['status'], 'acceptable')
    
    def test_check_generation_zero_percent(self):
        """Test zero renewable percentage"""
        result = self.monitor.check_generation(0.0)
        self.assertTrue(result['alert'])
    
    def test_check_generation_100_percent(self):
        """Test 100% renewable percentage"""
        result = self.monitor.check_generation(100.0)
        self.assertEqual(result['status'], 'optimal')
    
    def test_check_generation_negative_percent(self):
        """Test error handling for negative percentage"""
        with self.assertRaises(ValueError):
            self.monitor.check_generation(-5.0)
    
    def test_check_generation_over_100_percent(self):
        """Test error handling for percentage > 100"""
        with self.assertRaises(ValueError):
            self.monitor.check_generation(105.0)
    
    def test_alert_accumulation(self):
        """Test that alerts accumulate over time"""
        self.monitor.check_generation(80.0)
        self.monitor.check_generation(75.0)
        self.monitor.check_generation(70.0)
        self.assertEqual(len(self.monitor.alerts), 3)
    
    def test_history_tracking(self):
        """Test history accumulation"""
        self.monitor.check_generation(95.0)
        self.monitor.check_generation(87.0)
        self.monitor.check_generation(82.0)
        self.assertEqual(len(self.monitor.history), 3)
    
    def test_get_statistics_empty_history(self):
        """Test statistics with empty history"""
        stats = self.monitor.get_statistics()
        self.assertIsNone(stats)
    
    def test_get_statistics_single_entry(self):
        """Test statistics with single entry"""
        self.monitor.check_generation(92.0)
        stats = self.monitor.get_statistics()
        self.assertEqual(stats['count'], 1)
        self.assertEqual(stats['average'], 92.0)
        self.assertEqual(stats['min'], 92.0)
        self.assertEqual(stats['max'], 92.0)
    
    def test_get_statistics_multiple_entries(self):
        """Test statistics with multiple entries"""
        percentages = [95.0, 87.0, 92.0, 80.0]
        for p in percentages:
            self.monitor.check_generation(p)
        
        stats = self.monitor.get_statistics()
        self.assertEqual(stats['count'], 4)
        self.assertEqual(stats['average'], 88.5)
        self.assertEqual(stats['min'], 80.0)
        self.assertEqual(stats['max'], 95.0)
        self.assertEqual(stats['alerts_triggered'], 1)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for realistic scenarios"""
    
    def setUp(self):
        self.fetcher = RenewableEnergyDataFetcher()
        self.monitor = RenewableEnergyMonitor(target_percentage=90.0, alert_threshold=85.0)
    
    def test_end_to_end_day_scenario(self):
        """Test realistic day scenario with variable generation"""
        # Morning: low solar, increasing wind
        morning_data = {
            'sources': {
                'wind': 35,
                'solar': 5,
                'gas': 40,
                'coal': 20
            }
        }
        morning_percentage = self.fetcher.calculate_renewable_percentage(morning_data)
        morning_result = self.monitor.check_generation(morning_percentage)
        self.assertEqual(morning_result['status'], 'alert')
        
        # Midday: peak solar
        midday_data = {
            'sources': {
                'wind': 30,
                'solar': 35,
                'hydro': 15,
                'gas': 15,
                'coal': 5
            }
        }
        midday_percentage = self.fetcher.calculate_renewable_percentage(midday_data)
        midday_result = self.monitor.check_generation(midday_percentage)
        self.assertEqual(midday_result['status'], 'optimal')
        
        # Evening: wind increases, solar decreases
        evening_data = {
            'sources': {
                'wind': 50,
                'solar': 15,
                'hydro': 10,
                'gas': 20,
                'coal': 5
            }
        }
        evening_percentage = self.fetcher.calculate_renewable_percentage(evening_data)
        evening_result = self.monitor.check_generation(evening_percentage)
        self.assertEqual(evening_result['status'], 'optimal')
        
        # Verify history and statistics
        stats = self.monitor.get_statistics()
        self.assertEqual(stats['count'], 3)
        self.assertEqual(stats['alerts_triggered'], 1)
    
    def test_network_failure_recovery(self):
        """Test handling of network failures and recovery"""
        # Simulate network failure
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")
            with self.assertRaises(ConnectionError):
                self.fetcher.fetch_current_generation()
        
        # Verify monitor still works with cached/fallback data
        result = self.monitor.check_generation(88.0)
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'acceptable')
    
    def test_data_validation_chain(self):
        """Test complete validation chain"""
        valid_data = {
            'timestamp': datetime.now().isoformat(),
            'sources': {
                'wind': 40,
                'solar': 30,
                'gas': 20,
                'coal': 10
            }
        }
        
        # Validate timestamp
        is_fresh = self.fetcher.validate_data_freshness(valid_data['timestamp'])
        self.assertTrue(is_fresh)
        
        # Calculate percentage
        percentage = self.fetcher.calculate_renewable_percentage(valid_data)
        self.assertGreater(percentage, 0)
        self.assertLessEqual(percentage, 100)
        
        # Monitor the result
        result = self.monitor.check_generation(percentage)
        self.assertIn(result['status'], ['optimal', 'acceptable', 'alert'])
    
    def test_concurrent_monitoring_simulation(self):
        """Test handling multiple monitoring cycles"""
        data_sequence = [
            {'sources': {'wind': 45, 'solar': 25, 'gas': 20, 'coal': 10}},
            {'sources': {'wind': 40, 'solar': 35, 'hydro': 10, 'gas': 10, 'coal': 5}},
            {'sources': {'wind': 50, 'solar': 20, 'gas': 20, 'coal': 10}},
            {'sources': {'wind': 35, 'solar': 10, 'gas': 35, 'coal': 20}},
            {'sources': {'wind': 55, 'solar': 30, 'gas': 10, 'coal': 5}},
        ]
        
        for data in data_sequence:
            percentage = self.fetcher.calculate_renewable_percentage(data)
            self.monitor.check_generation(percentage)
        
        # Verify accumulated state
        stats = self.monitor.get_statistics()
        self.assertEqual(stats['count'], 5)
        self.assertGreater(stats['average'], 0)
        self.assertLessEqual(stats['average'], 100)


def run_tests_with_verbosity(verbosity_level=2):
    """Run all tests with specified verbosity"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestRenewableEnergyFetcher))
    suite.addTests(loader.loadTestsFromTestCase(TestRenewableEnergyMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    
    runner = unittest.TextTestRunner(verbosity=verbosity_level)
    result = runner.run(suite)
    
    return result


def generate_test_report(result):
    """Generate structured test report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'tests_run': result.testsRun,
        'failures': len(result.failures),
        'errors': len(result.errors),
        'skipped': len(result.skipped),
        'success': result.wasSuccessful(),
        'success_rate': round((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100, 2) if result.testsRun > 0 else 0
    }
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Integration tests for renewable energy monitoring system'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity level (0=quiet, 1=normal, 2=verbose)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Print JSON report of test results'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run demonstration with sample data'
    )
    
    args = parser.parse_args()
    
    if args.demo:
        print("=== Renewable Energy Monitoring Demo ===\n")
        
        fetcher = RenewableEnergyDataFetcher()
        monitor = RenewableEnergyMonitor(target_percentage=90.0, alert_threshold=85.0)
        
        # Simulate a day of monitoring
        scenarios = [
            {
                'name': 'Early Morning (Low Generation)',
                'sources': {'wind': 25, 'solar': 2, 'gas': 50, 'coal': 23}
            },
            {
                'name': 'Late Morning (Increasing Solar)',
                'sources': {'wind': 30, 'solar': 20, 'gas': 35, 'coal': 15}
            },
            {
                'name': 'Midday (Peak Solar)',
                'sources': {'wind': 28, 'solar': 40, 'hydro': 12, 'gas': 15, 'coal': 5}
            },
            {
                'name': 'Afternoon (Stable)',
                'sources': {'wind': 35, 'solar': 35, 'hydro': 10, 'gas': 15, 'coal': 5}
            },
            {
                'name': 'Evening (Decreasing Solar)',
                'sources': {'wind': 45, 'solar': 20, 'hydro': 10, 'gas': 20, 'coal': 5}
            },
            {
                'name': 'Night (Wind Dominant)',
                'sources': {'wind': 60, 'solar': 0, 'hydro': 12, 'gas': 20, 'coal': 8}
            },
        ]
        
        for scenario in scenarios:
            percentage = fetcher.calculate_renewable_percentage(scenario)
            result = monitor.check_generation(percentage)
            
            print(f"{scenario['name']}:")
            print(f"  Renewable: {percentage}%")
            print(f"  Status: {result['status'].upper()}")
            print(f"  Message: {result['message']}")
            print()
        
        stats = monitor.get_statistics()
        print("=== Daily Statistics ===")
        print(json.dumps(stats, indent=2))
        print()
    
    # Run tests
    result = run_tests_with_verbosity(args.verbosity)
    
    if args.report:
        report = generate_test_report(result)
        print("\n=== Test Report ===")
        print(json.dumps(report, indent=2))
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)