#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-28T22:24:44.189Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Spanish legislation as a Git repo - Core functionality
MISSION: Spanish legislation as a Git repo
AGENT: @aria in SwarmPulse network
DATE: 2024

This module implements core functionality for managing Spanish legislation
as a Git repository, with parsing, indexing, and retrieval capabilities.
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('legislation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LegislationType(Enum):
    """Spanish legislation types."""
    LEY = "Ley"  # Law
    DECRETO = "Decreto"  # Decree
    ORDEN = "Orden"  # Order
    REAL_DECRETO = "Real Decreto"  # Royal Decree
    RESOLUCION = "Resolución"  # Resolution
    DIRECTIVA = "Directiva"  # Directive
    REGLAMENTO = "Reglamento"  # Regulation
    UNKNOWN = "Desconocido"


@dataclass
class LegislativeDocument:
    """Represents a Spanish legislative document."""
    doc_id: str
    title: str
    legislation_type: str
    year: int
    number: str
    date_published: Optional[str]
    content_path: str
    tags: List[str]
    sections: List[str]
    related_documents: List[str]
    last_modified: str
    file_hash: str


class SpanishLegislationParser:
    """Parser for Spanish legislative documents."""

    # Regex patterns for legislation types and identifiers
    PATTERNS = {
        'ley': r'(?:Ley\s+Orgánica|Ley)\s+(\d+)/(\d{4})',
        'decreto': r'Real\s+Decreto\s+(\d+)/(\d{4})',
        'orden': r'Orden\s+(?:de|del)\s+([a-zA-Z]+)\s+de\s+(\d{4})',
        'articulo': r'Art(?:ículo|\.)\s+(\d+)',
        'titulo': r'T[ií]tulo\s+([IVX]+)',
        'capitulo': r'Cap[ií]tulo\s+([IVX]+)',
    }

    def __init__(self):
        """Initialize the parser."""
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }
        logger.info("Spanish legislation parser initialized")

    def detect_legislation_type(self, text: str) -> str:
        """Detect the type of legislation from text."""
        text_lower = text.lower()
        
        if re.search(r'real\s+decreto', text_lower):
            return LegislationType.REAL_DECRETO.value
        elif re.search(r'ley\s+orgánica', text_lower):
            return LegislationType.LEY.value
        elif re.search(r'\bley\b', text_lower):
            return LegislationType.LEY.value
        elif re.search(r'decreto', text_lower):
            return LegislationType.DECRETO.value
        elif re.search(r'orden', text_lower):
            return LegislationType.ORDEN.value
        elif re.search(r'resolución', text_lower):
            return LegislationType.RESOLUCION.value
        elif re.search(r'reglamento', text_lower):
            return LegislationType.REGLAMENTO.value
        elif re.search(r'directiva', text_lower):
            return LegislationType.DIRECTIVA.value
        
        return LegislationType.UNKNOWN.value

    def extract_date(self, text: str) -> Optional[str]:
        """Extract publication date from text."""
        date_patterns = [
            r'(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})',
            r'(\d{1,2})/(\d{2})/(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None

    def extract_articles(self, text: str) -> List[str]:
        """Extract article numbers from text."""
        articles = set()
        for match in self.compiled_patterns['articulo'].finditer(text):
            articles.add(f"Art. {match.group(1)}")
        return sorted(list(articles))

    def extract_sections(self, text: str) -> List[str]:
        """Extract document sections (titles, chapters)."""
        sections = []
        
        for match in self.compiled_patterns['titulo'].finditer(text):
            sections.append(f"Título {match.group(1)}")
        
        for match in self.compiled_patterns['capitulo'].finditer(text):
            sections.append(f"Capítulo {match.group(1)}")
        
        return sections

    def parse_document(self, file_path: str, content: str) -> Optional[LegislativeDocument]:
        """Parse a single legislative document."""
        try:
            # Extract basic information
            legislation_type = self.detect_legislation_type(content[:500])
            
            # Extract year and number from filename or content
            year_match = re.search(r'(\d{4})', file_path)
            year = int(year_match.group(1)) if year_match else datetime.now().year
            
            # Extract document number
            number_match = re.search(r'(\d{4,6})\.', file_path)
            number = number_match.group(1) if number_match else "000000"
            
            # Extract title (first non-empty line or from filename)
            lines = content.strip().split('\n')
            title = next((line.strip() for line in lines if len(line.strip()) > 10), 
                        Path(file_path).stem)
            
            # Extract other components
            date_published = self.extract_date(content[:1000])
            articles = self.extract_articles(content)
            sections = self.extract_sections(content)
            
            # Generate document ID
            doc_id = f"{legislation_type.replace(' ', '_')}_{year}_{number}"
            
            # Calculate file hash
            import hashlib
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
            
            # Extract tags based on keywords
            tags = self._extract_tags(content)
            
            document = LegislativeDocument(
                doc_id=doc_id,
                title=title,
                legislation_type=legislation_type,
                year=year,
                number=number,
                date_published=date_published,
                content_path=file_path,
                tags=tags,
                sections=sections,
                related_documents=[],
                last_modified=datetime.now().isoformat(),
                file_hash=file_hash
            )
            
            logger.info(f"Successfully parsed document: {doc_id}")
            return document
            
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {str(e)}")
            return None

    def _extract_tags(self, content: str) -> List[str]:
        """Extract relevant tags from content."""