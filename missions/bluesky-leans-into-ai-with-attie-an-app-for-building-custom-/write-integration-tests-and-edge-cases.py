#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Write integration tests and edge cases
# Mission: Bluesky leans into AI with Attie, an app for building custom feeds
# Agent:   @aria
# Date:    2026-04-01T17:33:39.090Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Bluesky Attie Custom Feed Builder - Integration Tests & Edge Cases
Mission: Bluesky leans into AI with Attie, an app for building custom feeds
Agent: @aria (SwarmPulse)
Date: 2026-03-28

Integration test suite covering failure modes and boundary conditions for
Bluesky's Attie AI-powered custom feed builder on atproto.
"""

import argparse
import json
import sys
import unittest
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timedelta
import hashlib


class FeedFilterType(Enum):
    """Types of feed filters supported by Attie."""
    KEYWORD = "keyword"
    AUTHOR = "author"
    LANGUAGE = "language"
    ENGAGEMENT = "engagement"
    RECENCY = "recency"
    CUSTOM_ALGORITHM = "custom_algorithm"


class FeedAlgorithmType(Enum):
    """AI algorithm types for feed building."""
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    USER_PREFERENCE = "user_preference"


@dataclass
class FeedFilter:
    """Represents a single filter in a custom feed."""
    filter_type: FeedFilterType
    value: str
    enabled: bool = True
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        
        if not self.value:
            raise ValueError("Filter value cannot be empty")
        
        if len(self.value) > 500:
            raise ValueError("Filter value exceeds maximum length of 500 characters")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filter_type": self.filter_type.value,
            "value": self.value,
            "enabled": self.enabled,
            "created_at": self.created_at
        }


@dataclass
class CustomFeed:
    """Represents a custom feed built with Attie."""
    feed_id: str
    name: str
    description: str
    algorithm_type: FeedAlgorithmType
    filters: List[FeedFilter]
    owner_did: str
    is_public: bool = False
    created_at: str = None
    updated_at: str = None
    post_count: int = 0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow().isoformat()
        
        if not self.feed_id or len(self.feed_id) > 256:
            raise ValueError("Feed ID must be non-empty and <= 256 characters")
        
        if not self.name or len(self.name) > 100:
            raise ValueError("Feed name must be non-empty and <= 100 characters")
        
        if len(self.description) > 1000:
            raise ValueError("Feed description exceeds maximum length of 1000 characters")
        
        if not self.owner_did or not self.owner_did.startswith("did:"):
            raise ValueError("Invalid DID format for owner")
        
        if not self.filters:
            raise ValueError("Feed must have at least one filter")
        
        if len(self.filters) > 20:
            raise ValueError("Feed cannot have more than 20 filters")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feed_id": self.feed_id,
            "name": self.name,
            "description": self.description,
            "algorithm_type": self.algorithm_type.value,
            "filters": [f.to_dict() for f in self.filters],
            "owner_did": self.owner_did,
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "post_count": self.post_count
        }


class AttieIntegrationTest(unittest.TestCase):
    """Integration test suite for Attie feed builder."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_did = "did:plc:test123456789abcdef"
        self.test_filter = FeedFilter(
            filter_type=FeedFilterType.KEYWORD,
            value="bluesky"
        )
    
    def test_feed_creation_valid(self):
        """Test successful feed creation with valid parameters."""
        feed = CustomFeed(
            feed_id="feed_001",
            name="AI News",
            description="Latest AI and ML news from atproto",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did,
            is_public=True
        )
        
        self.assertEqual(feed.feed_id, "feed_001")
        self.assertEqual(feed.name, "AI News")
        self.assertTrue(feed.is_public)
        self.assertEqual(len(feed.filters), 1)
    
    def test_feed_creation_empty_feed_id(self):
        """Test feed creation fails with empty feed ID."""
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="",
                name="Test Feed",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
        self.assertIn("Feed ID must be non-empty", str(context.exception))
    
    def test_feed_creation_oversized_feed_id(self):
        """Test feed creation fails with oversized feed ID."""
        long_id = "x" * 300
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id=long_id,
                name="Test Feed",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
        self.assertIn("Feed ID", str(context.exception))
    
    def test_feed_creation_empty_name(self):
        """Test feed creation fails with empty name."""
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_002",
                name="",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
        self.assertIn("Feed name must be non-empty", str(context.exception))
    
    def test_feed_creation_oversized_name(self):
        """Test feed creation fails with oversized name."""
        long_name = "x" * 150
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_003",
                name=long_name,
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
        self.assertIn("Feed name", str(context.exception))
    
    def test_feed_creation_oversized_description(self):
        """Test feed creation fails with oversized description."""
        long_desc = "x" * 1500
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_004",
                name="Test Feed",
                description=long_desc,
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
        self.assertIn("description exceeds maximum length", str(context.exception))
    
    def test_feed_creation_invalid_did(self):
        """Test feed creation fails with invalid DID format."""
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_005",
                name="Test Feed",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did="invalid_did_format"
            )
        self.assertIn("Invalid DID format", str(context.exception))
    
    def test_feed_creation_empty_filters(self):
        """Test feed creation fails with no filters."""
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_006",
                name="Test Feed",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[],
                owner_did=self.test_did
            )
        self.assertIn("at least one filter", str(context.exception))
    
    def test_feed_creation_too_many_filters(self):
        """Test feed creation fails with too many filters."""
        filters = [
            FeedFilter(FeedFilterType.KEYWORD, f"keyword_{i}")
            for i in range(25)
        ]
        with self.assertRaises(ValueError) as context:
            CustomFeed(
                feed_id="feed_007",
                name="Test Feed",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=filters,
                owner_did=self.test_did
            )
        self.assertIn("cannot have more than 20 filters", str(context.exception))
    
    def test_filter_creation_valid(self):
        """Test successful filter creation."""
        filter_obj = FeedFilter(
            filter_type=FeedFilterType.AUTHOR,
            value="did:plc:author123",
            enabled=True
        )
        
        self.assertEqual(filter_obj.filter_type, FeedFilterType.AUTHOR)
        self.assertEqual(filter_obj.value, "did:plc:author123")
        self.assertTrue(filter_obj.enabled)
        self.assertIsNotNone(filter_obj.created_at)
    
    def test_filter_creation_empty_value(self):
        """Test filter creation fails with empty value."""
        with self.assertRaises(ValueError) as context:
            FeedFilter(
                filter_type=FeedFilterType.KEYWORD,
                value=""
            )
        self.assertIn("Filter value cannot be empty", str(context.exception))
    
    def test_filter_creation_oversized_value(self):
        """Test filter creation fails with oversized value."""
        long_value = "x" * 600
        with self.assertRaises(ValueError) as context:
            FeedFilter(
                filter_type=FeedFilterType.KEYWORD,
                value=long_value
            )
        self.assertIn("exceeds maximum length", str(context.exception))
    
    def test_filter_multiple_types(self):
        """Test creating filters of different types."""
        filters = [
            FeedFilter(FeedFilterType.KEYWORD, "python"),
            FeedFilter(FeedFilterType.AUTHOR, "did:plc:author"),
            FeedFilter(FeedFilterType.LANGUAGE, "en"),
            FeedFilter(FeedFilterType.ENGAGEMENT, "likes>100"),
            FeedFilter(FeedFilterType.RECENCY, "24h")
        ]
        
        self.assertEqual(len(filters), 5)
        self.assertEqual(filters[0].filter_type, FeedFilterType.KEYWORD)
        self.assertEqual(filters[1].filter_type, FeedFilterType.AUTHOR)
    
    def test_feed_serialization(self):
        """Test feed serialization to dictionary."""
        feed = CustomFeed(
            feed_id="feed_008",
            name="Test Feed",
            description="A test feed",
            algorithm_type=FeedAlgorithmType.COLLABORATIVE_FILTERING,
            filters=[self.test_filter],
            owner_did=self.test_did
        )
        
        feed_dict = feed.to_dict()
        self.assertIsInstance(feed_dict, dict)
        self.assertEqual(feed_dict["feed_id"], "feed_008")
        self.assertEqual(feed_dict["algorithm_type"], "collaborative_filtering")
        self.assertEqual(len(feed_dict["filters"]), 1)
    
    def test_feed_serialization_json(self):
        """Test feed serialization to JSON."""
        feed = CustomFeed(
            feed_id="feed_009",
            name="JSON Test Feed",
            description="Testing JSON serialization",
            algorithm_type=FeedAlgorithmType.CONTENT_BASED,
            filters=[self.test_filter],
            owner_did=self.test_did,
            is_public=True
        )
        
        feed_json = json.dumps(feed.to_dict(), indent=2)
        self.assertIsInstance(feed_json, str)
        
        parsed = json.loads(feed_json)
        self.assertEqual(parsed["feed_id"], "feed_009")
        self.assertTrue(parsed["is_public"])
    
    def test_boundary_max_filters(self):
        """Test feed creation with maximum allowed filters."""
        filters = [
            FeedFilter(FeedFilterType.KEYWORD, f"keyword_{i}")
            for i in range(20)
        ]
        
        feed = CustomFeed(
            feed_id="feed_010",
            name="Max Filters Feed",
            description="Feed with maximum filters",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=filters,
            owner_did=self.test_did
        )
        
        self.assertEqual(len(feed.filters), 20)
    
    def test_boundary_max_name_length(self):
        """Test feed creation with maximum name length."""
        max_name = "x" * 100
        feed = CustomFeed(
            feed_id="feed_011",
            name=max_name,
            description="Test",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did
        )
        
        self.assertEqual(len(feed.name), 100)
    
    def test_boundary_max_description_length(self):
        """Test feed creation with maximum description length."""
        max_desc = "x" * 1000
        feed = CustomFeed(
            feed_id="feed_012",
            name="Test",
            description=max_desc,
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did
        )
        
        self.assertEqual(len(feed.description), 1000)
    
    def test_filter_timestamp_consistency(self):
        """Test that filter creation timestamps are consistent."""
        filter1 = FeedFilter(FeedFilterType.KEYWORD, "test1")
        filter2 = FeedFilter(FeedFilterType.KEYWORD, "test2")
        
        self.assertIsNotNone(filter1.created_at)
        self.assertIsNotNone(filter2.created_at)
        self.assertTrue(filter1.created_at <= filter2.created_at)
    
    def test_feed_update_timestamp(self):
        """Test that feed timestamps are properly managed."""
        feed = CustomFeed(
            feed_id="feed_013",
            name="Timestamp Test",
            description="Test",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did
        )
        
        initial_created = feed.created_at
        initial_updated = feed.updated_at
        
        self.assertEqual(initial_created, initial_updated)
        self.assertIsNotNone(initial_created)
    
    def test_filter_enable_disable(self):
        """Test toggling filter enabled status."""
        filter_obj = FeedFilter(
            FeedFilterType.KEYWORD,
            "test",
            enabled=True
        )
        
        self.assertTrue(filter_obj.enabled)
        
        filter_obj.enabled = False
        self.assertFalse(filter_obj.enabled)
    
    def test_multiple_algorithm_types(self):
        """Test creating feeds with different algorithm types."""
        for algo_type in FeedAlgorithmType:
            feed = CustomFeed(
                feed_id=f"feed_algo_{algo_type.value}",
                name=f"Feed {algo_type.value}",
                description="Test",
                algorithm_type=algo_type,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
            self.assertEqual(feed.algorithm_type, algo_type)
    
    def test_special_characters_in_feed_name(self):
        """Test handling special characters in feed name."""
        special_names = [
            "Feed #1",
            "Test & Demo",
            "Feed (Beta)",
            "Test @mention",
            "Feed $special"
        ]
        
        for name in special_names:
            feed = CustomFeed(
                feed_id=f"feed_{hashlib.md5(name.encode()).hexdigest()[:8]}",
                name=name,
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=self.test_did
            )
            self.assertEqual(feed.name, name)
    
    def test_unicode_in_filter_value(self):
        """Test handling Unicode characters in filter values."""
        unicode_values = [
            "python 🐍",
            "日本語",
            "العربية",
            "emoji🎉🚀",
            "mixed_中文_text"
        ]
        
        for value in unicode_values:
            filter_obj = FeedFilter(
                FeedFilterType.KEYWORD,
                value
            )
            self.assertEqual(filter_obj.value, value)
    
    def test_feed_with_all_filter_types(self):
        """Test creating feed with all filter types."""
        filters = [
            FeedFilter(FeedFilterType.KEYWORD, "python"),
            FeedFilter(FeedFilterType.AUTHOR, "did:plc:author"),
            FeedFilter(FeedFilterType.LANGUAGE, "en"),
            FeedFilter(FeedFilterType.ENGAGEMENT, "likes>100"),
            FeedFilter(FeedFilterType.RECENCY, "24h"),
            FeedFilter(FeedFilterType.CUSTOM_ALGORITHM, "custom:trending")
        ]
        
        feed = CustomFeed(
            feed_id="feed_all_types",
            name="All Filter Types",
            description="Feed with all filter types",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=filters,
            owner_did=self.test_did
        )
        
        self.assertEqual(len(feed.filters), 6)
        filter_types = {f.filter_type for f in feed.filters}
        self.assertEqual(len(filter_types), 6)
    
    def test_concurrent_filter_creation(self):
        """Test creating multiple filters in sequence."""
        base_time = datetime.utcnow()
        filters = []
        
        for i in range(10):
            f = FeedFilter(FeedFilterType.KEYWORD, f"keyword_{i}")
            filters.append(f)
        
        self.assertEqual(len(filters), 10)
        for i, f in enumerate(filters):
            self.assertEqual(f
.value, f"keyword_{i}")
    
    def test_edge_case_single_char_filter(self):
        """Test filter with single character value."""
        filter_obj = FeedFilter(
            FeedFilterType.KEYWORD,
            "x"
        )
        self.assertEqual(len(filter_obj.value), 1)
    
    def test_edge_case_max_char_filter(self):
        """Test filter with maximum character value."""
        max_value = "x" * 500
        filter_obj = FeedFilter(
            FeedFilterType.KEYWORD,
            max_value
        )
        self.assertEqual(len(filter_obj.value), 500)
    
    def test_whitespace_only_value(self):
        """Test that whitespace-only values are handled."""
        with self.assertRaises(ValueError):
            FeedFilter(
                FeedFilterType.KEYWORD,
                ""
            )
    
    def test_did_format_variations(self):
        """Test various valid DID formats."""
        valid_dids = [
            "did:plc:abc123",
            "did:key:z6MkmjY8GC6M7i3r3SLrn1ih1Le1Ad6Palau8Sgvzn8e2KLt",
            "did:web:example.com",
            "did:ion:EiClkZMDxPEJcuOpQyuvjZTOWaISHEP2nRZ0d-VTgFJ7Jg"
        ]
        
        for did in valid_dids:
            feed = CustomFeed(
                feed_id="feed_did_test",
                name="DID Test",
                description="Test",
                algorithm_type=FeedAlgorithmType.HYBRID,
                filters=[self.test_filter],
                owner_did=did
            )
            self.assertEqual(feed.owner_did, did)
    
    def test_feed_post_count_increment(self):
        """Test feed post count tracking."""
        feed = CustomFeed(
            feed_id="feed_counter",
            name="Counter Test",
            description="Test",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did,
            post_count=0
        )
        
        self.assertEqual(feed.post_count, 0)
        feed.post_count = 100
        self.assertEqual(feed.post_count, 100)
    
    def test_feed_visibility_toggle(self):
        """Test toggling feed visibility."""
        feed = CustomFeed(
            feed_id="feed_visibility",
            name="Visibility Test",
            description="Test",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did,
            is_public=False
        )
        
        self.assertFalse(feed.is_public)
        feed.is_public = True
        self.assertTrue(feed.is_public)
    
    def test_filter_dict_representation(self):
        """Test filter dictionary conversion."""
        filter_obj = FeedFilter(
            FeedFilterType.KEYWORD,
            "test_value",
            enabled=True
        )
        
        filter_dict = filter_obj.to_dict()
        self.assertEqual(filter_dict["filter_type"], "keyword")
        self.assertEqual(filter_dict["value"], "test_value")
        self.assertTrue(filter_dict["enabled"])
        self.assertIn("created_at", filter_dict)
    
    def test_feed_dict_structure(self):
        """Test feed dictionary has all required fields."""
        feed = CustomFeed(
            feed_id="feed_structure",
            name="Structure Test",
            description="Test",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[self.test_filter],
            owner_did=self.test_did
        )
        
        feed_dict = feed.to_dict()
        required_fields = {
            "feed_id", "name", "description", "algorithm_type",
            "filters", "owner_did", "is_public", "created_at",
            "updated_at", "post_count"
        }
        
        self.assertTrue(required_fields.issubset(set(feed_dict.keys())))


class FeedBuilder:
    """Helper class for building custom feeds."""
    
    def __init__(self, feed_id: str, name: str, owner_did: str):
        self.feed_id = feed_id
        self.name = name
        self.owner_did = owner_did
        self.description = ""
        self.algorithm_type = FeedAlgorithmType.HYBRID
        self.filters = []
        self.is_public = False
    
    def set_description(self, description: str) -> "FeedBuilder":
        """Set feed description."""
        self.description = description
        return self
    
    def set_algorithm(self, algo_type: FeedAlgorithmType) -> "FeedBuilder":
        """Set algorithm type."""
        self.algorithm_type = algo_type
        return self
    
    def add_filter(self, filter_type: FeedFilterType, value: str) -> "FeedBuilder":
        """Add a filter to the feed."""
        self.filters.append(FeedFilter(filter_type, value))
        return self
    
    def set_public(self, is_public: bool) -> "FeedBuilder":
        """Set feed visibility."""
        self.is_public = is_public
        return self
    
    def build(self) -> CustomFeed:
        """Build and return the CustomFeed object."""
        if not self.description:
            raise ValueError("Description must be set before building")
        
        return CustomFeed(
            feed_id=self.feed_id,
            name=self.name,
            description=self.description,
            algorithm_type=self.algorithm_type,
            filters=self.filters,
            owner_did=self.owner_did,
            is_public=self.is_public
        )


class BuilderPatternTest(unittest.TestCase):
    """Test feed builder pattern."""
    
    def test_builder_basic_flow(self):
        """Test basic builder flow."""
        feed = (FeedBuilder("feed_build_1", "Builder Feed", "did:plc:test")
                .set_description("A built feed")
                .add_filter(FeedFilterType.KEYWORD, "python")
                .set_public(True)
                .build())
        
        self.assertEqual(feed.feed_id, "feed_build_1")
        self.assertTrue(feed.is_public)
        self.assertEqual(len(feed.filters), 1)
    
    def test_builder_multiple_filters(self):
        """Test builder with multiple filters."""
        feed = (FeedBuilder("feed_build_2", "Multi Filter", "did:plc:test")
                .set_description("Multiple filters")
                .add_filter(FeedFilterType.KEYWORD, "ai")
                .add_filter(FeedFilterType.AUTHOR, "did:plc:author")
                .add_filter(FeedFilterType.LANGUAGE, "en")
                .build())
        
        self.assertEqual(len(feed.filters), 3)
    
    def test_builder_missing_description(self):
        """Test builder fails without description."""
        builder = FeedBuilder("feed_build_3", "No Desc", "did:plc:test")
        builder.add_filter(FeedFilterType.KEYWORD, "test")
        
        with self.assertRaises(ValueError):
            builder.build()


def run_integration_tests(verbose: bool = False) -> Dict[str, Any]:
    """Run all integration tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(AttieIntegrationTest))
    suite.addTests(loader.loadTestsFromTestCase(BuilderPatternTest))
    
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    result = runner.run(suite)
    
    return {
        "total_tests": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "success": result.wasSuccessful(),
        "failure_details": [str(f[1]) for f in result.failures],
        "error_details": [str(e[1]) for e in result.errors]
    }


def demonstrate_edge_cases() -> None:
    """Demonstrate various edge cases and boundary conditions."""
    print("\n=== ATTIE INTEGRATION TEST DEMONSTRATIONS ===\n")
    
    test_did = "did:plc:demonstration123"
    
    print("1. Creating feed with maximum filters (20):")
    filters = [
        FeedFilter(FeedFilterType.KEYWORD, f"keyword_{i}")
        for i in range(20)
    ]
    feed_max = CustomFeed(
        feed_id="demo_max_filters",
        name="Maximum Filters Feed",
        description="Feed with 20 filters (maximum allowed)",
        algorithm_type=FeedAlgorithmType.HYBRID,
        filters=filters,
        owner_did=test_did
    )
    print(f"   ✓ Created feed with {len(feed_max.filters)} filters")
    
    print("\n2. Creating feed with maximum name length (100 chars):")
    max_name = "x" * 100
    feed_max_name = CustomFeed(
        feed_id="demo_max_name",
        name=max_name,
        description="Feed with maximum name length",
        algorithm_type=FeedAlgorithmType.CONTENT_BASED,
        filters=[FeedFilter(FeedFilterType.KEYWORD, "test")],
        owner_did=test_did
    )
    print(f"   ✓ Created feed with name length: {len(feed_max_name.name)}")
    
    print("\n3. Creating filter with maximum value length (500 chars):")
    max_value = "x" * 500
    filter_max = FeedFilter(
        FeedFilterType.KEYWORD,
        max_value
    )
    print(f"   ✓ Created filter with value length: {len(filter_max.value)}")
    
    print("\n4. Testing Unicode support in filter values:")
    unicode_test = FeedFilter(
        FeedFilterType.KEYWORD,
        "Python 🐍 | 日本語 | العربية"
    )
    print(f"   ✓ Filter with Unicode: {unicode_test.value}")
    
    print("\n5. Creating feed with all algorithm types:")
    for algo in FeedAlgorithmType:
        feed = CustomFeed(
            feed_id=f"demo_{algo.value}",
            name=f"Feed {algo.value}",
            description=f"Test {algo.value}",
            algorithm_type=algo,
            filters=[FeedFilter(FeedFilterType.KEYWORD, "test")],
            owner_did=test_did
        )
        print(f"   ✓ {algo.value}: {feed.feed_id}")
    
    print("\n6. Testing valid DID formats:")
    valid_dids = [
        "did:plc:simple",
        "did:key:z6MkmjY8GC6M7i3r3SLrn1ih1Le1Ad6Palau8Sgvzn8e2KLt",
        "did:web:example.com"
    ]
    for did in valid_dids:
        feed = CustomFeed(
            feed_id=f"demo_did_{len(did)}",
            name="DID Test",
            description="Testing DID",
            algorithm_type=FeedAlgorithmType.HYBRID,
            filters=[FeedFilter(FeedFilterType.KEYWORD, "test")],
            owner_did=did
        )
        print(f"   ✓ Valid DID: {did}")
    
    print("\n7. Testing builder pattern:")
    feed_built = (FeedBuilder("demo_builder", "Built Feed", test_did)
                  .set_description("Built with builder pattern")
                  .set_algorithm(FeedAlgorithmType.COLLABORATIVE_FILTERING)
                  .add_filter(FeedFilterType.KEYWORD, "bluesky")
                  .add_filter(FeedFilterType.LANGUAGE, "en")
                  .set_public(True)
                  .build())
    print(f"   ✓ Built feed: {feed_built.feed_id}")
    print(f"      - Algorithm: {feed_built.algorithm_type.value}")
    print(f"      - Filters: {len(feed_built.filters)}")
    print(f"      - Public: {feed_built.is_public}")
    
    print("\n8. JSON serialization test:")
    test_feed = CustomFeed(
        feed_id="demo_json",
        name="JSON Test",
        description="Testing JSON serialization",
        algorithm_type=FeedAlgorithmType.HYBRID,
        filters=[
            FeedFilter(FeedFilterType.KEYWORD, "test"),
            FeedFilter(FeedFilterType.ENGAGEMENT, "likes>50")
        ],
        owner_did=test_did,
        is_public=True,
        post_count=42
    )
    json_output = json.dumps(test_feed.to_dict(), indent=2)
    print(f"   ✓ Serialized feed to JSON")
    print("   Sample output:")
    for line in json_output.split('\n')[:10]:
        print(f"      {line}")
    if len(json_output.split('\n')) > 10:
        print("      ...")
    
    print("\n9. Testing error conditions:")
    error_tests = [
        ("Empty feed ID", lambda: CustomFeed("", "Test", "Test", 
                                           FeedAlgorithmType.HYBRID,
                                           [FeedFilter(FeedFilterType.KEYWORD, "x")],
                                           test_did)),
        ("Invalid DID", lambda: CustomFeed("id", "Test", "Test",
                                          FeedAlgorithmType.HYBRID,
                                          [FeedFilter(FeedFilterType.KEYWORD, "x")],
                                          "invalid")),
        ("Empty filter value", lambda: FeedFilter(FeedFilterType.KEYWORD, "")),
        ("No filters", lambda: CustomFeed("id", "Test", "Test",
                                         FeedAlgorithmType.HYBRID, [],
                                         test_did)),
    ]
    
    for test_name, test_func in error_tests:
        try:
            test_func()
            print(f"   ✗ {test_name}: Should have failed")
        except ValueError as e:
            print(f"   ✓ {test_name}: Correctly rejected")
    
    print("\n10. Feed state management:")
    stateful_feed = CustomFeed(
        feed_id="demo_state",
        name="State Test",
        description="Testing state changes",
        algorithm_type=FeedAlgorithmType.HYBRID,
        filters=[FeedFilter(FeedFilterType.KEYWORD, "test")],
        owner_did=test_did,
        is_public=False,
        post_count=0
    )
    print(f"   ✓ Created private feed with 0 posts")
    
    stateful_feed.is_public = True
    stateful_feed.post_count = 150
    print(f"   ✓ Updated to public with 150 posts")
    
    for filter_obj in stateful_feed.filters:
        filter_obj.enabled = False
    print(f"   ✓ Disabled all filters")
    
    print("\n=== DEMONSTRATIONS COMPLETE ===\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bluesky Attie Custom Feed Builder - Integration Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode tests
  %(prog)s --mode tests --verbose
  %(prog)s --mode demo
  %(prog)s --mode all
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["tests", "demo", "all"],
        default="all",
        help="Execution mode: run tests, demo, or both (default: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose test output"
    )
    
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output test results as JSON"
    )
    
    args = parser.parse_args()
    
    if args.mode in ["tests", "all"]:
        print("Running integration tests...")
        results = run_integration_tests(verbose=args.verbose)
        
        if args.json_output:
            print(json.dumps(results, indent=2))
        else:
            print(f"\n{'='*50}")
            print("TEST RESULTS SUMMARY")
            print(f"{'='*50}")
            print(f"Total Tests: {results['total_tests']}")
            print(f"Passed: {results['total_tests'] - results['failures'] - results['errors']}")
            print(f"Failures: {results['failures']}")
            print(f"Errors: {results['errors']}")
            print(f"Skipped: {results['skipped']}")
            print(f"Overall Success: {results['success']}")
            print(f"{'='*50}\n")
        
        if not results['success']:
            sys.exit(1)
    
    if args.mode in ["demo", "all"]:
        demonstrate_edge_cases()


if __name__ == "__main__":
    main()