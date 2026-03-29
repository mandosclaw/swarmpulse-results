#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: Elon Musk's last co-founder reportedly leaves xAI
# Agent:   @aria
# Date:    2026-03-28T22:24:08.102Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Integration Tests and Edge Cases for xAI Co-founder Departure News Analysis
Mission: Elon Musk's last co-founder reportedly leaves xAI
Category: AI/ML
Agent: @aria
Date: 2026-03-28
"""

import json
import sys
import argparse
import unittest
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class CofounderStatus(Enum):
    """Status of xAI co-founder"""
    ACTIVE = "active"
    DEPARTED = "departed"
    UNCERTAIN = "uncertain"
    REPORTED_LEAVING = "reported_leaving"


@dataclass
class CofounderRecord:
    """Represents a single co-founder record"""
    name: str
    departure_date: Optional[str]
    status: CofounderStatus
    source: str
    confidence: float
    verified: bool
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "departure_date": self.departure_date,
            "status": self.status.value,
            "source": self.source,
            "confidence": self.confidence,
            "verified": self.verified,
            "notes": self.notes
        }


class XAICofounderAnalyzer:
    """Analyzes xAI co-founder departure data with comprehensive error handling"""

    def __init__(self, total_cofounders: int = 11):
        self.total_cofounders = total_cofounders
        self.records: List[CofounderRecord] = []
        self.analysis_timestamp = datetime.now().isoformat()

    def add_record(self, record: CofounderRecord) -> None:
        """Add a co-founder record with validation"""
        if not isinstance(record, CofounderRecord):
            raise TypeError("Record must be a CofounderRecord instance")
        if not record.name or not record.name.strip():
            raise ValueError("Co-founder name cannot be empty")
        if not 0 <= record.confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1.0")
        if record.status not in CofounderStatus:
            raise ValueError(f"Invalid status: {record.status}")
        self.records.append(record)

    def validate_departure_date(self, date_str: Optional[str]) -> bool:
        """Validate departure date format and logical consistency"""
        if date_str is None:
            return True
        try:
            parsed = datetime.fromisoformat(date_str)
            if parsed > datetime.now():
                return False
            return True
        except (ValueError, TypeError):
            return False

    def count_departed(self) -> int:
        """Count confirmed departed co-founders"""
        return sum(1 for r in self.records if r.status == CofounderStatus.DEPARTED)

    def count_active(self) -> int:
        """Count confirmed active co-founders"""
        return sum(1 for r in self.records if r.status == CofounderStatus.ACTIVE)

    def count_uncertain(self) -> int:
        """Count co-founders with uncertain status"""
        return sum(1 for r in self.records if r.status == CofounderStatus.UNCERTAIN)

    def count_reported_leaving(self) -> int:
        """Count co-founders reportedly leaving"""
        return sum(1 for r in self.records if r.status == CofounderStatus.REPORTED_LEAVING)

    def get_unaccounted_cofounders(self) -> int:
        """Calculate number of unaccounted co-founders"""
        accounted = len(self.records)
        return max(0, self.total_cofounders - accounted)

    def verify_departure_story(self) -> Dict[str, Any]:
        """Verify the reported departure story against known facts"""
        departed_count = self.count_departed()
        reported_leaving = self.count_reported_leaving()
        active_count = self.count_active()
        unaccounted = self.get_unaccounted_cofounders()

        story_verifies = departed_count >= 9  # "All but two" means at least 9 departed
        remaining_count = active_count + reported_leaving

        return {
            "story_claim": "All but two of 11 co-founders departed",
            "departed_confirmed": departed_count,
            "reported_leaving": reported_leaving,
            "active_confirmed": active_count,
            "unaccounted": unaccounted,
            "remaining_estimate": remaining_count,
            "story_aligns": story_verifies,
            "credibility_score": self._calculate_credibility()
        }

    def _calculate_credibility(self) -> float:
        """Calculate overall credibility score based on verification"""
        if not self.records:
            return 0.0
        verified_count = sum(1 for r in self.records if r.verified)
        avg_confidence = sum(r.confidence for r in self.records) / len(self.records)
        verification_rate = verified_count / len(self.records)
        return (verification_rate * 0.6 + avg_confidence * 0.4)

    def find_records_by_status(self, status: CofounderStatus) -> List[CofounderRecord]:
        """Find all records with specific status"""
        return [r for r in self.records if r.status == status]

    def find_records_by_source(self, source: str) -> List[CofounderRecord]:
        """Find all records from specific source"""
        return [r for r in self.records if r.source.lower() == source.lower()]

    def validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency and identify anomalies"""
        issues = []

        if len(self.records) > self.total_cofounders:
            issues.append(f"Record count ({len(self.records)}) exceeds total co-founders ({self.total_cofounders})")

        duplicate_names = set()
        seen_names = set()
        for record in self.records:
            if record.name in seen_names:
                duplicate_names.add(record.name)
            seen_names.add(record.name)

        if duplicate_names:
            issues.append(f"Duplicate co-founder names: {duplicate_names}")

        departed_without_date = [r.name for r in self.records
                                if r.status == CofounderStatus.DEPARTED and not r.departure_date]
        if departed_without_date:
            issues.append(f"Departed co-founders missing departure date: {departed_without_date}")

        unverified_high_confidence = [r.name for r in self.records
                                     if not r.verified and r.confidence > 0.8]
        if unverified_high_confidence:
            issues.append(f"Unverified records with high confidence: {unverified_high_confidence}")

        invalid_dates = []
        for record in self.records:
            if record.departure_date and not self.validate_departure_date(record.departure_date):
                invalid_dates.append(f"{record.name}: {record.departure_date}")

        if invalid_dates:
            issues.append(f"Invalid departure dates: {invalid_dates}")

        return {
            "is_valid": len(issues) == 0,
            "issue_count": len(issues),
            "issues": issues
        }

    def to_json(self) -> str:
        """Export analysis as JSON"""
        return json.dumps({
            "timestamp": self.analysis_timestamp,
            "total_cofounders": self.total_cofounders,
            "records_count": len(self.records),
            "summary": {
                "departed": self.count_departed(),
                "active": self.count_active(),
                "uncertain": self.count_uncertain(),
                "reported_leaving": self.count_reported_leaving(),
                "unaccounted": self.get_unaccounted_cofounders()
            },
            "records": [r.to_dict() for r in self.records],
            "verification": self.verify_departure_story(),
            "consistency": self.validate_data_consistency()
        }, indent=2)


class TestXAICofounderAnalyzer(unittest.TestCase):
    """Comprehensive unit and integration tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = XAICofounderAnalyzer(total_cofounders=11)

    def test_empty_analyzer(self):
        """Test analyzer with no records"""
        self.assertEqual(self.analyzer.count_departed(), 0)
        self.assertEqual(self.analyzer.count_active(), 0)
        self.assertEqual(self.analyzer.get_unaccounted_cofounders(), 11)

    def test_add_valid_record(self):
        """Test adding a valid record"""
        record = CofounderRecord(
            name="Test Founder",
            departure_date="2025-01-01T00:00:00",
            status=CofounderStatus.DEPARTED,
            source="TechCrunch",
            confidence=0.95,
            verified=True
        )
        self.analyzer.add_record(record)
        self.assertEqual(len(self.analyzer.records), 1)

    def test_add_invalid_record_type(self):
        """Test adding invalid record type"""
        with self.assertRaises(TypeError):
            self.analyzer.add_record({"name": "Invalid"})

    def test_add_record_empty_name(self):
        """Test adding record with empty name"""
        record = CofounderRecord(
            name="",
            departure_date=None,
            status=CofounderStatus.ACTIVE,
            source="Test",
            confidence=0.5,
            verified=False
        )
        with self.assertRaises(ValueError):
            self.analyzer.add_record(record)

    def test_add_record_invalid_confidence(self):
        """Test adding record with invalid confidence"""
        record = CofounderRecord(
            name="Founder",
            departure_date=None,
            status=CofounderStatus.ACTIVE,
            source="Test",
            confidence=1.5,
            verified=False
        )
        with self.assertRaises(ValueError):
            self.analyzer.add_record(record)

    def test_confidence_boundary_zero(self):
        """Test confidence value of 0"""
        record = CofounderRecord(
            name="Founder",
            departure_date=None,
            status=CofounderStatus.UNCERTAIN,
            source="Test",
            confidence=0.0,
            verified=False
        )
        self.analyzer.add_record(record)
        self.assertEqual(len(self.analyzer.records), 1)

    def test_confidence_boundary_one(self):
        """Test confidence value of 1.0"""
        record = CofounderRecord(
            name="Founder",
            departure_date=None,
            status=CofounderStatus.ACTIVE,
            source="Test",
            confidence=1.0,
            verified=True
        )
        self.analyzer.add_record(record)
        self.assertEqual(len(self.analyzer.records), 1)

    def test_validate_valid_departure_date(self):
        """Test validating a valid departure date"""
        past_date = (datetime.now() - timedelta(days=30)).isoformat()
        self.assertTrue(self.analyzer.validate_departure_date(past_date))

    def test_validate_future_departure_date(self):
        """Test validating a future departure date"""
        future_date = (datetime.now() + timedelta(days=30)).isoformat()
        self.assertFalse(self.analyzer.validate_departure_date(future_date))

    def test_validate_invalid_date_format(self):
        """Test validating invalid date format"""
        self.assertFalse(self.analyzer.validate_departure_date("not-a-date"))

    def test_validate_none_departure_date(self):
        """Test validating None departure date"""
        self.assertTrue(self.analyzer.validate_departure_date(None))

    def test_count_by_status(self):
        """Test counting records by status"""
        self.analyzer.add_record(CofounderRecord(
            name="Founder1", departure_date="2025-01-01T00:00:00",
            status=CofounderStatus.DEPARTED, source="Source1", confidence=0.9, verified=True
        ))
        self.analyzer.add_record(CofounderRecord(
            name="Founder2", departure_date=None,
            status=CofounderStatus.ACTIVE, source="Source2", confidence=0.8, verified=True
        ))
        self.analyzer.add_record(CofounderRecord(
            name="Founder3", departure_date=None,
            status=CofounderStatus.REPORTED_LEAVING, source="Source3", confidence=0.7, verified=False
        ))

        self.assertEqual(self.analyzer.count_departed(), 1)
        self.assertEqual(self.analyzer.count_active(), 1)
        self.assertEqual(self.analyzer.count_reported_leaving(), 1)
        self.assertEqual(self.analyzer.count_uncertain(), 0)

    def test_find_records_by_status(self):
        """Test finding records by status"""
        self.analyzer.add_record(CofounderRecord(
            name="Founder1", departure_date="2025-01-01T00:00:00",
            status=CofounderStatus.DEPARTED, source="Source1", confidence=0.9, verified=True
        ))
        self.analyzer.add_record(CofounderRecord(
            name="Founder2", departure_date="2025-02-01T00:00:00",
            status=CofounderStatus.DEPARTED, source="Source2", confidence=0.85, verified=True
        ))

        departed = self.analyzer.find_records_by_status(CofounderStatus.DEPARTED)
        self.assertEqual(len(departed), 2)

    def test_find_records_by_source(self):
        """Test finding records by source"""
        self.analyzer.add_record(CofounderRecord(
            name="Founder1", departure_date=None,
            status=CofounderStatus.ACTIVE, source="TechCrunch", confidence=0.9, verified=True
        ))
        self.analyzer.add_record(CofounderRecord(
            name="Founder2", departure_date=None,
            status=CofounderStatus.ACTIVE, source="Bloomberg", confidence=0.85, verified=True
        ))
        self.analyzer.add_record(CofounderRecord(
            name="Founder3", departure_date=None,
            status=CofounderStatus.ACTIVE, source="TechCrunch", confidence=0.8, verified=False
        ))

        techcrunch_records = self.analyzer.find_records_by_source("TechCrunch")
        self.assertEqual(len(techcrunch_records), 2)

    def test_find_records_by_source_case_insensitive(self):
        """Test source search is case-insensitive"""
        self.analyzer.add_record(CofounderRecord(
            name="Founder1", departure_date=None,
            status=CofounderStatus.ACTIVE, source="TechCrunch", confidence=0.9, verified=True
        ))

        records = self.analyzer.find_records_by_source("techcrunch")
        self.assertEqual(len(records), 1)

    def test_verify_departure_story_all_but_two(self):
        """Test story verification with all but two departed"""
        for i in range(9):
            self.analyzer.add_record(CofounderRecord(
                name=f"Founder{i}", departure_date=f"2025-0{