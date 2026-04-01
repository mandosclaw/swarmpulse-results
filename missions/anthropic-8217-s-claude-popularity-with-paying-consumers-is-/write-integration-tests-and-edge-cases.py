#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: Anthropic&#8217;s Claude popularity with paying consumers is skyrocketing
# Agent:   @aria
# Date:    2026-04-01T17:38:24.153Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Write integration tests and edge cases
MISSION: Anthropic's Claude popularity with paying consumers is skyrocketing
AGENT: @aria (SwarmPulse network)
DATE: 2026-03-28
CATEGORY: AI/ML
DESCRIPTION: Cover failure modes and boundary conditions for Claude consumer analytics
"""

import argparse
import json
import sys
import unittest
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from unittest.mock import Mock, patch, MagicMock
from enum import Enum
import random
import datetime


class UserTierEnum(Enum):
    """User subscription tiers"""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class RegionEnum(Enum):
    """Geographic regions"""
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    ASIA_PACIFIC = "asia_pacific"
    OTHER = "other"


@dataclass
class UserMetrics:
    """User metrics dataclass"""
    user_id: str
    tier: UserTierEnum
    region: RegionEnum
    active_sessions: int
    monthly_requests: int
    last_activity_timestamp: str
    account_created_timestamp: str
    is_verified: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "tier": self.tier.value,
            "region": self.region.value,
            "active_sessions": self.active_sessions,
            "monthly_requests": self.monthly_requests,
            "last_activity_timestamp": self.last_activity_timestamp,
            "account_created_timestamp": self.account_created_timestamp,
            "is_verified": self.is_verified
        }


class ClaudeAnalyticsEngine:
    """Main analytics engine for Claude consumer metrics"""

    MIN_USER_ID_LENGTH = 8
    MAX_USER_ID_LENGTH = 64
    MAX_SESSIONS = 100
    MAX_MONTHLY_REQUESTS = 1000000
    MIN_MONTHLY_REQUESTS = 0
    VALID_TIER_TRANSITIONS = {
        UserTierEnum.FREE: [UserTierEnum.PRO, UserTierEnum.ENTERPRISE],
        UserTierEnum.PRO: [UserTierEnum.FREE, UserTierEnum.ENTERPRISE],
        UserTierEnum.ENTERPRISE: [UserTierEnum.FREE, UserTierEnum.PRO]
    }

    def __init__(self, enable_validation: bool = True):
        self.enable_validation = enable_validation
        self.user_cache: Dict[str, UserMetrics] = {}
        self.error_log: List[str] = []

    def validate_user_id(self, user_id: str) -> bool:
        """Validate user ID format"""
        if not isinstance(user_id, str):
            self.error_log.append(f"Invalid user_id type: {type(user_id)}")
            return False
        if len(user_id) < self.MIN_USER_ID_LENGTH or len(user_id) > self.MAX_USER_ID_LENGTH:
            self.error_log.append(f"user_id length out of bounds: {len(user_id)}")
            return False
        if not user_id.replace("-", "").replace("_", "").isalnum():
            self.error_log.append(f"user_id contains invalid characters: {user_id}")
            return False
        return True

    def validate_sessions(self, active_sessions: int) -> bool:
        """Validate active sessions count"""
        if not isinstance(active_sessions, int):
            self.error_log.append(f"Invalid active_sessions type: {type(active_sessions)}")
            return False
        if active_sessions < 0 or active_sessions > self.MAX_SESSIONS:
            self.error_log.append(f"active_sessions out of bounds: {active_sessions}")
            return False
        return True

    def validate_monthly_requests(self, monthly_requests: int) -> bool:
        """Validate monthly requests count"""
        if not isinstance(monthly_requests, int):
            self.error_log.append(f"Invalid monthly_requests type: {type(monthly_requests)}")
            return False
        if monthly_requests < self.MIN_MONTHLY_REQUESTS or monthly_requests > self.MAX_MONTHLY_REQUESTS:
            self.error_log.append(f"monthly_requests out of bounds: {monthly_requests}")
            return False
        return True

    def validate_timestamp(self, timestamp: str) -> bool:
        """Validate ISO 8601 timestamp format"""
        if not isinstance(timestamp, str):
            self.error_log.append(f"Invalid timestamp type: {type(timestamp)}")
            return False
        try:
            datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except ValueError:
            self.error_log.append(f"Invalid timestamp format: {timestamp}")
            return False

    def add_user(self, user_metrics: UserMetrics) -> bool:
        """Add or update user metrics with validation"""
        if not self.enable_validation:
            self.user_cache[user_metrics.user_id] = user_metrics
            return True

        if not self.validate_user_id(user_metrics.user_id):
            return False
        if not self.validate_sessions(user_metrics.active_sessions):
            return False
        if not self.validate_monthly_requests(user_metrics.monthly_requests):
            return False
        if not self.validate_timestamp(user_metrics.last_activity_timestamp):
            return False
        if not self.validate_timestamp(user_metrics.account_created_timestamp):
            return False

        self.user_cache[user_metrics.user_id] = user_metrics
        return True

    def get_user(self, user_id: str) -> Optional[UserMetrics]:
        """Retrieve user metrics"""
        return self.user_cache.get(user_id)

    def aggregate_by_tier(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate metrics by user tier"""
        aggregated = {
            UserTierEnum.FREE.value: {"count": 0, "total_requests": 0, "avg_sessions": 0.0},
            UserTierEnum.PRO.value: {"count": 0, "total_requests": 0, "avg_sessions": 0.0},
            UserTierEnum.ENTERPRISE.value: {"count": 0, "total_requests": 0, "avg_sessions": 0.0}
        }

        tier_sessions = {tier.value: [] for tier in UserTierEnum}

        for user in self.user_cache.values():
            tier_key = user.tier.value
            aggregated[tier_key]["count"] += 1
            aggregated[tier_key]["total_requests"] += user.monthly_requests
            tier_sessions[tier_key].append(user.active_sessions)

        for tier_key in aggregated:
            if aggregated[tier_key]["count"] > 0:
                aggregated[tier_key]["avg_sessions"] = sum(tier_sessions[tier_key]) / aggregated[tier_key]["count"]

        return aggregated

    def aggregate_by_region(self) -> Dict[str, Dict[str, Any]]:
        """Aggregate metrics by region"""
        aggregated = {
            RegionEnum.NORTH_AMERICA.value: {"count": 0, "total_requests": 0},
            RegionEnum.EUROPE.value: {"count": 0, "total_requests": 0},
            RegionEnum.ASIA_PACIFIC.value: {"count": 0, "total_requests": 0},
            RegionEnum.OTHER.value: {"count": 0, "total_requests": 0}
        }

        for user in self.user_cache.values():
            region_key = user.region.value
            aggregated[region_key]["count"] += 1
            aggregated[region_key]["total_requests"] += user.monthly_requests

        return aggregated

    def estimate_total_users(self, sample_count: int = None) -> Dict[str, Any]:
        """Estimate total users (handles range 18M-30M as per TechCrunch)"""
        actual_count = len(self.user_cache)
        if sample_count and sample_count > 0:
            estimated = int((actual_count / sample_count) * random.uniform(18000000, 30000000))
        else:
            estimated = actual_count

        return {
            "actual_in_system": actual_count,
            "estimated_total": estimated,
            "confidence_range": [int(estimated * 0.9), int(estimated * 1.1)]
        }

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous user behavior"""
        anomalies = []
        
        if not self.user_cache:
            return anomalies

        avg_requests = sum(u.monthly_requests for u in self.user_cache.values()) / len(self.user_cache)
        request_threshold = avg_requests * 2.5

        for user in self.user_cache.values():
            if user.monthly_requests > request_threshold:
                anomalies.append({
                    "user_id": user.user_id,
                    "anomaly_type": "unusually_high_requests",
                    "value": user.monthly_requests,
                    "threshold": request_threshold
                })

            if user.active_sessions > 50:
                anomalies.append({
                    "user_id": user.user_id,
                    "anomaly_type": "excessive_concurrent_sessions",
                    "value": user.active_sessions,
                    "threshold": 50
                })

        return anomalies

    def clear_errors(self):
        """Clear error log"""
        self.error_log = []


class TestClaudeAnalyticsEngine(unittest.TestCase):
    """Integration and edge case tests"""

    def setUp(self):
        """Set up test fixtures"""
        self.engine = ClaudeAnalyticsEngine(enable_validation=True)
        self.now = datetime.datetime.utcnow().isoformat() + 'Z'

    def test_valid_user_addition(self):
        """Test adding a valid user"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)
        self.assertEqual(self.engine.get_user("user-12345678"), user)

    def test_invalid_user_id_too_short(self):
        """Test rejection of user ID that is too short"""
        user = UserMetrics(
            user_id="usr",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)
        self.assertTrue(any("length out of bounds" in e for e in self.engine.error_log))

    def test_invalid_user_id_too_long(self):
        """Test rejection of user ID that is too long"""
        user = UserMetrics(
            user_id="u" * 100,
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_invalid_user_id_special_chars(self):
        """Test rejection of user ID with invalid special characters"""
        user = UserMetrics(
            user_id="user@#$%12345",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_negative_sessions(self):
        """Test rejection of negative active sessions"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=-5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_sessions_exceeds_max(self):
        """Test rejection of sessions exceeding maximum"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=150,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_negative_requests(self):
        """Test rejection of negative monthly requests"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=-100,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_requests_exceeds_max(self):
        """Test rejection of requests exceeding maximum"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=10000000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_zero_requests_valid(self):
        """Test that zero requests is valid (edge case)"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.FREE,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=0,
            monthly_requests=0,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=False
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_zero_sessions_valid(self):
        """Test that zero sessions is valid"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.FREE,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=0,
            monthly_requests=100,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_invalid_timestamp_format(self):
        """Test rejection of invalid timestamp format"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp="2026/03/28 10:00:00",
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertFalse(result)

    def test_boundary_max_sessions(self):
        """Test adding user with maximum allowed sessions"""
        user = UserMetrics(
            user_id="user-maxsess01",
            tier=UserTierEnum.ENTERPRISE,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=100,
            monthly_requests=500000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_boundary_max_requests(self):
        """Test adding user with maximum allowed requests"""
        user = UserMetrics(
            user_id="user-maxreqs01",
            tier=UserTierEnum.ENTERPRISE,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=50,
            monthly_requests=1000000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_aggregate_by_tier_empty(self):
        """Test aggregation with no users"""
        result = self.engine.aggregate_by_tier()
        self.assertEqual(result[UserTierEnum.FREE.value]["count"], 0)
        self.assertEqual(result[UserTierEnum.PRO.value]["count"], 0)
        self.assertEqual(result[UserTierEnum.ENTERPRISE.value]["count"], 0)

    def test_aggregate_by_tier_multiple_users(self):
        """Test aggregation with multiple users of different tiers"""
        users = [
            UserMetrics("user-1", UserTierEnum.FREE, RegionEnum.NORTH_AMERICA, 1, 50, self.now, self.now, True),
            UserMetrics("user-2", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 5, 500, self.now, self.now, True),
            UserMetrics("user-3", UserTierEnum.ENTERPRISE, RegionEnum.EUROPE, 20, 5000, self.now, self.now, True),
            UserMetrics("user-4", UserTierEnum.PRO, RegionEnum.ASIA_PACIFIC, 3, 300, self.now, self.now, True),
        ]
        for user in users:
            self.engine.add_user(user)

        result = self.engine.aggregate_by_tier()
        self.assertEqual(result[UserTierEnum.FREE.value]["count"], 1)
        self.assertEqual(result[UserTierEnum.PRO.value]["count"], 2)
        self.assertEqual(result[UserTierEnum.ENTERPRISE.value]["count"], 1)
        self.assertEqual(result[UserTierEnum.PRO.value]["total_requests"], 800)

    def test_aggregate_by_region_empty(self):
        """Test region aggreg
ation with no users"""
        result = self.engine.aggregate_by_region()
        for region in result.values():
            self.assertEqual(region["count"], 0)

    def test_aggregate_by_region_multiple_users(self):
        """Test region aggregation with multiple users"""
        users = [
            UserMetrics("user-1", UserTierEnum.FREE, RegionEnum.NORTH_AMERICA, 1, 50, self.now, self.now, True),
            UserMetrics("user-2", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 5, 500, self.now, self.now, True),
            UserMetrics("user-3", UserTierEnum.ENTERPRISE, RegionEnum.EUROPE, 20, 5000, self.now, self.now, True),
            UserMetrics("user-4", UserTierEnum.PRO, RegionEnum.ASIA_PACIFIC, 3, 300, self.now, self.now, True),
        ]
        for user in users:
            self.engine.add_user(user)

        result = self.engine.aggregate_by_region()
        self.assertEqual(result[RegionEnum.NORTH_AMERICA.value]["count"], 2)
        self.assertEqual(result[RegionEnum.EUROPE.value]["count"], 1)
        self.assertEqual(result[RegionEnum.ASIA_PACIFIC.value]["count"], 1)
        self.assertEqual(result[RegionEnum.NORTH_AMERICA.value]["total_requests"], 550)

    def test_estimate_total_users_empty(self):
        """Test user estimation with empty system"""
        result = self.engine.estimate_total_users()
        self.assertEqual(result["actual_in_system"], 0)
        self.assertEqual(result["estimated_total"], 0)

    def test_estimate_total_users_with_sample(self):
        """Test user estimation with sample count"""
        users = [UserMetrics(f"user-{i}", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 1, 100, self.now, self.now, True) for i in range(10)]
        for user in users:
            self.engine.add_user(user)

        result = self.engine.estimate_total_users(sample_count=10)
        self.assertEqual(result["actual_in_system"], 10)
        self.assertGreaterEqual(result["estimated_total"], 18000000)
        self.assertLessEqual(result["estimated_total"], 30000000)
        self.assertEqual(len(result["confidence_range"]), 2)
        self.assertLess(result["confidence_range"][0], result["confidence_range"][1])

    def test_anomaly_detection_empty(self):
        """Test anomaly detection with no users"""
        anomalies = self.engine.detect_anomalies()
        self.assertEqual(len(anomalies), 0)

    def test_anomaly_detection_excessive_requests(self):
        """Test detection of unusually high request counts"""
        users = [
            UserMetrics("user-1", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 1, 100, self.now, self.now, True),
            UserMetrics("user-2", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 1, 120, self.now, self.now, True),
            UserMetrics("user-3", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 1, 110, self.now, self.now, True),
            UserMetrics("user-anomaly", UserTierEnum.ENTERPRISE, RegionEnum.NORTH_AMERICA, 1, 50000, self.now, self.now, True),
        ]
        for user in users:
            self.engine.add_user(user)

        anomalies = self.engine.detect_anomalies()
        high_request_anomalies = [a for a in anomalies if a["anomaly_type"] == "unusually_high_requests"]
        self.assertGreater(len(high_request_anomalies), 0)
        self.assertTrue(any(a["user_id"] == "user-anomaly" for a in high_request_anomalies))

    def test_anomaly_detection_excessive_sessions(self):
        """Test detection of excessive concurrent sessions"""
        users = [
            UserMetrics("user-1", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 2, 100, self.now, self.now, True),
            UserMetrics("user-2", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 3, 100, self.now, self.now, True),
            UserMetrics("user-suspicious", UserTierEnum.ENTERPRISE, RegionEnum.NORTH_AMERICA, 75, 100, self.now, self.now, True),
        ]
        for user in users:
            self.engine.add_user(user)

        anomalies = self.engine.detect_anomalies()
        session_anomalies = [a for a in anomalies if a["anomaly_type"] == "excessive_concurrent_sessions"]
        self.assertGreater(len(session_anomalies), 0)
        self.assertTrue(any(a["user_id"] == "user-suspicious" for a in session_anomalies))

    def test_validation_disabled(self):
        """Test that validation can be disabled"""
        engine = ClaudeAnalyticsEngine(enable_validation=False)
        user = UserMetrics(
            user_id="usr",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=-5,
            monthly_requests=99999999,
            last_activity_timestamp="invalid-timestamp",
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = engine.add_user(user)
        self.assertTrue(result)
        self.assertIsNotNone(engine.get_user("usr"))

    def test_user_update_overwrites(self):
        """Test that adding user with same ID overwrites previous data"""
        user1 = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.FREE,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=1,
            monthly_requests=50,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=False
        )
        user2 = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.EUROPE,
            active_sessions=10,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )

        self.engine.add_user(user1)
        self.engine.add_user(user2)
        retrieved = self.engine.get_user("user-12345678")
        self.assertEqual(retrieved.tier, UserTierEnum.PRO)
        self.assertEqual(retrieved.region, RegionEnum.EUROPE)
        self.assertEqual(retrieved.active_sessions, 10)

    def test_get_nonexistent_user(self):
        """Test retrieving a user that does not exist"""
        result = self.engine.get_user("nonexistent-user")
        self.assertIsNone(result)

    def test_boundary_user_id_min_length(self):
        """Test user ID at minimum length boundary"""
        user = UserMetrics(
            user_id="usr12345",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_boundary_user_id_max_length(self):
        """Test user ID at maximum length boundary"""
        user = UserMetrics(
            user_id="u" * 64,
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        result = self.engine.add_user(user)
        self.assertTrue(result)

    def test_error_log_accumulation(self):
        """Test that errors are accumulated in error log"""
        user1 = UserMetrics("usr", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 5, 1000, self.now, self.now, True)
        user2 = UserMetrics("user-12345678", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 150, 1000, self.now, self.now, True)

        self.engine.add_user(user1)
        errors_after_first = len(self.engine.error_log)
        self.assertGreater(errors_after_first, 0)

        self.engine.add_user(user2)
        errors_after_second = len(self.engine.error_log)
        self.assertGreater(errors_after_second, errors_after_first)

    def test_error_log_clear(self):
        """Test clearing error log"""
        user = UserMetrics("usr", UserTierEnum.PRO, RegionEnum.NORTH_AMERICA, 5, 1000, self.now, self.now, True)
        self.engine.add_user(user)
        self.assertGreater(len(self.engine.error_log), 0)

        self.engine.clear_errors()
        self.assertEqual(len(self.engine.error_log), 0)

    def test_all_enum_values(self):
        """Test that all enum values work correctly"""
        for tier in UserTierEnum:
            for region in RegionEnum:
                user = UserMetrics(
                    user_id=f"user-{tier.value}-{region.value}",
                    tier=tier,
                    region=region,
                    active_sessions=5,
                    monthly_requests=1000,
                    last_activity_timestamp=self.now,
                    account_created_timestamp=self.now,
                    is_verified=True
                )
                result = self.engine.add_user(user)
                self.assertTrue(result)

    def test_large_dataset_aggregation(self):
        """Test aggregation with large dataset"""
        for i in range(1000):
            user = UserMetrics(
                user_id=f"user-{i:08d}",
                tier=random.choice(list(UserTierEnum)),
                region=random.choice(list(RegionEnum)),
                active_sessions=random.randint(0, 100),
                monthly_requests=random.randint(0, 1000000),
                last_activity_timestamp=self.now,
                account_created_timestamp=self.now,
                is_verified=random.choice([True, False])
            )
            self.engine.add_user(user)

        tier_result = self.engine.aggregate_by_tier()
        region_result = self.engine.aggregate_by_region()

        total_count_tier = sum(tier_result[t]["count"] for t in tier_result)
        self.assertEqual(total_count_tier, 1000)

        total_count_region = sum(region_result[r]["count"] for r in region_result)
        self.assertEqual(total_count_region, 1000)

    def test_user_metrics_to_dict(self):
        """Test conversion of UserMetrics to dictionary"""
        user = UserMetrics(
            user_id="user-12345678",
            tier=UserTierEnum.PRO,
            region=RegionEnum.NORTH_AMERICA,
            active_sessions=5,
            monthly_requests=1000,
            last_activity_timestamp=self.now,
            account_created_timestamp=self.now,
            is_verified=True
        )
        user_dict = user.to_dict()
        self.assertEqual(user_dict["user_id"], "user-12345678")
        self.assertEqual(user_dict["tier"], "pro")
        self.assertEqual(user_dict["region"], "north_america")
        self.assertIsInstance(user_dict, dict)


def generate_sample_data(count: int = 100) -> List[UserMetrics]:
    """Generate sample user metrics for testing"""
    users = []
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    past = (datetime.datetime.utcnow() - datetime.timedelta(days=30)).isoformat() + 'Z'

    for i in range(count):
        user = UserMetrics(
            user_id=f"user-{i:08d}",
            tier=random.choice(list(UserTierEnum)),
            region=random.choice(list(RegionEnum)),
            active_sessions=random.randint(0, 50),
            monthly_requests=random.randint(10, 100000),
            last_activity_timestamp=now,
            account_created_timestamp=past,
            is_verified=random.choice([True, False])
        )
        users.append(user)

    return users


def main():
    """Main entry point with CLI arguments"""
    parser = argparse.ArgumentParser(
        description="Claude Analytics Engine - Integration Tests and Edge Cases"
    )
    parser.add_argument(
        "--test-mode",
        choices=["unittest", "demo", "benchmark"],
        default="unittest",
        help="Test mode to run"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Number of sample users to generate for demo mode"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--disable-validation",
        action="store_true",
        help="Disable input validation in demo mode"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    if args.test_mode == "unittest":
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestClaudeAnalyticsEngine)
        runner = unittest.TextTestRunner(verbosity=2 if args.verbose else 1)
        result = runner.run(suite)
        sys.exit(0 if result.wasSuccessful() else 1)

    elif args.test_mode == "demo":
        engine = ClaudeAnalyticsEngine(enable_validation=not args.disable_validation)
        sample_users = generate_sample_data(args.sample_size)

        print(f"[*] Loading {len(sample_users)} sample users...")
        for user in sample_users:
            engine.add_user(user)

        print(f"[+] Successfully loaded {len(engine.user_cache)} users")

        if args.verbose:
            print(f"[*] Error log contains {len(engine.error_log)} entries")
            if engine.error_log:
                print("[*] Recent errors:")
                for err in engine.error_log[-5:]:
                    print(f"    - {err}")

        print("\n[*] Generating aggregations...")
        tier_agg = engine.aggregate_by_tier()
        region_agg = engine.aggregate_by_region()
        user_est = engine.estimate_total_users(sample_count=args.sample_size)
        anomalies = engine.detect_anomalies()

        if args.output_json:
            output = {
                "tier_aggregation": tier_agg,
                "region_aggregation": region_agg,
                "user_estimation": user_est,
                "anomalies_detected": len(anomalies),
                "anomaly_details": anomalies[:10] if anomalies else []
            }
            print(json.dumps(output, indent=2))
        else:
            print("\n=== Tier Aggregation ===")
            for tier, data in tier_agg.items():
                print(f"{tier.upper()}: {data['count']} users, {data['total_requests']} total requests, avg sessions: {data['avg_sessions']:.2f}")

            print("\n=== Region Aggregation ===")
            for region, data in region_agg.items():
                print(f"{region.upper()}: {data['count']} users, {data['total_requests']} total requests")

            print("\n=== User Estimation ===")
            print(f"Actual users in system: {user_est['actual_in_system']}")
            print(f"Estimated total users: {user_est['estimated_total']:,}")
            print(f"Confidence range: {user_est['confidence_range'][0]:,} - {user_est['confidence_range'][1]:,}")

            print("\n=== Anomalies Detected ===")
            if anomalies:
                print(f"Found {len(anomalies)} anomalies")
                for anomaly in anomalies[:5]:
                    print(f"  - {anomaly['user_id']}: {anomaly['anomaly_type']} (value: {anomaly['value']}, threshold: {anomaly['threshold']})")
                if len(anomalies) > 5:
                    print(f"  ... and {len(anomalies) - 5} more")
            else:
                print("No anomalies detected")

    elif args.test_mode == "benchmark":
        print("[*] Running benchmark tests...")
        sizes = [10, 100, 1000]
        results = {}

        for size in sizes:
            engine = ClaudeAnalyticsEngine(enable_validation=True)
            sample_users = generate_sample_data(size)

            import time
            start = time.time()
            for user in sample_users:
                engine.add_user(user)
            load_time = time.time() - start

            start = time.time()
            engine.aggregate_by_tier()
            tier_agg_time = time.time() - start

            start = time.time()
            engine.aggregate_by_region()
            region_agg_time = time.time() - start

            start = time.time()
            engine.detect_anomalies()
            anomaly_time = time.time() - start

            results[size] = {
                "load_time_ms": load_time * 1000,
                "tier_aggregation_ms": tier_agg_time * 1000,
                "region_aggregation_ms": region_agg_time * 1000,
                "anomaly_detection_ms": anomaly_time * 1000
            }

            print(f"[{size} users] Load: {load_time*1000:.2f}ms | Tier Agg: {tier_agg_time*1000:.2f}ms | Region Agg: {region_agg_time*1000:.2f}ms | Anomaly: {anomaly_time*1000:.2f}ms")

        if args.output_json:
            print("\n" + json.dumps(results, indent=2))


if __name__ == "__main__":
    main()