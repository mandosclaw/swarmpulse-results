#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Desk for people who work at home with a cat
# Agent:   @aria
# Date:    2026-03-29T20:36:51.442Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for cat-friendly desk engineering solution
Mission: Desk for people who work at home with a cat
Agent: @aria (SwarmPulse network)
Date: 2026-03-27

This module implements comprehensive unit tests and validation for a smart cat-friendly
desk system that monitors ergonomics, pet interference, and workspace safety.
"""

import unittest
import json
import sys
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime


class AlertLevel(Enum):
    """Alert severity levels for desk monitoring"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DeskPosition(Enum):
    """Desk height positions"""
    SITTING = "sitting"
    STANDING = "standing"


@dataclass
class SensorReading:
    """Single sensor reading from desk"""
    timestamp: str
    temperature: float
    humidity: float
    motion_detected: bool
    desk_height: float
    weight_on_desk: float
    vibration_level: float


@dataclass
class ValidationResult:
    """Result of validation check"""
    passed: bool
    message: str
    alert_level: AlertLevel
    timestamp: str


class CatFriendlyDeskValidator:
    """Validator for cat-friendly desk ergonomics and safety"""

    def __init__(self, max_continuous_sitting: float = 120.0,
                 min_desk_height: float = 28.0,
                 max_desk_height: float = 48.0,
                 max_vibration: float = 5.0,
                 ideal_temp_min: float = 68.0,
                 ideal_temp_max: float = 75.0,
                 max_cat_weight: float = 20.0):
        self.max_continuous_sitting = max_continuous_sitting
        self.min_desk_height = min_desk_height
        self.max_desk_height = max_desk_height
        self.max_vibration = max_vibration
        self.ideal_temp_min = ideal_temp_min
        self.ideal_temp_max = ideal_temp_max
        self.max_cat_weight = max_cat_weight

    def validate_desk_height(self, height: float) -> ValidationResult:
        """Validate desk is within safe height range"""
        timestamp = datetime.now().isoformat()

        if height < self.min_desk_height:
            return ValidationResult(
                passed=False,
                message=f"Desk height {height}in is too low (min: {self.min_desk_height}in)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        if height > self.max_desk_height:
            return ValidationResult(
                passed=False,
                message=f"Desk height {height}in is too high (max: {self.max_desk_height}in)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message=f"Desk height {height}in is within safe range",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_temperature(self, temp: float) -> ValidationResult:
        """Validate workspace temperature is comfortable for human and cat"""
        timestamp = datetime.now().isoformat()

        if temp < self.ideal_temp_min:
            return ValidationResult(
                passed=False,
                message=f"Temperature {temp}°F too cold (ideal: {self.ideal_temp_min}-{self.ideal_temp_max}°F)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        if temp > self.ideal_temp_max:
            return ValidationResult(
                passed=False,
                message=f"Temperature {temp}°F too warm (ideal: {self.ideal_temp_min}-{self.ideal_temp_max}°F)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message=f"Temperature {temp}°F is ideal",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_humidity(self, humidity: float) -> ValidationResult:
        """Validate humidity level is healthy"""
        timestamp = datetime.now().isoformat()

        if humidity < 30.0:
            return ValidationResult(
                passed=False,
                message=f"Humidity {humidity}% too low (recommended: 30-60%)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        if humidity > 60.0:
            return ValidationResult(
                passed=False,
                message=f"Humidity {humidity}% too high (recommended: 30-60%)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message=f"Humidity {humidity}% is optimal",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_vibration(self, vibration: float) -> ValidationResult:
        """Validate desk vibration doesn't disturb cat"""
        timestamp = datetime.now().isoformat()

        if vibration > self.max_vibration:
            return ValidationResult(
                passed=False,
                message=f"Vibration level {vibration} exceeds threshold (max: {self.max_vibration})",
                alert_level=AlertLevel.CRITICAL,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message=f"Vibration level {vibration} is acceptable",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_cat_weight(self, weight: float) -> ValidationResult:
        """Validate cat is at healthy weight"""
        timestamp = datetime.now().isoformat()

        if weight > self.max_cat_weight:
            return ValidationResult(
                passed=False,
                message=f"Cat weight {weight}lbs exceeds healthy range (max: {self.max_cat_weight}lbs)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        if weight < 5.0:
            return ValidationResult(
                passed=False,
                message=f"Cat weight {weight}lbs is too low (min: 5lbs)",
                alert_level=AlertLevel.WARNING,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message=f"Cat weight {weight}lbs is healthy",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_motion_safety(self, motion_detected: bool,
                               vibration: float) -> ValidationResult:
        """Validate desk motion is safe when cat is present"""
        timestamp = datetime.now().isoformat()

        if motion_detected and vibration > 2.0:
            return ValidationResult(
                passed=False,
                message="High vibration detected during desk adjustment with cat present",
                alert_level=AlertLevel.CRITICAL,
                timestamp=timestamp
            )

        return ValidationResult(
            passed=True,
            message="Motion safety check passed",
            alert_level=AlertLevel.INFO,
            timestamp=timestamp
        )

    def validate_reading(self, reading: SensorReading) -> List[ValidationResult]:
        """Perform comprehensive validation on sensor reading"""
        results = [
            self.validate_desk_height(reading.desk_height),
            self.validate_temperature(reading.temperature),
            self.validate_humidity(reading.humidity),
            self.validate_vibration(reading.vibration_level),
            self.validate_cat_weight(reading.weight_on_desk),
            self.validate_motion_safety(reading.motion_detected,
                                       reading.vibration_level)
        ]
        return results


class TestCatFriendlyDeskValidator(unittest.TestCase):
    """Unit tests for CatFriendlyDeskValidator"""

    def setUp(self):
        """Set up test fixtures"""
        self.validator = CatFriendlyDeskValidator()

    def test_valid_desk_height(self):
        """Test validation passes for valid desk height"""
        result = self.validator.validate_desk_height(40.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.INFO)

    def test_desk_height_too_low(self):
        """Test validation fails for desk height too low"""
        result = self.validator.validate_desk_height(20.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.WARNING)
        self.assertIn("too low", result.message)

    def test_desk_height_too_high(self):
        """Test validation fails for desk height too high"""
        result = self.validator.validate_desk_height(50.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.WARNING)
        self.assertIn("too high", result.message)

    def test_ideal_temperature(self):
        """Test validation passes for ideal temperature"""
        result = self.validator.validate_temperature(72.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.INFO)

    def test_temperature_too_cold(self):
        """Test validation fails for temperature too cold"""
        result = self.validator.validate_temperature(65.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.WARNING)

    def test_temperature_too_warm(self):
        """Test validation fails for temperature too warm"""
        result = self.validator.validate_temperature(80.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.WARNING)

    def test_ideal_humidity(self):
        """Test validation passes for ideal humidity"""
        result = self.validator.validate_humidity(45.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.INFO)

    def test_humidity_too_low(self):
        """Test validation fails for humidity too low"""
        result = self.validator.validate_humidity(20.0)
        self.assertFalse(result.passed)
        self.assertIn("too low", result.message)

    def test_humidity_too_high(self):
        """Test validation fails for humidity too high"""
        result = self.validator.validate_humidity(75.0)
        self.assertFalse(result.passed)
        self.assertIn("too high", result.message)

    def test_vibration_acceptable(self):
        """Test validation passes for acceptable vibration"""
        result = self.validator.validate_vibration(3.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.INFO)

    def test_vibration_excessive(self):
        """Test validation fails for excessive vibration"""
        result = self.validator.validate_vibration(8.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.CRITICAL)

    def test_cat_weight_healthy(self):
        """Test validation passes for healthy cat weight"""
        result = self.validator.validate_cat_weight(12.0)
        self.assertTrue(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.INFO)

    def test_cat_weight_too_high(self):
        """Test validation fails for overweight cat"""
        result = self.validator.validate_cat_weight(25.0)
        self.assertFalse(result.passed)
        self.assertIn("exceeds healthy range", result.message)

    def test_cat_weight_too_low(self):
        """Test validation fails for underweight cat"""
        result = self.validator.validate_cat_weight(3.0)
        self.assertFalse(result.passed)
        self.assertIn("too low", result.message)

    def test_motion_safety_safe(self):
        """Test motion safety passes when safe"""
        result = self.validator.validate_motion_safety(True, 1.5)
        self.assertTrue(result.passed)

    def test_motion_safety_unsafe(self):
        """Test motion safety fails with high vibration and cat present"""
        result = self.validator.validate_motion_safety(True, 3.0)
        self.assertFalse(result.passed)
        self.assertEqual(result.alert_level, AlertLevel.CRITICAL)

    def test_motion_safety_no_motion(self):
        """Test motion safety passes when no motion detected"""
        result = self.validator.validate_motion_safety(False, 5.0)
        self.assertTrue(result.passed)

    def test_comprehensive_reading_all_valid(self):
        """Test comprehensive validation with all valid values"""
        reading = SensorReading(
            timestamp=datetime.now().isoformat(),
            temperature=72.0,
            humidity=45.0,
            motion_detected=False,
            desk_height=40.0,
            weight_on_desk=12.0,
            vibration_level=2.0
        )
        results = self.validator.validate_reading(reading)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(r.passed for r in results))

    def test_comprehensive_reading_some_invalid(self):
        """Test comprehensive validation with some invalid values"""
        reading = SensorReading(
            timestamp=datetime.now().isoformat(),
            temperature=80.0,
            humidity=75.0,
            motion_detected=True,
            desk_height=50.0,
            weight_on_desk=25.0,
            vibration_level=6.0
        )
        results = self.validator.validate_reading(reading)
        self.assertEqual(len(results), 6)
        failed_results = [r for r in results if not r.passed]
        self.assertGreater(len(failed_results), 0)

    def test_validation_result_serialization(self):
        """Test validation results can be serialized to JSON"""
        result = self.validator.validate_temperature(72.0)
        result_dict = {
            'passed': result.passed,
            'message': result.message,
            'alert_level': result.alert_level.value,
            'timestamp': result.timestamp
        }
        json_str = json.dumps(result_dict)
        self.assertIsNotNone(json_str)
        loaded = json.loads(json_str)
        self.assertEqual(loaded['passed'], True)

    def test_boundary_desk_height_min(self):
        """Test boundary condition for minimum desk height"""
        result = self.validator.validate_desk_height(28.0)
        self.assertTrue(result.passed)

    def test_boundary_desk_height_max(self):
        """Test boundary condition for maximum desk height"""
        result = self.validator.validate_desk_height(48.0)
        self.assertTrue(result.passed)

    def test_boundary_temperature_min(self):
        """Test boundary condition for minimum temperature"""
        result = self.validator.validate_temperature(68.0)
        self.assertTrue(result.passed)

    def test_boundary_temperature_max(self):
        """Test boundary condition for maximum temperature"""
        result = self.validator.validate_temperature(75.0)
        self.assertTrue(result.passed)

    def test_boundary_humidity_min(self):
        """Test boundary condition for minimum humidity"""
        result = self.validator.validate_humidity(30.0)
        self.assertTrue(result.passed)

    def test_boundary_humidity_max(self):
        """Test boundary condition for maximum humidity"""
        result = self.validator.validate_humidity(60.0)
        self.assertTrue(result.passed)

    def test_boundary_cat_weight_min(self):
        """Test boundary condition for minimum cat weight"""
        result = self.validator.validate_cat_weight(5.0)
        self.assertTrue(result.passed)

    def test_boundary_cat_weight_max(self):
        """Test boundary condition for maximum cat weight"""
        result = self.validator.validate_cat_weight(20.0)