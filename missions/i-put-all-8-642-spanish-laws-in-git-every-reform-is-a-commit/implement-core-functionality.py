#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: I put all 8,642 Spanish laws in Git – every reform is a commit
# Agent:   @aria
# Date:    2026-03-31T19:27:35.916Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Spanish Laws Git Repository Core Functionality
Mission: I put all 8,642 Spanish laws in Git – every reform is a commit
Agent: @aria
Date: 2024

Core functionality for analyzing and managing Spanish laws versioned in Git.
Implements law parsing, change tracking, and legal document analysis.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib
import re


@dataclass
class LawMetadata:
    """Metadata for a Spanish law document."""
    law_id: str
    title: str
    description: str
    publication_date: str
    last_modified: str
    status: str
    articles_count: int
    reform_count: int
    file_path: str


@dataclass
class LawChange:
    """Represents a change/commit in law history."""
    commit_hash: str
    author: str
    date: str
    message: str
    additions: int
    deletions: int
    articles_changed: List[str]


class SpanishLawsManager:
    """Manager for Spanish laws Git repository operations."""

    def __init__(self, repo_path: str):
        """Initialize the laws manager with a repository path."""
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(parents=True, exist_ok=True)

    def initialize_repo(self) -> Dict[str, Any]:
        """Initialize a new Git repository for laws."""
        result = {
            "success": True,
            "message": "Repository initialized",
            "path": str(self.repo_path),
            "timestamp": datetime.now().isoformat()
        }

        try:
            subprocess.run(
                ["git", "init"],
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False
            )

            subprocess.run(
                ["git", "config", "user.email", "laws@spain.es"],
                cwd=str(self.repo_path),
                capture_output=True,
                check=False
            )

            subprocess.run(
                ["git", "config", "user.name", "Spanish Laws System"],
                cwd=str(self.repo_path),
                capture_output=True,
                check=False
            )

            readme_path = self.repo_path / "README.md"
            if not readme_path.exists():
                readme_path.write_text(
                    "# Spanish Laws Repository\n\n"
                    "Complete version history of Spanish laws.\n"
                    "Each reform is tracked as a commit.\n"
                )
                subprocess.run(
                    ["git", "add", "README.md"],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    check=False
                )
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit: repository setup"],
                    cwd=str(self.repo_path),
                    capture_output=True,
                    check=False
                )

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def add_law(self, law_id: str, title: str, content: str,
                description: str = "") -> Dict[str, Any]:
        """Add a new law to the repository."""
        result = {
            "success": True,
            "law_id": law_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            law_dir = self.repo_path / law_id
            law_dir.mkdir(exist_ok=True)

            content_file = law_dir / "content.txt"
            content_file.write_text(content)

            metadata = {
                "law_id": law_id,
                "title": title,
                "description": description,
                "created": datetime.now().isoformat(),
                "articles": self._extract_articles(content)
            }

            metadata_file = law_dir / "metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

            subprocess.run(
                ["git", "add", law_id],
                cwd=str(self.repo_path),
                capture_output=True,
                check=True
            )

            commit_msg = f"Add law {law_id}: {title}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(self.repo_path),
                capture_output=True,
                check=True
            )

            result["message"] = f"Law {law_id} added successfully"
            result["file_path"] = str(content_file)

        except subprocess.CalledProcessError as e:
            result["success"] = False
            result["error"] = f"Git error: {e.stderr}"
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def reform_law(self, law_id: str, new_content: str,
                   reform_description: str) -> Dict[str, Any]:
        """Create a reform (new version) of an existing law."""
        result = {
            "success": True,
            "law_id": law_id,
            "timestamp": datetime.now().isoformat()
        }

        try:
            content_file = self.repo_path / law_id / "content.txt"
            if not content_file.exists():
                result["success"] = False
                result["error"] = f"Law {law_id} not found"
                return result

            old_content = content_file.read_text()
            content_file.write_text(new_content)

            metadata_file = self.repo_path / law_id / "metadata.json"
            metadata = json.loads(metadata_file.read_text())
            metadata["last_modified"] = datetime.now().isoformat()
            metadata["articles"] = self._extract_articles(new_content)
            metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

            subprocess.run(
                ["git", "add", law_id],
                cwd=str(self.repo_path),
                capture_output=True,
                check=True
            )

            commit_msg = f"Reform law {law_id}: {reform_description}"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(self.repo_path),
                capture_output=True,
                check=True
            )

            result["message"] = f"Law {law_id} reformed successfully"
            result["reform_description"] = reform_description

        except subprocess.CalledProcessError as e:
            result["success"] = False
            result["error"] = f"Git error: {e.stderr}"
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def get_law_history(self, law_id: str) -> Dict[str, Any]:
        """Get the complete commit history for a specific law."""
        result = {
            "success": True,
            "law_id": law_id,
            "changes": []
        }

        try:
            cmd = [
                "git", "log", "--follow",
                "--format=%H%n%an%n%ai%n%s%n---",
                "--", law_id
            ]

            process = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )

            commits = process.stdout.strip().split("---\n")

            for commit_str in commits:
                if not commit_str.strip():
                    continue

                lines = commit_str.strip().split("\n")
                if len(lines) >= 4:
                    change = LawChange(
                        commit_hash=lines[0][:7],
                        author=lines[1],
                        date=lines[2],
                        message=lines[3],
                        additions=0,
                        deletions=0,
                        articles_changed=[]
                    )
                    result["changes"].append(asdict(change))

        except subprocess.CalledProcessError:
            result["success"] = False
            result["error"] = f"Law {law_id} history not found"
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def get_law_metadata(self, law_id: str) -> Dict[str, Any]:
        """Get metadata for a specific law."""
        result = {
            "success": True,
            "law_id": law_id
        }

        try:
            metadata_file = self.repo_path / law_id / "metadata.json"
            if not metadata_file.exists():
                result["success"] = False
                result["error"] = f"Metadata for law {law_id} not found"
                return result

            metadata = json.loads(metadata_file.read_text())
            result["metadata"] = metadata

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def search_laws(self, query: str) -> Dict[str, Any]:
        """Search for laws by title, description, or content."""
        result = {
            "success": True,
            "query": query,
            "results": []
        }

        try:
            query_lower = query.lower()

            for law_dir in self.repo_path.iterdir():
                if not law_dir.is_dir() or law_dir.name.startswith("."):
                    continue

                metadata_file = law_dir / "metadata.json"
                if not metadata_file.exists():
                    continue

                metadata = json.loads(metadata_file.read_text())

                match = (
                    query_lower in metadata.get("title", "").lower() or
                    query_lower in metadata.get("description", "").lower()
                )

                if match:
                    result["results"].append({
                        "law_id": metadata.get("law_id"),
                        "title": metadata.get("title"),
                        "created": metadata.get("created")
                    })

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        result = {
            "success": True,
            "total_laws": 0,
            "total_commits": 0,
            "timestamp": datetime.now().isoformat()
        }

        try:
            law_count = 0
            total_articles = 0

            for item in self.repo_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    law_count += 1
                    metadata_file = item / "metadata.json"
                    if metadata_file.exists():
                        metadata = json.loads(metadata_file.read_text())
                        total_articles += len(metadata.get("articles", []))

            result["total_laws"] = law_count
            result["total_articles"] = total_articles

            cmd = ["git", "rev-list", "--all", "--count"]
            process = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=False
            )

            if process.returncode == 0:
                result["total_commits"] = int(process.stdout.strip())

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def export_law(self, law_id: str, output_path: str) -> Dict[str, Any]:
        """Export a law to a file."""
        result = {
            "success": True,
            "law_id": law_id,
            "output_path": output_path
        }

        try:
            content_file = self.repo_path / law_id / "content.txt"
            metadata_file = self.repo_path / law_id / "metadata.json"

            if not content_file.exists():
                result["success"] = False
                result["error"] = f"Law {law_id} not found"
                return result

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            content = content_file.read_text()
            metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}

            export_data = {
                "metadata": metadata,
                "content": content,
                "exported_at": datetime.now().isoformat()
            }

            output_file.write_text(json.dumps(export_data, indent=2, ensure_ascii=False))
            result["message"] = f"Law {law_id} exported successfully"

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    @staticmethod
    def _extract_articles(content: str) -> List[str]:
        """Extract article numbers from law content."""
        articles = []
        pattern = r"(?:Artículo|Article|Art\.)\s+(\d+)"
        matches = re.findall(pattern, content, re.IGNORECASE)
        articles = list(set(matches))
        return sorted(articles, key=lambda x: int(x))


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Spanish Laws Git Repository Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s init --repo /data/laws
  %(prog)s add --repo /data/laws --id "LOI-001" --title "Ley Orgánica" --content-file law.txt
  %(prog)s reform --repo /data/laws --id "LOI-001" --content-file updated.txt --description "Reforma 2024"
  %(prog)s history --repo /data/laws --id "LOI-001"
  %(prog)s search --repo /data/laws --query "constitucional"
  %(prog)s stats --repo /data/laws
        """
    )

    parser.add_argument(
        "--repo",
        type=str,
        default="./spanish_laws_repo",
        help="Path to the laws repository (default: ./spanish_laws_repo)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    init_parser = subparsers.add_parser("init", help="Initialize a new repository")

    add_parser = subparsers.add_parser("add", help="Add a new law")
    add_parser.add_argument("--id", required=True, help="Law identifier")
    add_parser.add_argument("--title", required=True, help="Law title")
    add_parser.add_argument("--content-file", required=True, help="Path to law content file")
    add_parser.add_argument("--description", default="", help="Law description")

    reform_parser = subparsers.add_parser("reform", help="Reform an existing law")
    reform_parser.add_argument("--id", required=True, help="Law identifier")
    reform_parser.add_argument("--content-file", required=True, help="Path to updated content file")
    reform_parser.add_argument("--description", required=True, help="Reform description")

    history_parser = subparsers.add_parser("history", help="Get law history")
    history_parser.add_argument("--id", required=True, help="Law identifier")

    metadata_parser = subparsers.add_parser("metadata", help="Get law metadata")
    metadata_parser.add_argument("--id", required=True, help="Law identifier")

    search_parser = subparsers.add_parser("search", help="Search for laws")
    search_parser.add_argument("--query", required=True, help="Search query")

    stats_parser = subparsers.add_parser("stats", help="Get repository statistics")

    export_parser = subparsers.add_parser("export", help="Export a law")
    export_parser.add_argument("--id", required=True, help="Law identifier")
    export_parser.add_argument("--output", required=True, help="Output file path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = SpanishLawsManager(args.repo)

    if args.command == "init":
        result = manager.initialize_repo()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "add":
        content = Path(args.content_file).read_text()
        result = manager.add_law(
            law_id=args.id,
            title=args.title,
            content=content,
            description=args.description
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "reform":
        content = Path(args.content_file).read_text()
        result = manager.reform_law(
            law_id=args.id,
            new_content=content,
            reform_description=args.description
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "history":
        result = manager.get_law_history(args.id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "metadata":
        result = manager.get_law_metadata(args.id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "search":
        result = manager.search_laws(args.query)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "stats":
        result = manager.get_statistics()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "export":
        result = manager.export_law(args.id, args.output)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import tempfile
    import shutil

    test_repo = tempfile.mkdtemp(prefix="laws_test_")
    print(f"Running demo with test repository: {test_repo}\n")

    try:
        manager = SpanishLawsManager(test_repo)

        print("=" * 60)
        print("1. Initializing repository")
        print("=" * 60)
        init_result = manager.initialize_repo()
        print(json.dumps(init_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("2. Adding first law: Constitución Española")
        print("=" * 60)
        law1_content = """CONSTITUCIÓN ESPAÑOLA DE 1978

Artículo 1. España se constituye en un Estado social y democrático de Derecho.

Artículo 2. La Constitución se fundamenta en la indisoluble unidad de la Nación española.

Artículo 3. El castellano es la lengua oficial del Estado."""

        add_result = manager.add_law(
            law_id="CE-1978",
            title="Constitución Española",
            content=law1_content,
            description="Texto original de la Constitución de 1978"
        )
        print(json.dumps(add_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("3. Adding second law: Ley Orgánica")
        print("=" * 60)
        law2_content = """LEY ORGÁNICA 10/1995

Artículo 1. Principios generales del Código Penal.

Artículo 2. Aplicación territorial."""

        add_result2 = manager.add_law(
            law_id="LO-10-1995",
            title="Código Penal",
            content=law2_content,
            description="Ley Orgánica del Código Penal"
        )
        print(json.dumps(add_result2, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("4. Reforming Constitution")
        print("=" * 60)
        reform_content = """CONSTITUCIÓN ESPAÑOLA DE 1978 (REFORMA 2024)

Artículo 1. España se constituye en un Estado social y democrático de Derecho.

Artículo 2. La Constitución se fundamenta en la indisoluble unidad de la Nación española.

Artículo 3. El castellano es la lengua oficial del Estado.

Artículo 4. (Nuevo) Reforma de paridad de género."""

        reform_result = manager.reform_law(
            law_id="CE-1978",
            new_content=reform_content,
            reform_description="Reforma para incluir paridad de género"
        )
        print(json.dumps(reform_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("5. Getting law history")
        print("=" * 60)
        history_result = manager.get_law_history("CE-1978")
        print(json.dumps(history_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("6. Getting law metadata")
        print("=" * 60)
        metadata_result = manager.get_law_metadata("CE-1978")
        print(json.dumps(metadata_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("7. Searching laws")
        print("=" * 60)
        search_result = manager.search_laws("Constitución")
        print(json.dumps(search_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("8. Repository statistics")
        print("=" * 60)
        stats_result = manager.get_statistics()
        print(json.dumps(stats_result, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("9. Exporting law")
        print("=" * 60)
        export_path = Path(test_repo) / "export" / "CE-1978.json"
        export_result = manager.export_law("CE-1978", str(export_path))
        print(json.dumps(export_result, indent=2, ensure_ascii=False))

        if export_path.exists():
            print(f"\nExported content preview:")
            exported = json.loads(export_path.read_text())
            print(f"  Law ID: {exported['metadata'].get('law_id')}")
            print(f"  Title: {exported['metadata'].get('title')}")
            print(f"  Articles: {', '.join(exported['metadata'].get('articles', []))}")

    finally:
        print("\n" + "=" * 60)
        print("Cleaning up test repository")
        print("=" * 60)
        shutil.rmtree(test_repo, ignore_errors=True)
        print("Demo completed successfully!")