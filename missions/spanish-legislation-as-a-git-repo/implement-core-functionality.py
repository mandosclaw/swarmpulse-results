#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-04-01T17:17:12.670Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Spanish legislation as a Git repo - Core functionality implementation
MISSION: Engineering
AGENT: @aria (SwarmPulse network)
DATE: 2024

Spanish legislation repository manager - fetches, parses, and manages Spanish laws
from the legalize-es GitHub repository with full error handling and logging.
"""

import argparse
import json
import logging
import os
import sys
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from dataclasses import dataclass, asdict
from enum import Enum


class LegislationType(Enum):
    """Types of Spanish legislation"""
    ORGANIC_LAW = "Ley Orgánica"
    ORDINARY_LAW = "Ley Ordinaria"
    ROYAL_DECREE = "Real Decreto"
    RESOLUTION = "Resolución"
    ORDER = "Orden"
    UNKNOWN = "Desconocido"


@dataclass
class LegislativeDocument:
    """Represents a Spanish legislative document"""
    identifier: str
    title: str
    doc_type: LegislationType
    date_published: str
    content: str
    file_path: str
    checksum: str
    repository_url: str

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "identifier": self.identifier,
            "title": self.title,
            "doc_type": self.doc_type.value,
            "date_published": self.date_published,
            "checksum": self.checksum,
            "file_path": self.file_path,
            "repository_url": self.repository_url,
            "content_length": len(self.content)
        }


class SpanishLegislationManager:
    """Manages Spanish legislation repository operations"""

    DEFAULT_REPO_URL = "https://github.com/EnriqueLop/legalize-es.git"
    GITHUB_API_BASE = "https://api.github.com/repos/EnriqueLop/legalize-es"

    def __init__(self, repo_path: str, log_level: str = "INFO"):
        """Initialize the legislation manager"""
        self.repo_path = Path(repo_path)
        self.logger = self._setup_logging(log_level)
        self.documents: Dict[str, LegislativeDocument] = {}

    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def clone_repository(self, url: Optional[str] = None, force: bool = False) -> bool:
        """Clone the Spanish legislation repository"""
        try:
            repo_url = url or self.DEFAULT_REPO_URL
            self.logger.info(f"Cloning repository from {repo_url}")

            if self.repo_path.exists() and force:
                self.logger.warning(f"Removing existing repository at {self.repo_path}")
                subprocess.run(
                    ["rm", "-rf", str(self.repo_path)],
                    check=True,
                    capture_output=True
                )

            if self.repo_path.exists():
                self.logger.info(f"Repository already exists at {self.repo_path}")
                return True

            self.repo_path.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                ["git", "clone", repo_url, str(self.repo_path)],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to clone repository: {result.stderr}")
                return False

            self.logger.info(f"Successfully cloned repository to {self.repo_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error cloning repository: {str(e)}")
            return False

    def get_repository_info(self) -> Dict:
        """Get repository information using git commands"""
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "remote", "-v"],
                capture_output=True,
                text=True,
                timeout=10
            )

            remote_url = None
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines:
                    remote_url = lines[0].split()[1]

            head_result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )

            commit_hash = head_result.stdout.strip() if head_result.returncode == 0 else "unknown"

            log_result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--oneline", "-1"],
                capture_output=True,
                text=True,
                timeout=10
            )

            latest_commit = log_result.stdout.strip() if log_result.returncode == 0 else "unknown"

            return {
                "repository_url": remote_url or self.DEFAULT_REPO_URL,
                "commit_hash": commit_hash,
                "latest_commit": latest_commit,
                "path": str(self.repo_path),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting repository info: {str(e)}")
            return {}

    def parse_legislation_files(self) -> List[LegislativeDocument]:
        """Parse and extract legislation from repository files"""
        try:
            if not self.repo_path.exists():
                self.logger.error(f"Repository path does not exist: {self.repo_path}")
                return []

            self.logger.info(f"Parsing legislation files from {self.repo_path}")
            documents = []

            for file_path in self.repo_path.rglob("*"):
                if file_path.is_file() and file_path.suffix in [".md", ".txt", ".json"]:
                    try:
                        doc = self._parse_file(file_path)
                        if doc:
                            documents.append(doc)
                            self.documents[doc.identifier] = doc
                    except Exception as e:
                        self.logger.warning(f"Error parsing {file_path}: {str(e)}")

            self.logger.info(f"Parsed {len(documents)} legislative documents")
            return documents

        except Exception as e:
            self.logger.error(f"Error parsing legislation files: {str(e)}")
            return []

    def _parse_file(self, file_path: Path) -> Optional[LegislativeDocument]:
        """Parse a single legislation file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                return None

            identifier = self._extract_identifier(file_path, content)
            title = self._extract_title(content)
            doc_type = self._detect_document_type(content)
            date_published = self._extract_date(content)
            checksum = self._compute_checksum(content)

            return LegislativeDocument(
                identifier=identifier,
                title=title,
                doc_type=doc_type,
                date_published=date_published,
                content=content[:10000],
                file_path=str(file_path),
                checksum=checksum,
                repository_url=self.DEFAULT_REPO_URL
            )

        except Exception as e:
            self.logger.debug(f"Error parsing file {file_path}: {str(e)}")
            return None

    def _extract_identifier(self, file_path: Path, content: str) -> str:
        """Extract document identifier"""
        filename_base = file_path.stem
        if filename_base:
            return filename_base

        for line in content.split('\n')[:20]:
            if any(prefix in line for prefix in ["BOE", "Real Decreto", "Ley"]):
                return line.strip()[:50]

        return f"DOC_{file_path.stat().st_ino}"

    def _extract_title(self, content: str) -> str:
        """Extract document title from content"""
        lines = content.split('\n')
        for line in lines[:30]:
            stripped = line.strip()
            if stripped and len(stripped) > 10 and len(stripped) < 300:
                if not stripped.startswith('#'):
                    return stripped
                return stripped.lstrip('#').strip()

        return "Sin título"

    def _detect_document_type(self, content: str) -> LegislationType:
        """Detect the type of legislative document"""
        content_lower = content.lower()

        type_keywords = {
            LegislationType.ORGANIC_LAW: ["ley orgánica", "lo"],
            LegislationType.ORDINARY_LAW: ["ley ordinaria", "ley número"],
            LegislationType.ROYAL_DECREE: ["real decreto", "rd"],
            LegislationType.RESOLUTION: ["resolución", "resuelve"],
            LegislationType.ORDER: ["orden ministerial", "orden"],
        }

        for leg_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return leg_type

        return LegislationType.UNKNOWN

    def _extract_date(self, content: str) -> str:
        """Extract publication date from content"""
        import re

        date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}'
        matches = re.findall(date_pattern, content)

        if matches:
            return matches[0]

        return datetime.now().isoformat()

    def _compute_checksum(self, content: str) -> str:
        """Compute SHA256 checksum of content"""
        return hashlib.sha256(content.encode()).hexdigest()

    def search_legislation(self, query: str, by_field: str = "title") -> List[LegislativeDocument]:
        """Search legislation by query"""
        try:
            query_lower = query.lower()
            results = []

            for doc in self.documents.values():
                if by_field == "title":
                    if query_lower in doc.title.lower():
                        results.append(doc)
                elif by_field == "content":
                    if query_lower in doc.content.lower():
                        results.append(doc)
                elif by_field == "type":
                    if query_lower in doc.doc_type.value.lower():
                        results.append(doc)

            self.logger.info(f"Search for '{query}' returned {len(results)} results")
            return results

        except Exception as e:
            self.logger.error(f"Error searching legislation: {str(e)}")
            return []

    def filter_by_type(self, doc_type: LegislationType) -> List[LegislativeDocument]:
        """Filter documents by type"""
        return [doc for doc in self.documents.values() if doc.doc_type == doc_type]

    def export_to_json(self, output_path: str) -> bool:
        """Export parsed documents to JSON"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_documents": len(self.documents),
                "repository_info": self.get_repository_info(),
                "documents": [doc.to_dict() for doc in self.documents.values()]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported {len(self.documents)} documents to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {str(e)}")
            return False

    def get_statistics(self) -> Dict:
        """Get repository statistics"""
        if not self.documents:
            return {}

        type_counts = {}
        for doc in self.documents.values():
            type_name = doc.doc_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_documents": len(self.documents),
            "documents_by_type": type_counts,
            "latest_update": datetime.now().isoformat(),
            "repository_url": self.DEFAULT_REPO_URL
        }


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Spanish legislation repository manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python3 solution.py --action clone --repo-path ./legalize-es"
    )

    parser.add_argument(
        "--action",
        choices=["clone", "parse", "search", "stats", "export", "info"],
        default="parse",
        help="Action to perform (default: parse)"
    )

    parser.add_argument(
        "--repo-path",
        type=str,
        default="./legalize-es",
        help="Path to legislation repository (default: ./legalize-es)"
    )

    parser.add_argument(
        "--repo-url",
        type=str,
        default=None,
        help="Repository URL to clone from"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force clone even if repository exists"
    )

    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Search query string"
    )

    parser.add_argument(
        "--search-field",
        choices=["title", "content", "type"],
        default="title",
        help="Field to search in (default: title)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path for export"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    manager = SpanishLegislationManager(args.repo_path, args.log_level)

    if args.action == "clone":
        success = manager.clone_repository(args.repo_url, args.force)
        sys.exit(0 if success else 1)

    elif args.action == "parse":
        manager.clone_repository(args.repo_url, False)
        documents = manager.parse_legislation_files()
        print(json.dumps(
            {
                "status": "success",
                "documents_parsed": len(documents),
                "timestamp": datetime.now().isoformat()
            },
            indent=2
        ))

    elif args.action == "search":
        if not args.query:
            print("Error: --query required for search action", file=sys.stderr)
            sys.exit(1)
        manager.parse_legislation_files()
        results = manager.search_legislation(args.query, args.search_field)
        print(json.dumps(
            {
                "query": args.query,
                "results_count": len(results),
                "results": [doc.to_dict() for doc in results]
            },
            indent=2,
            ensure_ascii=False
        ))

    elif args.action == "stats":
        manager.parse_legislation_files()
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif args.action == "export":
        if not args.output:
            print("Error: --output required for export action", file=sys.stderr)
            sys.exit(1)
        manager.parse_legislation_files()
        success = manager.export_to_json(args.output)
        sys.exit(0 if success else 1)

    elif args.action == "info":
        info = manager.get_repository_info()
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()