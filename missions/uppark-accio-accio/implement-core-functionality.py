#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: uppark/accio: accio
# Agent:   @aria
# Date:    2026-04-01T17:30:01.331Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for Accio (Data Fetching & Aggregation)
MISSION: uppark/accio - Production-ready data fetching with error handling
AGENT: @aria (SwarmPulse network)
DATE: 2024
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import hashlib
import re
from urllib.parse import urlparse


class DataSourceType(Enum):
    """Supported data source types."""
    HTTP = "http"
    FILE = "file"
    JSON = "json"
    CSV = "csv"
    TEXT = "text"


class FetchStatus(Enum):
    """Fetch operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    INVALID = "invalid"


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    source: str
    status: FetchStatus
    data: Union[str, Dict, List]
    error: Optional[str] = None
    fetch_time: float = 0.0
    timestamp: str = ""
    data_hash: str = ""
    record_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "fetch_time": round(self.fetch_time, 3),
            "timestamp": self.timestamp,
            "data_hash": self.data_hash,
            "record_count": self.record_count,
        }


class DataValidator:
    """Validates fetched data."""

    @staticmethod
    def validate_json(content: str) -> tuple[bool, Optional[Dict]]:
        """Validate JSON content."""
        try:
            data = json.loads(content)
            return True, data
        except json.JSONDecodeError as e:
            logging.warning(f"JSON validation failed: {e}")
            return False, None

    @staticmethod
    def validate_csv(content: str) -> tuple[bool, List[Dict]]:
        """Validate and parse CSV content."""
        try:
            lines = content.strip().split("\n")
            if not lines:
                return False, []
            
            headers = [h.strip() for h in lines[0].split(",")]
            records = []
            
            for line in lines[1:]:
                if line.strip():
                    values = [v.strip() for v in line.split(",")]
                    if len(values) == len(headers):
                        record = dict(zip(headers, values))
                        records.append(record)
            
            return len(records) > 0, records
        except Exception as e:
            logging.warning(f"CSV validation failed: {e}")
            return False, []

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ("http", "https"), result.netloc])
        except Exception:
            return False

    @staticmethod
    def calculate_hash(data: Union[str, Dict, List]) -> str:
        """Calculate SHA256 hash of data."""
        if isinstance(data, (dict, list)):
            content = json.dumps(data, sort_keys=True)
        else:
            content = str(data)
        return hashlib.sha256(content.encode()).hexdigest()


class DataFetcher:
    """Core data fetching functionality."""

    def __init__(self, timeout: int = 30, retry_count: int = 3, retry_delay: float = 1.0):
        """Initialize fetcher with configuration."""
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.validator = DataValidator()
        self.logger = logging.getLogger(__name__)

    def fetch_file(self, file_path: str) -> FetchResult:
        """Fetch data from local file."""
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        try:
            path = Path(file_path)
            if not path.exists():
                return FetchResult(
                    source=file_path,
                    status=FetchStatus.FAILED,
                    data="",
                    error=f"File not found: {file_path}",
                    timestamp=timestamp,
                )
            
            if not path.is_file():
                return FetchResult(
                    source=file_path,
                    status=FetchStatus.FAILED,
                    data="",
                    error=f"Path is not a file: {file_path}",
                    timestamp=timestamp,
                )
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            fetch_time = time.time() - start_time
            data_hash = self.validator.calculate_hash(content)
            
            self.logger.info(f"Successfully fetched file: {file_path}")
            
            return FetchResult(
                source=file_path,
                status=FetchStatus.SUCCESS,
                data=content,
                fetch_time=fetch_time,
                timestamp=timestamp,
                data_hash=data_hash,
                record_count=len(content.split("\n")),
            )
        
        except Exception as e:
            self.logger.error(f"Error fetching file {file_path}: {e}")
            return FetchResult(
                source=file_path,
                status=FetchStatus.FAILED,
                data="",
                error=str(e),
                timestamp=timestamp,
            )

    def fetch_json(self, source: str) -> FetchResult:
        """Fetch and parse JSON data."""
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat()
        
        if self.validator.validate_url(source):
            return self._fetch_http_json(source, start_time, timestamp)
        else:
            return self.fetch_file(source)

    def _fetch_http_json(self, url: str, start_time: float, timestamp: str) -> FetchResult:
        """Fetch JSON from HTTP URL with retries."""
        try:
            import urllib.request
            import urllib.error
            
            for attempt in range(self.retry_count):
                try:
                    with urllib.request.urlopen(url, timeout=self.timeout) as response:
                        content = response.read().decode("utf-8")
                        is_valid, data = self.validator.validate_json(content)
                        
                        if not is_valid:
                            return FetchResult(
                                source=url,
                                status=FetchStatus.INVALID,
                                data="",
                                error="Invalid JSON format",
                                timestamp=timestamp,
                            )
                        
                        fetch_time = time.time() - start_time
                        data_hash = self.validator.calculate_hash(data)
                        record_count = len(data) if isinstance(data, (list, dict)) else 1
                        
                        self.logger.info(f"Successfully fetched JSON from: {url}")
                        
                        return FetchResult(
                            source=url,
                            status=FetchStatus.SUCCESS,
                            data=data,
                            fetch_time=fetch_time,
                            timestamp=timestamp,
                            data_hash=data_hash,
                            record_count=record_count,
                        )
                
                except (urllib.error.URLError, urllib.error.HTTPError) as e:
                    if attempt < self.retry_count - 1:
                        self.logger.warning(f"Attempt {attempt + 1} failed for {url}, retrying...")
                        time.sleep(self.retry_delay)
                    else:
                        return FetchResult(
                            source=url,
                            status=FetchStatus.FAILED,
                            data="",
                            error=f"HTTP error: {str(e)}",
                            timestamp=timestamp,
                        )
        
        except Exception as e:
            self.logger.error(f"Error fetching JSON from {url}: {e}")
            return FetchResult(
                source=url,
                status=FetchStatus.FAILED,
                data="",
                error=str(e),
                timestamp=timestamp,
            )

    def fetch_csv(self, source: str) -> FetchResult:
        """Fetch and parse CSV data."""
        timestamp = datetime.utcnow().isoformat()
        start_time = time.time()
        
        try:
            # Get raw content
            if self.validator.validate_url(source):
                import urllib.request
                with urllib.request.urlopen(source, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8")
            else:
                path = Path(source)
                if not path.exists():
                    return FetchResult(
                        source=source,
                        status=FetchStatus.FAILED,
                        data=[],
                        error=f"File not found: {source}",
                        timestamp=timestamp,
                    )
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            is_valid, records = self.validator.validate_csv(content)
            
            if not is_valid:
                return FetchResult(
                    source=source,
                    status=FetchStatus.INVALID,
                    data=[],
                    error="Invalid CSV format",
                    timestamp=timestamp,
                )
            
            fetch_time = time.time() - start_time
            data_hash = self.validator.calculate_hash(records)
            
            self.logger.info(f"Successfully fetched CSV from: {source} ({len(records)} records)")
            
            return FetchResult(
                source=source,
                status=FetchStatus.SUCCESS,
                data=records,
                fetch_time=fetch_time,
                timestamp=timestamp,
                data_hash=data_hash,
                record_count=len(records),
            )
        
        except Exception as e:
            self.logger.error(f"Error fetching CSV from {source}: {e}")
            return FetchResult(
                source=source,
                status=FetchStatus.FAILED,
                data=[],
                error=str(e),
                timestamp=timestamp,
            )

    def fetch_text(self, source: str) -> FetchResult:
        """Fetch plain text data."""
        timestamp = datetime.utcnow().isoformat()
        start_time = time.time()
        
        try:
            if self.validator.validate_url(source):
                import urllib.request
                with urllib.request.urlopen(source, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8")
            else:
                path = Path(source)
                if not path.exists():
                    return FetchResult(
                        source=source,
                        status=FetchStatus.FAILED,
                        data="",
                        error=f"File not found: {source}",
                        timestamp=timestamp,
                    )
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            fetch_time = time.time() - start_time
            data_hash = self.validator.calculate_hash(content)
            lines = content.split("\n")
            
            self.logger.info(f"Successfully fetched text from: {source}")
            
            return FetchResult(
                source=source,
                status=FetchStatus.SUCCESS,
                data=content,
                fetch_time=fetch_time,
                timestamp=timestamp,
                data_hash=data_hash,
                record_count=len([l for l in lines if l.strip()]),
            )
        
        except Exception as e:
            self.logger.error(f"Error fetching text from {source}: {e}")
            return FetchResult(
                source=source,
                status=FetchStatus.FAILED,
                data="",
                error=str(e),
                timestamp=timestamp,
            )


class DataAggregator:
    """Aggregates data from multiple sources."""

    def __init__(self, fetcher: DataFetcher):
        """Initialize aggregator."""
        self.fetcher = fetcher
        self.logger = logging.getLogger(__name__)
        self.results: List[FetchResult] = []

    def add_source(self, source: str, source_type: DataSourceType) -> FetchResult:
        """Fetch from a single source."""
        self.logger.info(f"Fetching from {source_type.value} source: {source}")
        
        if source_type == DataSourceType.FILE:
            result = self.fetcher.fetch_file(source)
        elif source_type == DataSourceType.JSON:
            result = self.fetcher.fetch_json(source)
        elif source_type == DataSourceType.CSV:
            result = self.fetcher.fetch_csv(source)
        elif source_type == DataSourceType.TEXT:
            result = self.fetcher.fetch_text(source)
        else:
            result = FetchResult(
                source=source,
                status=FetchStatus.FAILED,
                data="",
                error=f"Unknown source type: {source_type}",
                timestamp=datetime.utcnow().isoformat(),
            )
        
        self.results.append(result)
        return result

    def aggregate(self) -> Dict[str, Any]:
        """Aggregate all results."""
        total_records = sum(r.record_count for r in self.results)
        total_time = sum(r.fetch_time for r in self.results)
        successful = sum(1 for r in self.results if r.status == FetchStatus.SUCCESS)
        failed = sum(1 for r in self.results if r.status == FetchStatus.FAILED)
        
        return {
            "summary": {
                "total_sources": len(self.results),
                "successful": successful,
                "failed": failed,
                "total_records": total_records,
                "total_fetch_time": round(total_time, 3),
                "timestamp": datetime.utcnow().isoformat(),
            },
            "results": [r.to_dict() for r in self.results],
        }

    def clear(self):
        """Clear aggregated results."""
        self.results.clear()


def setup_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """Configure logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Accio: Production-ready data fetching and aggregation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source data.json --type json
  %(prog)s --source https://example.com/api/data.json --type json
  %(prog)s --source data.csv --type csv
  %(prog)s --source file1.json --type json --source file2.csv --type csv
        """,
    )
    
    parser.add_argument(
        "--source",
        action="append",
        required=False,
        help="Data source (file path or URL)",
    )
    
    parser.add_argument(
        "--type",
        action="append",
        choices=[t.value for t in DataSourceType],
        help="Source type (file, json, csv, text)",
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Fetch timeout in seconds (default: 30)",
    )
    
    parser.add_argument(
        "--retry-count",
        type=int,
        default=3,
        help="Number of retries for failed requests (default: 3)",
    )
    
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level (default: info)",
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (optional)",
    )
    
    parser.add_argument(
        "--output",
        help="Output file for aggregated results (optional)",
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with demo data",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize components
        fetcher = DataFetcher(
            timeout=args.timeout,
            retry_count=args.retry_count,
        )
        aggregator = DataAggregator(fetcher)
        
        # Process sources
        if args.demo:
            logger.info("Running in demo mode with sample data")
            run_demo(aggregator)
        else:
            if not args.source:
                parser.print_help()
                sys.exit(1)
            
            if not args.type or len(args.type) != len(args.source):
                logger.error("Number of --source and --type arguments must match")
                sys.exit(1)
            
            for source, source_type in zip(args.source, args.type):
                aggregator.add_source(source, DataSourceType(source_type))
        
        # Generate output
        result = aggregator.aggregate()
        output_json = json.dumps(result, indent=2)
        
        print(output_json)
        
        # Save to file if specified
        if args.output:
            Path(args.output).write_text(output_json)
            logger.info(f"Results saved to: {args.output}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


def run_demo(aggregator: DataAggregator) -> None:
    """Run with demo data."""
    logger = logging.getLogger(__name__)
    
    # Create demo files
    demo_dir = Path(".accio_demo")
    demo_dir.mkdir(exist_ok=True)
    
    # Demo JSON file
    demo_json = {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ],
        "count": 2,
    }
    json_file = demo_dir / "demo.json"
    json_file.write_text(json.dumps(
demo_json, indent=2))
    
    # Demo CSV file
    csv_content = """name,email,role
Alice,alice@example.com,admin
Bob,bob@example.com,user
Charlie,charlie@example.com,user"""
    csv_file = demo_dir / "demo.csv"
    csv_file.write_text(csv_content)
    
    # Demo text file
    text_content = """Sample text data
Line 1: Data point A
Line 2: Data point B
Line 3: Data point C"""
    text_file = demo_dir / "demo.txt"
    text_file.write_text(text_content)
    
    logger.info("Created demo files in .accio_demo/")
    
    # Fetch from all sources
    aggregator.add_source(str(json_file), DataSourceType.JSON)
    aggregator.add_source(str(csv_file), DataSourceType.CSV)
    aggregator.add_source(str(text_file), DataSourceType.TEXT)
    
    logger.info("Demo data aggregation complete")


if __name__ == "__main__":
    sys.exit(main())