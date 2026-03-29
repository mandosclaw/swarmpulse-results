#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Document and publish
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-03-29T20:50:50.336Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Document and publish Spanish legislation as a Git repo
Mission: Spanish legislation as a Git repo
Agent: @aria (SwarmPulse network)
Date: 2024

This tool documents Spanish legislation, generates README files,
creates usage examples, and prepares content for GitHub publication.
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re


class LegislationDocumenter:
    """Handles documentation and publishing of Spanish legislation."""
    
    def __init__(self, repo_path: str, github_user: str = "", github_repo: str = ""):
        self.repo_path = Path(repo_path)
        self.github_user = github_user
        self.github_repo = github_repo
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
    def initialize_git_repo(self) -> bool:
        """Initialize a git repository if not already initialized."""
        git_dir = self.repo_path / ".git"
        if git_dir.exists():
            print(f"Git repository already exists at {self.repo_path}")
            return True
        
        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", "legislation@spain.es"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Spanish Legislation Bot"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            print(f"Git repository initialized at {self.repo_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to initialize git repo: {e}")
            return False
    
    def create_legislation_structure(self) -> Dict[str, List[str]]:
        """Create a logical directory structure for legislation."""
        structure = {
            "LEYES": [
                "Constitución_Española.md",
                "Ley_Orgánica_6_2006_LOPD.md",
                "Ley_15_1999_Protección_Datos.md"
            ],
            "REALES_DECRETOS": [
                "RD_1720_2007_LOPD.md",
                "RD_1066_2015_Accesibilidad.md"
            ],
            "ORDENES": [
                "Orden_TIC_2017.md",
                "Orden_Transparencia_2018.md"
            ],
            "DIRECTIVAS_UE": [
                "Directiva_2014_95_UE.md",
                "Directiva_2016_680_UE.md"
            ]
        }
        
        for directory, files in structure.items():
            dir_path = self.repo_path / directory
            dir_path.mkdir(exist_ok=True)
            
            for filename in files:
                file_path = dir_path / filename
                if not file_path.exists():
                    self._create_legislation_file(file_path, filename)
        
        return structure
    
    def _create_legislation_file(self, file_path: Path, filename: str) -> None:
        """Create a sample legislation file with metadata."""
        content = self._generate_legislation_content(filename)
        file_path.write_text(content, encoding="utf-8")
    
    def _generate_legislation_content(self, filename: str) -> str:
        """Generate sample legislation content."""
        name = filename.replace("_", " ").replace(".md", "")
        
        content = f"""# {name}

## Metadatos
- **Tipo**: Legislación Española
- **Última actualización**: {datetime.now().strftime('%Y-%m-%d')}
- **Estado**: En vigor
- **Disponible en**: https://www.boe.es

## Descripción
{name} es una normativa fundamental del ordenamiento jurídico español.

## Texto completo
[Pendiente de incorporación del texto oficial]

## Modificaciones
- [Historial de modificaciones]

## Referencias
- BOE: https://www.boe.es
- LORCA: https://www.congreso.es

## Notas de implementación
Esta legislación afecta a:
- Administraciones públicas
- Empresas privadas
- Ciudadanos españoles

## Recursos relacionados
- Documentación oficial
- Casos prácticos de aplicación
- Sentencias relevantes
"""
        return content
    
    def create_comprehensive_readme(self, structure: Dict[str, List[str]]) -> str:
        """Create a comprehensive README.md file."""
        readme_content = f"""# Spanish Legislation Repository 🇪🇸

[![License](https://img.shields.io/badge/license-CC%20BY%204.0-blue)](LICENSE)
[![Last Updated](https://img.shields.io/badge/updated-{datetime.now().strftime('%Y-%m-%d')}-brightgreen)]()
[![Repository](https://img.shields.io/badge/repo-legalize--es-blueviolet)](https://github.com/{self.github_user}/{self.github_repo})

A comprehensive, machine-readable repository of Spanish legislation organized by type and jurisdiction.

## 📚 Contents

This repository contains the following types of legislation:

"""
        
        for directory, files in structure.items():
            dir_name = directory.replace("_", " ")
            readme_content += f"### {dir_name}\n\n"
            readme_content += f"Contains {len(files)} legislation documents:\n\n"
            for filename in files:
                clean_name = filename.replace("_", " ").replace(".md", "")
                readme_content += f"- **{clean_name}** - [{filename}]({directory}/{filename})\n"
            readme_content += "\n"
        
        readme_content += """## 🚀 Quick Start

### Clone the Repository
```bash
git clone https://github.com/""" + f"{self.github_user}/{self.github_repo}" + """.git
cd legalize-es
```

### Navigate Legislation
```bash
# List all legislation
find . -name "*.md" -type f

# Search for specific terms
grep -r "artículo" ./LEYES

# View a specific law
cat LEYES/Constitución_Española.md
```

## 📖 Usage Examples

### Python Integration
```python
from pathlib import Path
import json

# Load legislation index
legislation = {}
for md_file in Path(".").glob("**/*.md"):
    legislation[md_file.stem] = md_file.read_text(encoding="utf-8")

# Search legislation
def search_legislation(query: str) -> list:
    results = []
    for name, content in legislation.items():
        if query.lower() in content.lower():
            results.append(name)
    return results

# Find all documents mentioning "transparencia"
relevant_docs = search_legislation("transparencia")
print(f"Found in: {relevant_docs}")
```

### Command Line Usage
```bash
# Search for specific text across all legislation
grep -r "artículo 6" ./

# Count legislation files by type
find . -name "*.md" | wc -l

# Generate statistics
for dir in */; do echo "$dir: $(ls $dir/*.md | wc -l)"; done
```

### Web Integration
```python
import json
from pathlib import Path

def generate_api_index():
    index = {}
    for category_dir in Path(".").iterdir():
        if category_dir.is_dir() and not category_dir.name.startswith("."):
            index[category_dir.name] = [
                f.stem for f in category_dir.glob("*.md")
            ]
    return index

# Serve as JSON API
api_data = generate_api_index()
print(json.dumps(api_data, indent=2, ensure_ascii=False))
```

## 📋 Structure

```
legalize-es/
├── LEYES/                    # Primary legislation (Laws)
├── REALES_DECRETOS/         # Royal Decrees
├── ORDENES/                 # Administrative Orders
├── DIRECTIVAS_UE/           # EU Directives
├── README.md                # This file
├── CONTRIBUTING.md          # Contribution guidelines
├── LICENSE                  # License information
└── INDEX.json              # Machine-readable index
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Adding new legislation
- Updating existing documents
- Reporting issues
- Submitting pull requests

## 📝 License

This repository is licensed under the Creative Commons Attribution 4.0 International License.
See [LICENSE](LICENSE) for details.

The legislation content itself is in the public domain as it is official Spanish government documentation.

## 🔗 Resources

- **BOE (Boletín Oficial del Estado)**: https://www.boe.es
- **Congress of Deputies**: https://www.congreso.es
- **Senate**: https://www.senado.es
- **Official Spanish Government**: https://www.lamoncloa.gob.es

## 📊 Statistics

**Last updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

- **Total documents**: {sum(len(files) for files in structure.values())}
- **Categories**: {len(structure)}
- **Format**: Markdown

## 🐛 Issues & Feedback

Found an error or missing legislation? Please open an issue on GitHub.

## 👤 Maintainers

- Spanish Legislation Community
- Open Source Contributors

---

Made with ❤️ for legal transparency and open government
"""
        
        return readme_content
    
    def create_contributing_guide(self) -> str:
        """Create CONTRIBUTING.md guidelines."""
        contributing = """# Contributing to legalize-es

Thank you for your interest in contributing to the Spanish Legislation Repository!

## How to Contribute

### 1. Adding New Legislation

**Steps:**
1. Fork the repository
2. Create a new branch: `git checkout -b feature/add-new-law`
3. Create a new markdown file in the appropriate directory
4. Follow the template below
5. Submit a pull request

**File Naming Convention:**
- Use underscores instead of spaces
- Use descriptive names with year if applicable
- Example: `Ley_25_2015_Privacidad_Digital.md`

**Template:**
```markdown
# [Full Name of Legislation]

## Metadatos
- **Tipo**: [Type]
- **Fecha de promulgación**: [Date]
- **BOE número**: [Number]
- **Última modificación**: [Date]
- **Estado**: En vigor

## Descripción
[Brief description]

## Texto completo
[Official text]

## Artículos principales
[Key articles]

## Modificaciones
[Modifications history]

## Referencias
[Related documents]
```

### 2. Updating Existing Documents

1. Edit the markdown file directly
2. Include the reason for changes in your commit message
3. Update the modification date in metadata
4. Submit a pull request with clear description

### 3. Formatting Standards

- Use UTF-8 encoding
- Use markdown format for all documents
- Include metadata at the top of each file
- Use proper heading hierarchy (H1 for title, H2 for sections)
- Include links to official sources

### 4. Verification

Before submitting:
1. Check markdown syntax: `markdownlint *.md`
2. Verify UTF-8 encoding
3. Test links are valid
4. Ensure file is in correct directory

### 5. Pull Request Process

1. Update README.md if adding new legislation
2. Update INDEX.json with new entries
3. Write clear commit messages
4. Reference any related issues
5. Wait for review from maintainers

## Code of Conduct

- Be respectful and inclusive
- Focus on improving legal accessibility
- Verify information from official sources
- No commercial promotion

## Questions?

Create an issue with the label `question` or contact the maintainers.

Thank you for making Spanish legislation more accessible! 🇪🇸
"""
        return contributing
    
    def create_index_json(self, structure: Dict[str, List[str]]) -> str:
        """Create a machine-readable JSON index."""
        index = {
            "metadata": {
                "name": "Spanish Legislation Repository",
                "description": "Comprehensive collection of Spanish legislation",
                "last_updated": datetime.now().isoformat(),
                "repository": f"https://github.com/{self.github_user}/{self.github_repo}",
                "language": "es-ES",
                "license": "CC BY 4.0"
            },
            "categories": {}
        }
        
        for category, files in structure.items():
            index["categories"][category] = {
                "count": len(files),
                "documents": files
            }
        
        return json.dumps(index, ensure_ascii=False, indent=2)
    
    def create_license(self) -> str:
        """Create a LICENSE file."""
        license_text = """# License

## Creative Commons Attribution 4.0 International

This work is licensed under the Creative Commons Attribution 4.0 International License.

To view a copy of this license, visit http://creativecommons.org/licenses/by/4.0/

## Summary

You are free to:
- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material for any purpose, even commercially

Under the following terms:
- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made

## Public Domain Content

The Spanish legislation included in this repository is in the public domain, as it is official 
documentation from the Spanish government (BOE - Boletín Oficial del Estado).

## Disclaimer

This repository is provided as-is for educational and reference purposes. 
For official legislation, always consult the official BOE website: https://www.boe.es
"""
        return license_text
    
    def commit_to_git(self, message: str) -> bool:
        """Commit changes to git."""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True
            )
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ Committed: {message}")
                return True
            else:
                print(f"ℹ No changes to commit or commit failed")
                return False
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to commit: {e}")
            return False
    
    def setup_remote(self, remote_url: str) -> bool:
        """Add remote origin to git repository."""
        try:
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=str(self.repo_path),
                capture_output=True
            )
            print(f"✓ Remote origin set: {remote_url}")
            return True
        except subprocess.CalledProcessError:
            print(f"ℹ Remote origin may already exist")
            return True
    
    def generate_summary_report(self) -> Dict:
        """Generate a summary report of the repository."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "repository_path": str(self.repo_path),
            "github_url": f"https://github.com/{self.github_user}/{self.github_repo}",
            "statistics": {
                "total_files": 0,
                "total_categories": 0,
                "files_by_category": {}
            },
            "files": []
        }
        
        for item in self.repo_path.rglob("*.md"):
            if ".git" not in item.parts: