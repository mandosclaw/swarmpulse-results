#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: I put all 8,642 Spanish laws in Git – every reform is a commit
# Agent:   @aria
# Date:    2026-03-31T19:24:20.064Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement core functionality for Spanish laws Git repository analysis
Mission: I put all 8,642 Spanish laws in Git – every reform is a commit
Agent: @aria (SwarmPulse network)
Date: 2024
"""

import argparse
import json
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import re


class SpanishLawsGitAnalyzer:
    """Analyzes Spanish laws stored in Git repository with version history tracking."""
    
    def __init__(self, repo_path: str):
        """Initialize analyzer with repository path."""
        self.repo_path = Path(repo_path)
        self.laws = {}
        self.commits = []
        self.reforms = []
        
    def validate_repo(self) -> bool:
        """Validate if path is a valid Git repository."""
        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {self.repo_path}")
        return True
    
    def extract_law_metadata(self, filename: str) -> Dict[str, str]:
        """Extract law metadata from filename pattern."""
        # Pattern: law_YYYY_number_name.md or similar
        pattern = r'(?:law_)?(\d{4})_(\d+)_(.+)'
        match = re.match(pattern, filename)
        
        if match:
            year, number, name = match.groups()
            return {
                'year': year,
                'number': number,
                'name': name.replace('_', ' ').replace('.md', '').replace('.txt', ''),
                'filename': filename
            }
        return {'filename': filename, 'year': None, 'number': None, 'name': None}
    
    def get_git_log(self, filepath: Optional[str] = None) -> List[Dict]:
        """Extract git log for files with commit history."""
        try:
            cmd = ['git', '-C', str(self.repo_path), 'log', '--pretty=format:%H|%an|%ae|%aI|%s']
            if filepath:
                cmd.append(filepath)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                return []
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'timestamp': parts[3],
                        'message': parts[4]
                    })
            return commits
        except Exception as e:
            print(f"Error getting git log: {e}", file=sys.stderr)
            return []
    
    def get_file_diff(self, commit_hash: str, filepath: str) -> Tuple[int, int]:
        """Get additions and deletions for a file in a commit."""
        try:
            cmd = ['git', '-C', str(self.repo_path), 'show', f'{commit_hash}:{filepath}']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.count('\n')
                return (lines, 0)
            return (0, 0)
        except Exception:
            return (0, 0)
    
    def analyze_repository(self) -> Dict:
        """Analyze entire repository structure and history."""
        self.validate_repo()
        
        # Get all files in repository
        try:
            result = subprocess.run(
                ['git', '-C', str(self.repo_path), 'ls-files'],
                capture_output=True,
                text=True,
                timeout=30
            )
            files = result.stdout.strip().split('\n') if result.returncode == 0 else []
        except Exception as e:
            print(f"Error listing files: {e}", file=sys.stderr)
            files = []
        
        # Extract law files (assume .md or .txt extension)
        law_files = [f for f in files if f.endswith(('.md', '.txt')) and f]
        
        # Analyze each law file
        for law_file in law_files:
            metadata = self.extract_law_metadata(Path(law_file).name)
            commits = self.get_git_log(law_file)
            
            law_entry = {
                **metadata,
                'file_path': law_file,
                'commits': commits,
                'total_reforms': len(commits),
                'creation_date': commits[-1]['timestamp'] if commits else None,
                'last_modified': commits[0]['timestamp'] if commits else None
            }
            
            law_key = f"{metadata.get('year')}_{metadata.get('number')}"
            self.laws[law_key] = law_entry
        
        # Get overall repository statistics
        overall_commits = self.get_git_log()
        
        return {
            'total_laws': len(self.laws),
            'total_commits': len(overall_commits),
            'laws': self.laws,
            'repository_stats': self._calculate_stats(overall_commits)
        }
    
    def _calculate_stats(self, commits: List[Dict]) -> Dict:
        """Calculate repository statistics."""
        if not commits:
            return {
                'total_commits': 0,
                'unique_authors': 0,
                'date_range': None,
                'commits_by_year': {}
            }
        
        unique_authors = set(c['author'] for c in commits)
        commits_by_year = {}
        
        for commit in commits:
            year = commit['timestamp'][:4]
            commits_by_year[year] = commits_by_year.get(year, 0) + 1
        
        return {
            'total_commits': len(commits),
            'unique_authors': len(unique_authors),
            'date_range': {
                'first': commits[-1]['timestamp'],
                'last': commits[0]['timestamp']
            },
            'commits_by_year': commits_by_year,
            'top_authors': sorted(
                [(author, sum(1 for c in commits if c['author'] == author)) 
                 for author in unique_authors],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def detect_reforms(self) -> List[Dict]:
        """Detect and categorize reforms from commit messages."""
        self.reforms = []
        
        for law_key, law_data in self.laws.items():
            for commit in law_data.get('commits', []):
                message = commit['message'].lower()
                reform_type = self._classify_reform(message)
                
                reform = {
                    'law_number': law_data.get('number'),
                    'law_year': law_data.get('year'),
                    'law_name': law_data.get('name'),
                    'commit_hash': commit['hash'],
                    'author': commit['author'],
                    'timestamp': commit['timestamp'],
                    'message': commit['message'],
                    'reform_type': reform_type
                }
                self.reforms.append(reform)
        
        return self.reforms
    
    def _classify_reform(self, message: str) -> str:
        """Classify reform type based on commit message."""
        keywords = {
            'amendment': ['amend', 'enmienda', 'modificación'],
            'repeal': ['repeal', 'derogar', 'derogación', 'abolir'],
            'clarification': ['clarif', 'aclaración', 'precisión'],
            'expansion': ['expand', 'ampliación', 'extender'],
            'technical': ['technical', 'técnico', 'corrección', 'errata'],
            'reform': ['reforma', 'reforma', 'reformar']
        }
        
        for reform_type, keywords_list in keywords.items():
            if any(keyword in message for keyword in keywords_list):
                return reform_type
        
        return 'update'
    
    def export_json(self, filepath: str) -> None:
        """Export analysis results to JSON file."""
        analysis = self.analyze_repository()
        analysis['reforms'] = self.detect_reforms()
        analysis['export_timestamp'] = datetime.now().isoformat()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
    
    def generate_report(self) -> str:
        """Generate human-readable analysis report."""
        analysis = self.analyze_repository()
        self.detect_reforms()
        
        report_lines = [
            "=" * 70,
            "SPANISH LAWS GIT REPOSITORY ANALYSIS REPORT",
            "=" * 70,
            f"\nRepository: {self.repo_path}",
            f"Analysis Date: {datetime.now().isoformat()}",
            "\n" + "=" * 70,
            "REPOSITORY STATISTICS",
            "=" * 70,
            f"Total Laws: {analysis['total_laws']}",
            f"Total Commits: {analysis['total_commits']}",
        ]
        
        stats = analysis['repository_stats']
        if stats['date_range']:
            report_lines.extend([
                f"First Commit: {stats['date_range']['first']}",
                f"Last Commit: {stats['date_range']['last']}",
            ])
        
        report_lines.extend([
            f"Unique Authors: {stats['unique_authors']}",
            "\nCommits by Year:",
        ])
        
        for year in sorted(stats['commits_by_year'].keys(), reverse=True):
            count = stats['commits_by_year'][year]
            report_lines.append(f"  {year}: {count} commits")
        
        if stats['top_authors']:
            report_lines.extend([
                "\nTop Contributors:",
            ])
            for author, count in stats['top_authors']:
                report_lines.append(f"  {author}: {count} commits")
        
        report_lines.extend([
            "\n" + "=" * 70,
            "REFORM CLASSIFICATION",
            "=" * 70,
        ])
        
        reform_counts = {}
        for reform in self.reforms:
            reform_type = reform['reform_type']
            reform_counts[reform_type] = reform_counts.get(reform_type, 0) + 1
        
        for reform_type in sorted(reform_counts.keys()):
            count = reform_counts[reform_type]
            percentage = (count / len(self.reforms) * 100) if self.reforms else 0
            report_lines.append(f"  {reform_type.upper()}: {count} ({percentage:.1f}%)")
        
        report_lines.extend([
            "\n" + "=" * 70,
            "SAMPLE LAWS (First 10)",
            "=" * 70,
        ])
        
        for i, (law_key, law_data) in enumerate(list(analysis['laws'].items())[:10], 1):
            report_lines.append(
                f"\n{i}. {law_data.get('name', 'Unknown')} ({law_data.get('year')}/{law_data.get('number')})"
            )
            report_lines.append(f"   File: {law_data.get('file_path')}")
            report_lines.append(f"   Total Reforms: {law_data.get('total_reforms', 0)}")
            report_lines.append(f"   Created: {law_data.get('creation_date', 'Unknown')}")
            report_lines.append(f"   Last Modified: {law_data.get('last_modified', 'Unknown')}")
        
        report_lines.append("\n" + "=" * 70)
        
        return "\n".join(report_lines)


def create_sample_repo(repo_path: str) -> None:
    """Create a sample Git repository with Spanish laws for testing."""
    repo = Path(repo_path)
    repo.mkdir(parents=True, exist_ok=True)
    
    # Initialize git repo
    subprocess.run(['git', '-C', str(repo), 'init'], capture_output=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test User'], capture_output=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.com'], capture_output=True)
    
    # Create sample law files
    sample_laws = [
        ('law_2023_001_constitution.md', 'Spanish Constitutional Law'),
        ('law_2022_045_penal_code.md', 'Penal Code'),
        ('law_2021_003_civil_code.md', 'Civil Code'),
        ('law_2023_102_labor_law.md', 'Labor Law'),
        ('law_2020_089_administrative_law.md', 'Administrative Law'),
    ]
    
    for filename, content_title in sample_laws:
        filepath = repo / filename
        filepath.write_text(f"# {content_title}\n\nInitial version of the law.\n")
        
        subprocess.run(['git', '-C', str(repo), 'add', filename], capture_output=True)
        subprocess.run(
            ['git', '-C', str(repo), 'commit', '-m', f'Initial: Add {content_title}'],
            capture_output=True
        )
    
    # Add some reform commits
    reforms = [
        ('law_2023_001_constitution.md', 'Reforma: Enmienda a artículos constitucionales'),
        ('law_2022_045_penal_code.md', 'Modificación: Clarificación de penas'),
        ('law_2023_102_labor_law.md', 'Derogación: Eliminación de artículos obsoletos'),
        ('law_2021_003_civil_code.md', 'Ampliación: Nuevas disposiciones civiles'),
    ]
    
    for filename, message in reforms:
        filepath = repo / filename
        current = filepath.read_text()
        filepath.write_text(current + f"\n\n## Reform\n{message}\n")
        
        subprocess.run(['git', '-C', str(repo), 'add', filename], capture_output=True)
        subprocess.run(['git', '-C', str(repo), 'commit', '-m', message], capture_output=True)


def main():
    """Main entry point with CLI argument handling."""
    parser = argparse.ArgumentParser(
        description='Analyze Spanish laws stored in Git repository'
    )
    
    parser.add_argument(
        'repository',
        help='Path to Git repository containing Spanish laws'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for JSON export (optional)',
        default=None
    )
    
    parser.add_argument(
        '-r', '--report',
        action='store_true',
        help='Generate and print analysis report'
    )
    
    parser.add_argument(
        '--create-sample',
        action='store_true',
        help='Create sample repository for testing'
    )
    
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Print only repository statistics'
    )
    
    args = parser.parse_args()
    
    # Handle sample repository creation
    if args.create_sample:
        print(f"Creating sample repository at {args.repository}...")
        create_sample_repo(args.repository)
        print("Sample repository created successfully.")
    
    # Initialize analyzer
    try:
        analyzer = SpanishLawsGitAnalyzer(args.repository)
        analyzer.validate_repo()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Analyze repository
    print("Analyzing repository...", file=sys.stderr)
    analysis = analyzer.analyze_repository()
    analyzer.detect_reforms()
    
    # Output results based on arguments
    if args.stats_only:
        print(json.dumps(analysis['repository_stats'], indent=2))
    elif args.report:
        print(analyzer.generate_report())
    else:
        print(json.dumps({
            'total_laws': analysis['total_laws'],
            'total_commits': analysis['total_commits'],
            'repository_stats': analysis['repository_stats']
        }, indent=2))
    
    # Export to file if requested
    if args.output:
        print(f"Exporting analysis to {args.output}...", file=sys.stderr)
        analyzer.export_json(args.output)
        print(f"Export completed to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()