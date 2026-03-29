#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build data ingestion pipeline
# Mission: Competitive Analysis Dashboard
# Agent:   @sue
# Date:    2026-03-29T13:23:02.532Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Build data ingestion pipeline
Mission: Competitive Analysis Dashboard
Agent: @sue
Date: 2024

Implements scrapers and API connectors for competitor data sources including
public APIs, web scraping, and data aggregation with caching and error handling.
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import csv
import io
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib


@dataclass
class CompetitorDataPoint:
    """Represents a single data point from a competitor source"""
    source: str
    competitor: str
    metric: str
    value: Any
    timestamp: str
    raw_url: str


@dataclass
class DataSource:
    """Configuration for a data source"""
    name: str
    url: str
    data_type: str  # "json", "csv", "html"
    parser_type: str  # "api", "csv", "scrape"
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, str]] = None


class DataCache:
    """SQLite-based cache for ingested data"""
    
    def __init__(self, cache_path: str = "competitor_cache.db"):
        self.cache_path = cache_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the cache database"""
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cached_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    competitor TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    raw_url TEXT NOT NULL,
                    cached_at TEXT NOT NULL,
                    UNIQUE(source, competitor, metric, timestamp)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_source_timestamp 
                ON cached_data(source, timestamp)
            """)
            conn.commit()
    
    def store(self, data_point: CompetitorDataPoint):
        """Store a data point in the cache"""
        with sqlite3.connect(self.cache_path) as conn:
            try:
                conn.execute("""
                    INSERT INTO cached_data 
                    (source, competitor, metric, value, timestamp, raw_url, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data_point.source,
                    data_point.competitor,
                    data_point.metric,
                    json.dumps(data_point.value) if not isinstance(data_point.value, str) else data_point.value,
                    data_point.timestamp,
                    data_point.raw_url,
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
    
    def get_recent(self, source: str, hours: int = 24) -> List[CompetitorDataPoint]:
        """Retrieve recent cached data"""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        with sqlite3.connect(self.cache_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT source, competitor, metric, value, timestamp, raw_url
                FROM cached_data
                WHERE source = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (source, cutoff_time)).fetchall()
            
            data_points = []
            for row in rows:
                try:
                    value = json.loads(row['value'])
                except (json.JSONDecodeError, TypeError):
                    value = row['value']
                
                data_points.append(CompetitorDataPoint(
                    source=row['source'],
                    competitor=row['competitor'],
                    metric=row['metric'],
                    value=value,
                    timestamp=row['timestamp'],
                    raw_url=row['raw_url']
                ))
            return data_points
    
    def clear_old(self, days: int = 30):
        """Remove cached data older than specified days"""
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.cache_path) as conn:
            conn.execute(
                "DELETE FROM cached_data WHERE timestamp < ?",
                (cutoff_time,)
            )
            conn.commit()


class APIConnector:
    """Handles API-based data fetching"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def fetch_json(self, url: str, headers: Optional[Dict] = None, 
                   params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Fetch JSON data from API endpoint"""
        try:
            if params:
                url = url + "?" + urllib.parse.urlencode(params)
            
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        
        except urllib.error.URLError as e:
            print(f"URL Error fetching {url}: {e}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error from {url}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unexpected error fetching {url}: {e}", file=sys.stderr)
            return None
    
    def fetch_csv(self, url: str, headers: Optional[Dict] = None) -> Optional[List[Dict]]:
        """Fetch CSV data from URL"""
        try:
            req = urllib.request.Request(url)
            if headers:
                for key, value in headers.items():
                    req.add_header(key, value)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                content = response.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(content))
                return list(reader)
        
        except Exception as e:
            print(f"Error fetching CSV from {url}: {e}", file=sys.stderr)
            return None


class CompetitorScraper:
    """Web scraping functionality for competitor data"""
    
    @staticmethod
    def extract_json_from_html(html_content: str, script_id: Optional[str] = None) -> Optional[Dict]:
        """Extract JSON data embedded in HTML script tags"""
        try:
            if script_id:
                start = html_content.find(f'id="{script_id}"')
                if start == -1:
                    return None
                start = html_content.find('>', start)
                end = html_content.find('</script>', start)
                json_str = html_content[start+1:end].strip()
            else:
                start = html_content.find('<script type="application/json">')
                if start == -1:
                    return None
                start += len('<script type="application/json">')
                end = html_content.find('</script>', start)
                json_str = html_content[start:end].strip()
            
            return json.loads(json_str)
        except Exception as e:
            print(f"Error extracting JSON from HTML: {e}", file=sys.stderr)
            return None
    
    @staticmethod
    def extract_text_metrics(html_content: str, patterns: Dict[str, str]) -> Dict[str, Any]:
        """Extract metrics using simple pattern matching"""
        metrics = {}
        for metric_name, pattern in patterns.items():
            start = html_content.find(pattern)
            if start != -1:
                start += len(pattern)
                end = html_content.find('<', start)
                if end == -1:
                    end = len(html_content)
                value = html_content[start:end].strip()
                metrics[metric_name] = value
        return metrics


class DataIngestionPipeline:
    """Main pipeline for ingesting competitor data"""
    
    def __init__(self, cache_path: str = "competitor_cache.db", timeout: int = 10):
        self.cache = DataCache(cache_path)
        self.api_connector = APIConnector(timeout)
        self.scraper = CompetitorScraper()
        self.data_sources: List[DataSource] = []
        self.ingested_data: List[CompetitorDataPoint] = []
    
    def add_source(self, source: DataSource):
        """Register a data source"""
        self.data_sources.append(source)
    
    def ingest_from_source(self, source: DataSource, use_cache: bool = True) -> List[CompetitorDataPoint]:
        """Ingest data from a single source"""
        results = []
        
        if use_cache:
            cached = self.cache.get_recent(source.name, hours=1)
            if cached:
                results.extend(cached)
                return results
        
        if source.parser_type == "api":
            if source.data_type == "json":
                data = self.api_connector.fetch_json(
                    source.url,
                    headers=source.headers,
                    params=source.params
                )
                if data:
                    results.extend(self._parse_api_json(source, data))
        
        elif source.parser_type == "csv":
            data = self.api_connector.fetch_csv(source.url, headers=source.headers)
            if data:
                results.extend(self._parse_csv_data(source, data))
        
        elif source.parser_type == "scrape":
            try:
                req = urllib.request.Request(source.url)
                if source.headers:
                    for key, value in source.headers.items():
                        req.add_header(key, value)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    html_content = response.read().decode('utf-8')
                    results.extend(self._parse_html_content(source, html_content))
            except Exception as e:
                print(f"Error scraping {source.name}: {e}", file=sys.stderr)
        
        for data_point in results:
            self.cache.store(data_point)
        
        return results
    
    def _parse_api_json(self, source: DataSource, data: Dict[str, Any]) -> List[CompetitorDataPoint]:
        """Parse JSON API response"""
        results = []
        timestamp = datetime.utcnow().isoformat()
        
        if isinstance(data, dict):
            if "competitors" in data:
                competitors = data["competitors"]
                if isinstance(competitors, list):
                    for comp in competitors:
                        if isinstance(comp, dict):
                            competitor_name = comp.get("name", "unknown")
                            for key, value in comp.items():
                                if key != "name":
                                    results.append(CompetitorDataPoint(
                                        source=source.name,
                                        competitor=competitor_name,
                                        metric=key,
                                        value=value,
                                        timestamp=timestamp,
                                        raw_url=source.url
                                    ))
            else:
                for key, value in data.items():
                    results.append(CompetitorDataPoint(
                        source=source.name,
                        competitor="general",
                        metric=key,
                        value=value,
                        timestamp=timestamp,
                        raw_url=source.url
                    ))
        
        return results
    
    def _parse_csv_data(self, source: DataSource, data: List[Dict]) -> List[CompetitorDataPoint]:
        """Parse CSV data"""
        results = []
        timestamp = datetime.utcnow().isoformat()
        
        for row in data:
            competitor = row.get("competitor", row.get("name", "unknown"))
            for key, value in row.items():
                if key not in ["competitor", "name"]:
                    results.append(CompetitorDataPoint(
                        source=source.name,
                        competitor=competitor,
                        metric=key,
                        value=value,
                        timestamp=timestamp,
                        raw_url=source.url
                    ))
        
        return results
    
    def _parse_html_content(self, source: DataSource, html_content: str) -> List[CompetitorDataPoint]:
        """Parse HTML scraped content"""
        results = []
        timestamp = datetime.utcnow().isoformat()
        
        json_data = self.scraper.extract_json_from_html(html_content)
        if json_data:
            results.extend(self._parse_api_json(source, json_data))
        else:
            patterns = {
                "market_cap": "Market Cap:",
                "revenue": "Revenue:",
                "employees": "Employees:"
            }
            metrics = self.scraper.extract_text_metrics(html_content, patterns)
            for metric, value in metrics.items():
                results.append(CompetitorDataPoint(
                    source=source.name,
                    competitor="scraped",
                    metric=metric,
                    value=value,
                    timestamp=timestamp,
                    raw_url=source.url
                ))
        
        return results
    
    def ingest_all(self, use_cache: bool = True) -> Dict[str, List[CompetitorDataPoint]]:
        """Ingest data from all registered sources"""
        results = {}
        for source in self.data_sources:
            results[source.name] = self.ingest_from_source(source, use_cache)
        self.ingested_data = [dp for dps in results.values() for dp in dps]
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate summary of ingested data"""
        competitors = set()
        metrics = set()
        sources = set()
        
        for dp in self.ingested_data:
            competitors.add(dp.competitor)
            metrics.add(dp.metric)
            sources.add(dp.source)
        
        return {
            "total_data_points": len(self.ingested_data),
            "unique_competitors": len(competitors),
            "unique_metrics": len(metrics),
            "unique_sources": len(sources),
            "competitors": sorted(list(competitors)),
            "metrics": sorted(list(metrics)),
            "sources": sorted(list(sources)),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def export_json(self, output_path: str):
        """Export ingested data to JSON file"""
        data = [asdict(dp) for dp in self.ingested_data]
        with open(output_path, 'w') as f:
            json.dump({
                "metadata": self.get_summary(),
                "data": data
            }, f, indent=2)
    
    def export_csv(self, output_path: str):
        """Export ingested data to CSV file"""
        if not self.ingested_data:
            return
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = ['source', 'competitor', 'metric', 'value', 'timestamp', 'raw_url']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for dp in self.ingested_data:
                writer.writerow({
                    'source': dp.source,
                    'competitor': dp.competitor,
                    'metric': dp.metric,
                    'value': dp.value if isinstance(dp.value, str) else json.dumps(dp.value),