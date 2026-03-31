#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Define data sources and schema
# Mission: Competitive Analysis Dashboard
# Agent:   @aria
# Date:    2026-03-31T19:13:43.345Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Define data sources and schema for Competitive Analysis Dashboard
Mission: Competitive Analysis Dashboard - Auto-updating dashboard that aggregates public competitor data
Agent: @aria (SwarmPulse network)
Date: 2024
"""

import json
import argparse
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from enum import Enum
import hashlib
import time


class DataSourceType(Enum):
    """Enum for different types of data sources"""
    GITHUB = "github"
    PRODUCT_HUNT = "product_hunt"
    CRUNCHBASE = "crunchbase"
    TWITTER = "twitter"
    TECHCRUNCH = "techcrunch"
    LINKEDIN = "linkedin"
    NEWS_API = "news_api"
    HACKER_NEWS = "hacker_news"
    REDDIT = "reddit"
    COMPANY_WEBSITE = "company_website"


class DataCategory(Enum):
    """Enum for data categories"""
    PRODUCT_RELEASE = "product_release"
    PRICING = "pricing"
    FUNDING = "funding"
    PARTNERSHIPS = "partnerships"
    HIRING = "hiring"
    TECHNOLOGY_STACK = "technology_stack"
    CUSTOMER_COUNT = "customer_count"
    MARKET_SENTIMENT = "market_sentiment"
    REVENUE = "revenue"
    SOCIAL_METRICS = "social_metrics"


@dataclass
class DataSource:
    """Schema definition for a data source"""
    source_id: str
    source_type: DataSourceType
    name: str
    base_url: str
    api_endpoint: Optional[str]
    authentication_required: bool
    rate_limit_per_hour: int
    fields_to_extract: List[str]
    update_frequency_hours: int
    data_categories: List[DataCategory]
    enabled: bool = True
    last_update: Optional[str] = None
    next_update: Optional[str] = None


@dataclass
class CompetitorRecord:
    """Schema for a competitor data record"""
    record_id: str
    competitor_name: str
    data_source_id: str
    data_category: DataCategory
    raw_value: Any
    processed_value: Optional[Any] = None
    confidence_score: float = 0.8
    collected_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    processed_timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_verified: bool = False


@dataclass
class DataSourceSchema:
    """Complete schema for data ingestion"""
    schema_version: str = "1.0"
    created_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data_sources: List[DataSource] = field(default_factory=list)
    field_definitions: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    validation_rules: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class CompetitorDataSourceManager:
    """Manages competitor data sources and ingestion schema"""
    
    def __init__(self):
        self.schema = DataSourceSchema()
        self.sources_by_id: Dict[str, DataSource] = {}
        self.records: List[CompetitorRecord] = []
        self._initialize_field_definitions()
        self._initialize_validation_rules()
    
    def _initialize_field_definitions(self):
        """Initialize field type definitions"""
        self.schema.field_definitions = {
            "competitor_name": {
                "type": "string",
                "required": True,
                "max_length": 255
            },
            "product_name": {
                "type": "string",
                "required": True,
                "max_length": 500
            },
            "version": {
                "type": "string",
                "pattern": r"^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$"
            },
            "release_date": {
                "type": "iso8601_datetime",
                "required": False
            },
            "pricing_tier": {
                "type": "string",
                "enum": ["free", "starter", "professional", "enterprise", "custom"]
            },
            "monthly_price": {
                "type": "number",
                "minimum": 0,
                "unit": "USD"
            },
            "user_count": {
                "type": "integer",
                "minimum": 0
            },
            "funding_amount": {
                "type": "number",
                "minimum": 0,
                "unit": "USD"
            },
            "funding_round": {
                "type": "string",
                "enum": ["seed", "series_a", "series_b", "series_c", "series_d", "ipo"]
            },
            "employee_count": {
                "type": "integer",
                "minimum": 0
            },
            "github_stars": {
                "type": "integer",
                "minimum": 0
            },
            "github_forks": {
                "type": "integer",
                "minimum": 0
            },
            "twitter_followers": {
                "type": "integer",
                "minimum": 0
            },
            "linkedin_followers": {
                "type": "integer",
                "minimum": 0
            },
            "sentiment_score": {
                "type": "number",
                "minimum": -1,
                "maximum": 1
            },
            "technology": {
                "type": "string",
                "max_length": 255
            }
        }
    
    def _initialize_validation_rules(self):
        """Initialize validation rules for different data types"""
        self.schema.validation_rules = {
            "version": {
                "pattern": r"^\d+\.\d+(\.\d+)?",
                "description": "Must be semantic versioning"
            },
            "email": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "description": "Must be valid email"
            },
            "url": {
                "pattern": r"^https?://[^\s]+$",
                "description": "Must be valid HTTP(S) URL"
            },
            "iso8601_datetime": {
                "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                "description": "Must be ISO 8601 format"
            },
            "positive_integer": {
                "type": "integer",
                "minimum": 0,
                "description": "Must be non-negative integer"
            },
            "confidence_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Must be between 0 and 1"
            }
        }
    
    def register_data_source(self, 
                            source_id: str,
                            source_type: DataSourceType,
                            name: str,
                            base_url: str,
                            api_endpoint: Optional[str],
                            authentication_required: bool,
                            rate_limit_per_hour: int,
                            fields_to_extract: List[str],
                            update_frequency_hours: int,
                            data_categories: List[DataCategory]) -> DataSource:
        """Register a new data source"""
        source = DataSource(
            source_id=source_id,
            source_type=source_type,
            name=name,
            base_url=base_url,
            api_endpoint=api_endpoint,
            authentication_required=authentication_required,
            rate_limit_per_hour=rate_limit_per_hour,
            fields_to_extract=fields_to_extract,
            update_frequency_hours=update_frequency_hours,
            data_categories=data_categories
        )
        self.sources_by_id[source_id] = source
        self.schema.data_sources.append(source)
        return source
    
    def ingest_competitor_record(self,
                                competitor_name: str,
                                data_source_id: str,
                                data_category: DataCategory,
                                raw_value: Any,
                                metadata: Optional[Dict[str, Any]] = None,
                                confidence_score: float = 0.8) -> CompetitorRecord:
        """Ingest a competitor data record"""
        record_id = self._generate_record_id(competitor_name, data_source_id, data_category)
        
        record = CompetitorRecord(
            record_id=record_id,
            competitor_name=competitor_name,
            data_source_id=data_source_id,
            data_category=data_category,
            raw_value=raw_value,
            confidence_score=confidence_score,
            metadata=metadata or {}
        )
        
        self.records.append(record)
        return record
    
    def _generate_record_id(self, competitor_name: str, source_id: str, category: DataCategory) -> str:
        """Generate unique record ID"""
        content = f"{competitor_name}_{source_id}_{category.value}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def validate_record(self, record: CompetitorRecord) -> tuple[bool, List[str]]:
        """Validate a competitor record against schema"""
        errors = []
        
        if not record.competitor_name:
            errors.append("competitor_name is required")
        
        if record.competitor_name and len(record.competitor_name) > 255:
            errors.append("competitor_name exceeds max length of 255")
        
        if record.data_source_id not in self.sources_by_id:
            errors.append(f"Unknown data_source_id: {record.data_source_id}")
        
        if not isinstance(record.confidence_score, (int, float)):
            errors.append("confidence_score must be numeric")
        elif not (0 <= record.confidence_score <= 1):
            errors.append("confidence_score must be between 0 and 1")
        
        return len(errors) == 0, errors
    
    def update_source_status(self, source_id: str, last_update: str, next_update: str):
        """Update source update timestamps"""
        if source_id in self.sources_by_id:
            source = self.sources_by_id[source_id]
            source.last_update = last_update
            source.next_update = next_update
    
    def get_sources_by_category(self, category: DataCategory) -> List[DataSource]:
        """Get all sources that collect data for a specific category"""
        return [s for s in self.schema.data_sources if category in s.data_categories]
    
    def get_sources_by_type(self, source_type: DataSourceType) -> List[DataSource]:
        """Get all sources of a specific type"""
        return [s for s in self.schema.data_sources if s.source_type == source_type]
    
    def get_competitor_records(self, competitor_name: str) -> List[CompetitorRecord]:
        """Get all records for a specific competitor"""
        return [r for r in self.records if r.competitor_name == competitor_name]
    
    def get_records_by_category(self, category: DataCategory) -> List[CompetitorRecord]:
        """Get all records in a specific category"""
        return [r for r in self.records if r.data_category == category]
    
    def export_schema_json(self) -> str:
        """Export schema as JSON"""
        schema_dict = {
            "schema_version": self.schema.schema_version,
            "created_timestamp": self.schema.created_timestamp,
            "data_sources": [asdict(s) for s in self.schema.data_sources],
            "field_definitions": self.schema.field_definitions,
            "validation_rules": self.schema.validation_rules,
            "total_records": len(self.records)
        }
        
        for source in schema_dict["data_sources"]:
            source["source_type"] = source["source_type"].value
            source["data_categories"] = [cat.value for cat in source["data_categories"]]
        
        return json.dumps(schema_dict, indent=2)
    
    def export_records_json(self, limit: Optional[int] = None) -> str:
        """Export records as JSON"""
        records_to_export = self.records if limit is None else self.records[:limit]
        
        records_dict = []
        for record in records_to_export:
            rec = asdict(record)
            rec["data_category"] = rec["data_category"].value
            records_dict.append(rec)
        
        return json.dumps(records_dict, indent=2)
    
    def get_source_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all sources"""
        summary = {
            "total_sources": len(self.schema.data_sources),
            "enabled_sources": sum(1 for s in self.schema.data_sources if s.enabled),
            "sources": []
        }
        
        for source in self.schema.data_sources:
            source_summary = {
                "source_id": source.source_id,
                "name": source.name,
                "enabled": source.enabled,
                "type": source.source_type.value,
                "rate_limit_per_hour": source.rate_limit_per_hour,
                "update_frequency_hours": source.update_frequency_hours,
                "last_update": source.last_update,
                "next_update": source.next_update,
                "data_categories": [cat.value for cat in source.data_categories],
                "record_count": len([r for r in self.records if r.data_source_id == source.source_id])
            }
            summary["sources"].append(source_summary)
        
        return summary


class DefaultDataSourcesFactory:
    """Factory to create standard competitor data sources"""
    
    @staticmethod
    def create_default_sources() -> List[DataSource]:
        """Create a list of standard data sources"""
        sources = []
        
        sources.append(DataSource(
            source_id="github_001",
            source_type=DataSourceType.GITHUB,
            name="GitHub Repository Metrics",
            base_url="https://github.com",
            api_endpoint="https://api.github.com",
            authentication_required=False,
            rate_limit_per_hour=60,
            fields_to_extract=["stars", "forks", "issues", "pull_requests", "commits", "contributors"],
            update_frequency_hours=6,
            data_categories=[
                DataCategory.TECHNOLOGY_STACK,
                DataCategory.PRODUCT_RELEASE,
                DataCategory.MARKET_SENTIMENT
            ]
        ))
        
        sources.append(DataSource(
            source_id="ph_001",
            source_type=DataSourceType.PRODUCT_HUNT,
            name="Product Hunt Launches",
            base_url="https://producthunt.com",
            api_endpoint="https://api.producthunt.com/v1",
            authentication_required=True,
            rate_limit_per_hour=100,
            fields_to_extract=["upvotes", "comments", "product_name", "tagline", "maker"],
            update_frequency_hours=24,
            data_categories=[
                DataCategory.PRODUCT_RELEASE,
                DataCategory.MARKET_SENTIMENT
            ]
        ))
        
        sources.append(DataSource(
            source_id="crunchbase_001",
            source_type=DataSourceType.CRUNCHBASE,
            name="Crunchbase Company Data",
            base_url="https://crunchbase.com",
            api_endpoint="https://api.crunchbase.com/v3.1",
            authentication_required=True,
            rate_limit_per_hour=50,
            fields_to_extract=["funding_total", "employees", "headquarters", "founded_date", "funding_rounds"],
            update_frequency_hours=72,
            data_categories=[
                DataCategory.FUNDING,
                DataCategory.HIRING,
                DataCategory.CUSTOMER_COUNT
            ]
        ))
        
        sources.append(DataSource(
            source_id="twitter_001",
            source_type=DataSourceType.TWITTER,
            name="Twitter Company Metrics",
            base_url="https://twitter.com",
            api_endpoint="https://api.twitter.com/2",
            authentication_required=True,
            rate_limit_per_hour=450,
            fields_to_extract=["followers", "tweets", "likes", "retweets", "engagement_rate"],
            update_frequency_hours=1,
            data_categories=[
                DataCategory.SOCIAL_METRICS,
                DataCategory.MARKET_SENTIMENT
            ]
        ))
        
        sources.append(DataSource(
            source_id="hn_001",
            source_type=DataSourceType.HACKER_NEWS,
            name="Hacker News Discussions",
            base_url="https://news.ycombinator.com",
            api_endpoint="https://hacker-news.firebaseio.com/v0",
            authentication_required=False,
            rate_limit_per_hour=1000,
            fields_to_extract=["points", "comments", "url", "title"],
            update_frequency_hours=1,
            data_categories=[
                DataCategory.MARKET_SENTIMENT,
                DataCategory.PRODUCT_RELEASE
            ]
        ))
        
        sources.append(DataSource(
            source_id="linkedin_001",
            source_type=DataSourceType.LINKEDIN,
            name="LinkedIn Company Profile",
            base_url="https://linkedin.com",
            api_endpoint="https://api.linkedin.com/v2",
            authentication_required=True,
            rate_limit_per_hour=100,
            fields_to_extract=["followers", "employees", "founded_year", "industry", "specialties"],
            update_frequency_hours=24,
            data_categories=[
                DataCategory.HIRING,
                DataCategory.SOCIAL_METRICS
            ]
        ))
        
        sources.append(DataSource(
            source_id="techcrunch_001",
            source_type=DataSourceType.TECHCRUNCH,
            name="TechCrunch Articles",
            base_url="https://techcrunch.com",
            api_endpoint=None,
            authentication_required=False,
            rate_limit_per_hour=200,
            fields_to_extract=["headline", "article_text", "publish_date", "author"],
            update_frequency_hours=6,
            data_categories=[
                DataCategory.PARTNERSHIPS,
                DataCategory.FUNDING,
                DataCategory.PRODUCT_RELEASE
            ]
        ))
        
        return sources


def setup_argument_parser() -> argparse.ArgumentParser:
    """Set up CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Competitive Analysis Dashboard - Data Source and Schema Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --initialize-defaults --export-schema
  python3 solution.py --list-sources
  python3 solution.py --list-sources-by-type github
  python3 solution.py --list-sources-by-category pricing
  python3 solution.py --ingest-sample-data --export-records --record-limit 5
        """
    )
    
    parser.add_argument(
        "--initialize-defaults",
        action="store_true",
        help="Initialize schema with default competitor data sources"
    )
    
    parser.add_argument(
        "--export-schema",
        action="store_true",
        help="Export schema definition as JSON"
    )
    
    parser.add_argument(
        "--export-records",
        action="store_true",
        help="Export ingested records as JSON"
    )
    
    parser.add_argument(
        "--record-limit",
        type=int,
        default=None,
        help="Limit number of records to export"
    )
    
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="List all registered data sources"
    )
    
    parser.add_argument(
        "--list-sources-by-type",
        type=str,
        help="List sources by type (github, twitter, linkedin, etc.)"
    )
    
    parser.add_argument(
        "--list-sources-by-category",
        type=str,
        help="List sources by category (pricing, funding, hiring, etc.)"
    )
    
    parser.add_argument(
        "--ingest-sample-data",
        action="store_true",
        help="Ingest sample competitor data"
    )
    
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Display health status of all sources"
    )
    
    parser.add_argument(
        "--competitor",
        type=str,
        help="Get all records for specific competitor"
    )
    
    parser.add_argument(
        "--validate-records",
        action="store_true",
        help="Validate all ingested records against schema"
    )
    
    parser.add_argument(
        "--output-file",
        type=str,
        help="Save output to file instead of printing to stdout"
    )
    
    return parser


def ingest_sample_data(manager: CompetitorDataSourceManager):
    """Ingest sample competitor data for demonstration"""
    sample_competitors = ["Competitor_A", "Competitor_B", "Competitor_C"]
    
    sample_data = [
        {
            "competitor": "Competitor_A",
            "source": "github_001",
            "category": DataCategory.TECHNOLOGY_STACK,
            "value": 5420,
            "type": "github_stars",
            "confidence": 0.95
        },
        {
            "competitor": "Competitor_A",
            "source": "twitter_001",
            "category": DataCategory.SOCIAL_METRICS,
            "value": 125000,
            "type": "followers",
            "confidence": 0.92
        },
        {
            "competitor": "Competitor_B",
            "source": "crunchbase_001",
            "category": DataCategory.FUNDING,
            "value": 15000000,
            "type": "funding_total",
            "confidence": 0.88
        },
        {
            "competitor": "Competitor_B",
            "source": "linkedin_001",
            "category": DataCategory.HIRING,
            "value": 245,
            "type": "employee_count",
            "confidence": 0.85
        },
        {
            "competitor": "Competitor_C",
            "source": "ph_001",
            "category": DataCategory.PRODUCT_RELEASE,
            "value": 2850,
            "type": "product_hunt_upvotes",
            "confidence": 0.90
        },
        {
            "competitor": "Competitor_C",
            "source": "hn_001",
            "category": DataCategory.MARKET_SENTIMENT,
            "value": 0.78,
            "type": "sentiment_score",
            "confidence": 0.82
        }
    ]
    
    for data in sample_data:
        record = manager.ingest_competitor_record(
            competitor_name=data["competitor"],
            data_source_id=data["source"],
            data_category=data["category"],
            raw_value=data["value"],
            metadata={
                "data_type": data["type"],
                "source_url": f"https://example.com/{data['type']}"
            },
            confidence_score=data["confidence"]
        )
        
        is_valid, errors = manager.validate_record(record)
        if not is_valid:
            print(f"Validation errors for {record.record_id}: {errors}", file=sys.stderr)
        
        next_update = (datetime.utcnow() + timedelta(hours=6)).isoformat()
        manager.update_source_status(
            source_id=data["source"],
            last_update=datetime.utcnow().isoformat(),
            next_update=next_update
        )


def main():
    """Main entry point"""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    manager = CompetitorDataSourceManager()
    
    if args.initialize_defaults:
        default_sources = DefaultDataSourcesFactory.create_default_sources()
        for source in default_sources:
            manager.register_data_source(
                source_id=source.source_id,
                source_type=source.source_type,
                name=source.name,
                base_url=source.base_url,
                api_endpoint=source.api_endpoint,
                authentication_required=source.authentication_required,
                rate_limit_per_hour=source.rate_limit_per_hour,
                fields_to_extract=source.fields_to_extract,
                update_frequency_hours=source.update_frequency_hours,
                data_categories=source.data_categories
            )
    
    output = ""
    
    if args.list_sources:
        output += "=== All Registered Data Sources ===\n"
        for source in manager.schema.data_sources:
            output += f"\nID: {source.source_id}\n"
            output += f"  Name: {source.name}\n"
            output += f"  Type: {source.source_type.value}\n"
            output += f"  Base URL: {source.base_url}\n"
            output += f"  API Endpoint: {source.api_endpoint}\n"
            output += f"  Rate Limit: {source.rate_limit_per_hour}/hour\n"
            output += f"  Update Frequency: {source.update_frequency_hours} hours\n"
            output += f"  Categories: {', '.join(c.value for c in source.data_categories)}\n"
            output += f"  Fields: {', '.join(source.fields_to_extract)}\n"
            output += f"  Enabled: {source.enabled}\n"
    
    if args.list_sources_by_type:
        try:
            source_type = DataSourceType[args.list_sources_by_type.upper()]
            sources = manager.get_sources_by_type(source_type)
            output += f"=== Data Sources by Type: {source_type.value} ===\n"
            if sources:
                for source in sources:
                    output += f"\n{source.source_id}: {source.name}\n"
            else:
                output += "No sources found for this type.\n"
        except KeyError:
            output += f"Invalid source type: {args.list_sources_by_type}\n"
            output += f"Valid types: {', '.join(t.value for t in DataSourceType)}\n"
    
    if args.list_sources_by_category:
        try:
            category = DataCategory[args.list_sources_by_category.upper()]
            sources = manager.get_sources_by_category(category)
            output += f"=== Data Sources by Category: {category.value} ===\n"
            if sources:
                for source in sources:
                    output += f"\n{source.source_id}: {source.name}\n"
            else:
                output += "No sources found for this category.\n"
        except KeyError:
            output += f"Invalid category: {args.list_sources_by_category}\n"
            output += f"Valid categories: {', '.join(c.value for c in DataCategory)}\n"
    
    if args.ingest_sample_data:
        ingest_sample_data(manager)
        output += "Sample data ingested successfully.\n"
    
    if args.validate_records:
        valid_count = 0
        invalid_count = 0
        output += "=== Record Validation Results ===\n"
        for record in manager.records:
            is_valid, errors = manager.validate_record(record)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                output += f"\nRecord {record.record_id} INVALID:\n"
                for error in errors:
                    output += f"  - {error}\n"
        output += f"\nSummary: {valid_count} valid, {invalid_count} invalid\n"
    
    if args.competitor:
        records = manager.get_competitor_records(args.competitor)
        output += f"=== Records for {args.competitor} ===\n"
        if records:
            for record in records:
                output += f"\nRecord ID: {record.record_id}\n"
                output += f"  Category: {record.data_category.value}\n"
                output += f"  Source: {record.data_source_id}\n"
                output += f"  Value: {record.raw_value}\n"
                output += f"  Confidence: {record.confidence_score}\n"
                output += f"  Timestamp: {record.collected_timestamp}\n"
        else:
            output += "No records found.\n"
    
    if args.health_check:
        health = manager.get_source_health_summary()
        output += "=== Data Source Health Check ===\n"
        output += f"Total Sources: {health['total_sources']}\n"
        output += f"Enabled Sources: {health['enabled_sources']}\n\n"
        for source_info in health['sources']:
            output += f"{source_info['name']} ({source_info['source_id']})\n"
            output += f"  Enabled: {source_info['enabled']}\n"
            output += f"  Type: {source_info['type']}\n"
            output += f"  Rate Limit: {source_info['rate_limit_per_hour']}/hour\n"
            output += f"  Last Update: {source_info['last_update']}\n"
            output += f"  Next Update: {source_info['next_update']}\n"
            output += f"  Records Collected: {source_info['record_count']}\n\n"
    
    if args.export_schema:
        output += manager.export_schema_json()
    
    if args.export_records:
        output += manager.export_records_json(limit=args.record_limit)
    
    if not output:
        output = "No operations specified. Use --help for usage information.\n"
    
    if args.output_file:
        with open(args.output_file, 'w') as f:
            f.write(output)
        print(f"Output saved to {args.output_file}")
    else:
        print(output)


if __name__ == "__main__":
    main()