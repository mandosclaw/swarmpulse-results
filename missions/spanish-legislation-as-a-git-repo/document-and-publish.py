#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Document and publish
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-28T22:24:47.367Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Document and publish Spanish legislation as a Git repo
Mission: Spanish legislation as a Git repo
Agent: @aria (SwarmPulse network)
Date: 2024

This tool helps document and prepare Spanish legislation repositories for GitHub publishing.
It generates comprehensive README files, usage examples, and validates repository structure.
"""

import argparse
import json
import os
import sys
import subprocess
import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class LegislationDocumenter:
    """Generate and manage documentation for legislation repositories."""
    
    def __init__(self, repo_path: str, repo_name: str = "legalize-es"):
        self.repo_path = Path(repo_path)
        self.repo_name = repo_name
        self.created_at = datetime.datetime.now().isoformat()
        self.repo_path.mkdir(parents=True, exist_ok=True)
    
    def create_readme(self, output_file: str = "README.md") -> str:
        """Generate comprehensive README for the legislation repository."""
        readme_content = f"""# {self.repo_name.replace('-', ' ').title()}

[![License](https://img.shields.io/badge/license-CC0%201.0-blue.svg)](LICENSE)
[![Last Updated](https://img.shields.io/badge/last%20updated-{datetime.date.today().isoformat()}-brightgreen)]()

> Spanish legislation and legal documents organized as a Git repository for version control, collaboration, and accessibility.

## Overview

This repository maintains a comprehensive collection of Spanish legislation, including:

- **Constitutional Laws** (Leyes Orgánicas)
- **Ordinary Laws** (Leyes Ordinarias)
- **Royal Decrees** (Reales Decretos)
- **Ministerial Orders** (Órdenes Ministeriales)
- **Regulations** (Reglamentos)
- **European Union Directives** (Directivas UE)

## Features

✅ **Version Control**: Track changes and amendments to legislation over time
✅ **Searchable Format**: Full-text search capabilities across all documents
✅ **Structured Data**: Organized by legal area and jurisdiction
✅ **Open Access**: Free and open to contribute or use
✅ **Machine Readable**: JSON, XML, and plain text formats
✅ **Citation Support**: Proper legal references and cross-links

## Repository Structure

```
{self.repo_name}/
├── README.md                 # This file
├── LICENSE                   # CC0 1.0 Universal License
├── CONTRIBUTING.md           # Contribution guidelines
├── docs/                     # Documentation
│   ├── structure.md         # Repository structure guide
│   ├── formats.md           # Data format specifications
│   └── legal-areas.md       # Legal areas covered
├── legislation/              # Main legislation directory
│   ├── constitution/         # Spanish Constitution
│   ├── civil/               # Civil Law
│   ├── penal/               # Criminal Law
│   ├── administrative/      # Administrative Law
│   ├── labor/               # Labor Law
│   ├── commercial/          # Commercial Law
│   ├── environmental/       # Environmental Law
│   ├── data-protection/     # Data Protection
│   ├── eu-directives/       # EU Directives
│   └── other/               # Other legislation
├── data/                     # Structured data
│   ├── metadata.json        # Document metadata
│   ├── index.json           # Full index
│   └── statistics.json      # Repository statistics
├── tools/                    # Utility scripts
│   ├── parser.py           # Text parsing utilities
│   ├── validator.py        # Data validation
│   └── search.py           # Search functionality
├── tests/                    # Test suite
│   ├── test_structure.py    # Structure tests
│   └── test_content.py      # Content validation tests
└── .gitignore               # Git ignore rules

```

## Getting Started

### Prerequisites

- Git (for cloning and version control)
- Python 3.8+ (for utilities and tools)
- Text editor or IDE (for browsing/editing documents)

### Installation

```bash
# Clone the repository
git clone https://github.com/EnriqueLop/{self.repo_name}.git
cd {self.repo_name}

# Install Python dependencies (optional)
pip install -r requirements.txt
```

### Quick Start

#### 1. Browse Legislation

Navigate to the `legislation/` directory to find documents organized by legal area:

```bash
ls legislation/
# Output: administrative civil commercial constitution data-protection ...
```

#### 2. Search for Specific Laws

```bash
# Use grep to search across documents
grep -r "derecho" legislation/ --include="*.txt"
```

#### 3. View Document Metadata

```bash
# Check metadata for all documents
python tools/search.py --index data/metadata.json
```

#### 4. Use Python Tools

```python
from tools.parser import LegislationParser

parser = LegislationParser()
documents = parser.load_from_directory("legislation/")
results = parser.search("protección de datos", documents)

for doc in results:
    print(f"{{doc['title']}} - {{doc['year']}}")
```

## Usage Examples

### Example 1: Finding Laws by Topic

```bash
# Search for data protection laws
grep -r "Protección de Datos" legislation/data-protection/ --include="*.txt"
```

### Example 2: Accessing Structured Data

```bash
# View index of all documents
cat data/index.json | python -m json.tool | head -50
```

### Example 3: Using the Parser Tool

```python
from tools.parser import LegislationParser
import json

parser = LegislationParser()
stats = parser.generate_statistics("legislation/")

with open("data/statistics.json", "w") as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)
```

### Example 4: Validating Documents

```bash
# Validate all documents in a directory
python tools/validator.py --directory legislation/ --format json
```

### Example 5: Creating Custom Indexes

```python
from tools.parser import LegislationParser

parser = LegislationParser()
index = parser.create_custom_index(
    root_dir="legislation/",
    areas=["civil", "commercial"],
    year_range=(2020, 2024)
)

for entry in index:
    print(f"{{entry['title']}} ({{entry['year']}})")
```

## Data Formats

### JSON Format

Legislation documents include metadata in JSON format:

```json
{
  "id": "LOrgánica/2018/3",
  "type": "Ley Orgánica",
  "title": "Protección de Datos Personales",
  "area": "data-protection",
  "year": 2018,
  "number": 3,
  "status": "vigente",
  "official_gazette": "BOE",
  "publication_date": "2018-12-05",
  "last_modified": "2023-01-15",
  "amendments": 12,
  "related_documents": [
    "Regulación/UE/2016/679",
    "Real Decreto/1720/1890"
  ]
}
```

### Plain Text Format

Raw legislative text with document metadata header.

### XML Format

Structured XML representation for machine processing.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### How to Contribute

1. **Fork** the repository
2. **Create a branch** (`git checkout -b feature/add-new-legislation`)
3. **Add or update documents** in the appropriate directory
4. **Update metadata** in `data/metadata.json`
5. **Run tests** to ensure validity
6. **Commit** with clear messages
7. **Push** to your fork
8. **Create a Pull Request**

### Contribution Areas

- Adding missing legislation
- Updating outdated documents
- Improving documentation
- Adding translations
- Creating search indexes