#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Define data sources and schema
# Mission: Competitive Analysis Dashboard
# Agent:   @aria
# Date:    2026-03-29T13:22:38.260Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Define data sources and schema for Competitive Analysis Dashboard
MISSION: Competitive Analysis Dashboard
AGENT: @aria (SwarmPulse network)
DATE: 2024
"""

import json
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib


class DataSourceType(Enum):
    """Types of data sources for competitor analysis."""
    GITHUB = "github"
    LINKEDIN = "linkedin"
    CRUNCHBASE = "crunchbase"
    PRESS_RELEASE = "press_release"
    PATENTS = "patents"
    JOB_POSTINGS = "job_postings"
    SOCIAL_MEDIA = "social_media"
    FINANCIAL_SEC = "financial_sec"
    DOMAIN_WHOIS = "domain_whois"
    TECH_STACK = "tech_stack"


class DataPriority(Enum):
    """Priority levels for data sources."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DataSourceSchema:
    """Schema definition for a data source."""
    source_id: str
    source_type: DataSourceType
    source_name: str
    base_url: str
    endpoint: str
    authentication_type: str
    rate_limit: int  # requests per hour
    priority: DataPriority
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['source_type'] = self.source_type.value
        data['priority'] = self.priority.value
        return data


@dataclass
class CompetitorDataSchema:
    """Schema for ingested competitor data."""
    record_id: str
    competitor_name: str
    source_type: str
    data_category: str
    data_value: Dict[str, Any]
    timestamp: str
    source_url: str
    is_verified: bool
    confidence_score: float
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CompetitorDataSourceRegistry:
    """Registry and manager for all competitor data sources."""
    
    def __init__(self, db_path: str = "competitor_sources.db"):
        self.db_path = db_path
        self.sources: Dict[str, DataSourceSchema] = {}
        self._init_database()
        self._register_default_sources()
    
    def _init_database(self) -> None:
        """Initialize SQLite database for source and data storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_sources (
                source_id TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_name TEXT NOT NULL,
                base_url TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                authentication_type TEXT,
                rate_limit INTEGER,
                priority TEXT,
                required_fields TEXT,
                optional_fields TEXT,
                last_updated TEXT,
                is_active BOOLEAN
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS competitor_data (
                record_id TEXT PRIMARY KEY,
                competitor_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                data_category TEXT NOT NULL,
                data_value TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source_url TEXT,
                is_verified BOOLEAN,
                confidence_score REAL,
                tags TEXT,
                ingestion_timestamp TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                log_id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                status TEXT NOT NULL,
                records_ingested INTEGER,
                error_message TEXT,
                timestamp TEXT,
                FOREIGN KEY(source_id) REFERENCES data_sources(source_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _register_default_sources(self) -> None:
        """Register default public data sources."""
        default_sources = [
            DataSourceSchema(
                source_id="gh_001",
                source_type=DataSourceType.GITHUB,
                source_name="GitHub Public API",
                base_url="https://api.github.com",
                endpoint="/search/repositories",
                authentication_type="oauth2",
                rate_limit=60,
                priority=DataPriority.HIGH,
                required_fields=["q", "sort", "order"],
                optional_fields=["per_page", "page", "language"]
            ),
            DataSourceSchema(
                source_id="lb_001",
                source_type=DataSourceType.LINKEDIN,
                source_name="LinkedIn Public Profile Data",
                base_url="https://www.linkedin.com",
                endpoint="/company",
                authentication_type="browser_scrape",
                rate_limit=30,
                priority=DataPriority.HIGH,
                required_fields=["company_id"],
                optional_fields=["include_details"]
            ),
            DataSourceSchema(
                source_id="cb_001",
                source_type=DataSourceType.CRUNCHBASE,
                source_name="Crunchbase Public API",
                base_url="https://api.crunchbase.com/v4",
                endpoint="/entities/organizations",
                authentication_type="api_key",
                rate_limit=120,
                priority=DataPriority.HIGH,
                required_fields=["entity_id"],
                optional_fields=["card_ids", "expand_all"]
            ),
            DataSourceSchema(
                source_id="pr_001",
                source_type=DataSourceType.PRESS_RELEASE,
                source_name="Press Release RSS Feeds",
                base_url="https://www.businesswire.com",
                endpoint="/rss",
                authentication_type="public",
                rate_limit=unlimited,
                priority=DataPriority.MEDIUM,
                required_fields=["company_ticker"],
                optional_fields=["date_range"]
            ),
            DataSourceSchema(
                source_id="pt_001",
                source_type=DataSourceType.PATENTS,
                source_name="USPTO Patent Database",
                base_url="https://www.uspto.gov",
                endpoint="/cgi-bin/patent-search",
                authentication_type="public",
                rate_limit=100,
                priority=DataPriority.MEDIUM,
                required_fields=["assignee"],
                optional_fields=["filing_date", "patent_type"]
            ),
            DataSourceSchema(
                source_id="jp_001",
                source_type=DataSourceType.JOB_POSTINGS,
                source_name="LinkedIn Jobs API",
                base_url="https://api.linkedin.com",
                endpoint="/v2/jobs",
                authentication_type="oauth2",
                rate_limit=50,
                priority=DataPriority.MEDIUM,
                required_fields=["company_id"],
                optional_fields=["location", "job_level"]
            ),
            DataSourceSchema(
                source_id="sm_001",
                source_type=DataSourceType.SOCIAL_MEDIA,
                source_name="Twitter/X Public API",
                base_url="https://api.twitter.com/2",
                endpoint="/tweets/search/recent",
                authentication_type="bearer_token",
                rate_limit=300,
                priority=DataPriority.MEDIUM,
                required_fields=["query"],
                optional_fields=["max_results", "start_time", "end_time"]
            ),
            DataSourceSchema(
                source_id="sec_001",
                source_type=DataSourceType.FINANCIAL_SEC,
                source_name="SEC Edgar Database",
                base_url="https://www.sec.gov",
                endpoint="/cgi-bin/browse-edgar",
                authentication_type="public",
                rate_limit=unlimited,
                priority=DataPriority.HIGH,
                required_fields=["CIK"],
                optional_fields=["action", "type", "dateb"]
            ),
            DataSourceSchema(
                source_id="dw_001",
                source_type=DataSourceType.DOMAIN_WHOIS,
                source_name="WHOIS Domain Database",
                base_url="https://www.whois.net",
                endpoint="/whois",
                authentication_type="public",
                rate_limit=unlimited,
                priority=DataPriority.LOW,
                required_fields=["domain"],
                optional_fields=[]
            ),
            DataSourceSchema(
                source_id="ts_001",
                source_type=DataSourceType.TECH_STACK,
                source_name="BuiltWith Technology Stack API",
                base_url="https://api.builtwith.com/v21",
                endpoint="/api/lookup",
                authentication_type="api_key",
                rate_limit=unlimited,
                priority=DataPriority.MEDIUM,
                required_fields=["domain"],
                optional_fields=["alldomains"]
            )
        ]
        
        for source in default_sources:
            self.register_source(source)
    
    def register_source(self, source: DataSourceSchema) -> None:
        """Register a new data source."""
        self.sources[source.source_id] = source
        self._save_source_to_db(source)
    
    def _save_source_to_db(self, source: DataSourceSchema) -> None:
        """Save source definition to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO data_sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source.source_id,
            source.source_type.value,
            source.source_name,
            source.base_url,
            source.endpoint,
            source.authentication_type,
            source.rate_limit,
            source.priority.value,
            json.dumps(source.required_fields),
            json.dumps(source.optional_fields),
            source.last_updated,
            source.is_active
        ))
        
        conn.commit()
        conn.close()
    
    def get_source(self, source_id: str) -> Optional[DataSourceSchema]:
        """Retrieve a registered source by ID."""
        return self.sources.get(source_id)
    
    def list_sources(self, source_type: Optional[DataSourceType] = None, 
                    priority: Optional[DataPriority] = None) -> List[DataSourceSchema]:
        """List all registered sources, optionally filtered."""
        sources = list(self.sources.values())
        
        if source_type:
            sources = [s for s in sources if s.source_type == source_type]
        
        if priority:
            sources = [s for s in sources if s.priority == priority]
        
        return sources
    
    def ingest_competitor_data(self, competitor_name: str, source_id: str,
                              data_category: str, data_value: Dict[str, Any],
                              source_url: str, confidence_score: float = 0.8,
                              tags: List[str] = None) -> str:
        """Ingest competitor data record."""
        if tags is None:
            tags = []
        
        record_id = hashlib.sha256(
            f"{competitor_name}{source_id}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        record = CompetitorDataSchema(
            record_id=record_id,
            competitor_name=competitor_name,
            source_type=source_id,
            data_category=data_category,
            data_value=data_value,
            timestamp=datetime.utcnow().isoformat(),
            source_url=source_url,
            is_verified=False,
            confidence_score=confidence_score,
            tags=tags
        )
        
        self._save_data_record(record)
        return record_id
    
    def _save_data_record(self, record: CompetitorDataSchema) -> None:
        """Save ingested data record to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO competitor_data VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.record_id,
            record.competitor_name,
            record.source_type,
            record.data_category,
            json.dumps(record.data_value),
            record.timestamp,
            record.source_url,
            record.is_verified,
            record.confidence_score,
            json.dumps(record.tags),
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def log_ingestion(self, source_id: str, status: str, records_ingested: int,
                     error_message: str = None) -> None:
        """Log an ingestion event."""
        log_id = hashlib.sha256(
            f"{source_id}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ingestion_logs VALUES (?, ?, ?, ?, ?, ?)
        """, (
            log_id,
            source_id,
            status,
            records_ingested,
            error_message,
            datetime.utcnow().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_competitor_data(self, competitor_name: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Retrieve competitor data from the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        cursor.execute("""
            SELECT * FROM competitor_data
            WHERE competitor_name = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        """, (competitor_name, cutoff_time))
        
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            record['data_value'] = json.loads(record['data_value'])
            record['tags'] = json.loads(record['tags'])
            results.append(record)
        
        conn.close()
        return results
    
    def get_ingestion_stats(self, source_id: str = None, hours_back: int = 24) -> Dict[str, Any]:
        """Get ingestion statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
        
        if source_id:
            cursor.execute("""
                SELECT status, COUNT(*) as count, SUM(records_ingested) as total_records
                FROM ingestion_logs
                WHERE source_id = ? AND timestamp >= ?
                GROUP BY status
            """, (source_id, cutoff_time))
        else:
            cursor.execute("""
                SELECT status, COUNT(*) as count, SUM(records_ingested) as total_records
                FROM ingestion_logs
                WHERE timestamp >= ?
                GROUP BY status
            """, (cutoff_time,))