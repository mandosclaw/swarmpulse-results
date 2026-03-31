#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design the solution architecture
# Mission: Anatomy of the .claude/ folder
# Agent:   @aria
# Date:    2026-03-31T19:15:22.262Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Design the solution architecture for .claude/ folder anatomy
Mission: Anatomy of the .claude/ folder
Agent: @aria
Date: 2024

This module analyzes and documents the architecture of Claude configuration folders,
their structure, trade-offs, and best practices for organization.
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum


class StorageStrategy(Enum):
    """Storage strategy options for .claude/ folder organization."""
    FLAT = "flat"
    HIERARCHICAL = "hierarchical"
    MODULAR = "modular"


@dataclass
class ComponentMetrics:
    """Metrics for a component in the .claude/ folder."""
    name: str
    path: str
    size_bytes: int
    file_count: int
    last_modified: str
    read_frequency: str
    write_frequency: str
    criticality: str


@dataclass
class ArchitectureDesign:
    """Complete architecture design documentation."""
    strategy: str
    timestamp: str
    components: List[Dict[str, Any]]
    trade_offs: List[Dict[str, str]]
    recommendations: List[str]
    implementation_guide: List[str]


def analyze_claude_folder_structure(
    base_path: str,
    max_depth: int = 3
) -> Dict[str, Any]:
    """
    Analyze the structure and contents of a .claude/ folder.
    
    Args:
        base_path: Path to the .claude folder to analyze
        max_depth: Maximum depth to traverse
    
    Returns:
        Dictionary containing structure analysis
    """
    structure = {
        "path": base_path,
        "exists": os.path.exists(base_path),
        "components": [],
        "total_size": 0,
        "total_files": 0,
    }
    
    if not structure["exists"]:
        return structure
    
    def traverse(path: str, depth: int = 0) -> None:
        if depth > max_depth:
            return
        
        try:
            items = os.listdir(path)
        except PermissionError:
            return
        
        for item in items:
            item_path = os.path.join(path, item)
            
            if os.path.isdir(item_path):
                component = {
                    "type": "directory",
                    "name": item,
                    "path": item_path,
                    "relative_path": os.path.relpath(item_path, base_path),
                    "depth": depth,
                    "contents": []
                }
                
                component_size = 0
                component_files = 0
                
                try:
                    sub_items = os.listdir(item_path)
                    for sub_item in sub_items:
                        sub_path = os.path.join(item_path, sub_item)
                        if os.path.isfile(sub_path):
                            file_size = os.path.getsize(sub_path)
                            component_size += file_size
                            component_files += 1
                            component["contents"].append({
                                "name": sub_item,
                                "size": file_size,
                                "type": "file"
                            })
                except PermissionError:
                    pass
                
                component["size"] = component_size
                component["file_count"] = component_files
                structure["components"].append(component)
                structure["total_size"] += component_size
                structure["total_files"] += component_files
                
                traverse(item_path, depth + 1)
            
            elif os.path.isfile(item_path):
                try:
                    file_size = os.path.getsize(item_path)
                    structure["total_size"] += file_size
                    structure["total_files"] += 1
                    
                    structure["components"].append({
                        "type": "file",
                        "name": item,
                        "path": item_path,
                        "size": file_size,
                        "depth": depth
                    })
                except OSError:
                    pass
    
    traverse(base_path)
    return structure


def generate_flat_strategy() -> ArchitectureDesign:
    """Generate flat storage strategy design."""
    components = [
        {
            "id": "config",
            "name": "config.json",
            "purpose": "Primary configuration file",
            "location": ".claude/config.json",
            "format": "JSON",
            "read_frequency": "high",
            "write_frequency": "low"
        },
        {
            "id": "cache",
            "name": "cache.db",
            "purpose": "Response and computation cache",
            "location": ".claude/cache.db",
            "format": "SQLite",
            "read_frequency": "very_high",
            "write_frequency": "high"
        },
        {
            "id": "sessions",
            "name": "sessions.json",
            "purpose": "Active session tracking",
            "location": ".claude/sessions.json",
            "format": "JSON",
            "read_frequency": "high",
            "write_frequency": "high"
        },
        {
            "id": "logs",
            "name": "activity.log",
            "purpose": "Event and operation logs",
            "location": ".claude/activity.log",
            "format": "Text",
            "read_frequency": "medium",
            "write_frequency": "high"
        }
    ]
    
    trade_offs = [
        {
            "aspect": "Simplicity",
            "advantage": "Easy to understand and implement",
            "disadvantage": "Limited organization for growing systems"
        },
        {
            "aspect": "Maintenance",
            "advantage": "Minimal configuration required",
            "disadvantage": "Can become cluttered with multiple files"
        },
        {
            "aspect": "Performance",
            "advantage": "Direct file access, minimal traversal",
            "disadvantage": "All components compete for disk I/O"
        },
        {
            "aspect": "Scalability",
            "advantage": "Works well for small deployments",
            "disadvantage": "Not suitable for complex multi-tenant scenarios"
        }
    ]
    
    recommendations = [
        "Use for single-user or single-instance deployments",
        "Implement file locking for cache access",
        "Set up log rotation for activity.log",
        "Monitor total folder size periodically",
        "Use atomic writes for configuration changes"
    ]
    
    implementation_guide = [
        "Create .claude/ directory in user home or project root",
        "Initialize config.json with default settings",
        "Set up SQLite cache database with proper indexes",
        "Implement session management with TTL",
        "Configure log rotation with maximum size limits"
    ]
    
    return ArchitectureDesign(
        strategy=StorageStrategy.FLAT.value,
        timestamp=datetime.now().isoformat(),
        components=components,
        trade_offs=trade_offs,
        recommendations=recommendations,
        implementation_guide=implementation_guide
    )


def generate_hierarchical_strategy() -> ArchitectureDesign:
    """Generate hierarchical storage strategy design."""
    components = [
        {
            "id": "root_config",
            "name": "config/",
            "purpose": "Configuration management directory",
            "location": ".claude/config/",
            "subdirs": ["settings.json", "models.json", "plugins.json"],
            "read_frequency": "high",
            "write_frequency": "low"
        },
        {
            "id": "data",
            "name": "data/",
            "purpose": "Data storage and caching",
            "location": ".claude/data/",
            "subdirs": ["cache/", "embeddings/", "artifacts/"],
            "read_frequency": "very_high",
            "write_frequency": "high"
        },
        {
            "id": "logs",
            "name": "logs/",
            "purpose": "Structured logging directory",
            "location": ".claude/logs/",
            "subdirs": ["activity/", "errors/", "performance/"],
            "read_frequency": "medium",
            "write_frequency": "high"
        },
        {
            "id": "state",
            "name": "state/",
            "purpose": "Runtime state management",
            "location": ".claude/state/",
            "subdirs": ["sessions/", "contexts/", "temp/"],
            "read_frequency": "high",
            "write_frequency": "very_high"
        }
    ]
    
    trade_offs = [
        {
            "aspect": "Organization",
            "advantage": "Clear separation of concerns and logical grouping",
            "disadvantage": "Requires understanding the hierarchy structure"
        },
        {
            "aspect": "Maintenance",
            "advantage": "Easier to manage and locate specific components",
            "disadvantage": "More directories to create and maintain"
        },
        {
            "aspect": "Performance",
            "advantage": "Reduced contention on high-frequency components",
            "disadvantage": "Deeper directory traversal for some operations"
        },
        {
            "aspect": "Scalability",
            "advantage": "Better suited for growing systems",
            "disadvantage": "Risk of over-engineering for simple use cases"
        }
    ]
    
    recommendations = [
        "Use for multi-component deployments",
        "Implement separate I/O handlers per major directory",
        "Set up monitoring for each subdirectory",
        "Use consistent naming conventions across levels",
        "Document the hierarchy in a README"
    ]
    
    implementation_guide = [
        "Create main .claude/ structure with config/, data/, logs/, state/",
        "Initialize each subdirectory with appropriate schema files",
        "Set up .gitignore rules for data and logs",
        "Implement recursive permission management",
        "Create initialization script for folder structure creation"
    ]
    
    return ArchitectureDesign(
        strategy=StorageStrategy.HIERARCHICAL.value,
        timestamp=datetime.now().isoformat(),
        components=components,
        trade_offs=trade_offs,
        recommendations=recommendations,
        implementation_guide=implementation_guide
    )


def generate_modular_strategy() -> ArchitectureDesign:
    """Generate modular storage strategy design."""
    components = [
        {
            "id": "core",
            "name": "core/",
            "purpose": "Core system configuration and runtime",
            "location": ".claude/core/",
            "module_type": "essential",
            "dependencies": [],
            "read_frequency": "very_high",
            "write_frequency": "medium"
        },
        {
            "id": "plugins",
            "name": "plugins/",
            "purpose": "Plugin storage and metadata",
            "location": ".claude/plugins/",
            "module_type": "extension",
            "dependencies": ["core"],
            "read_frequency": "medium",
            "write_frequency": "medium"
        },
        {
            "id": "integrations",
            "name": "integrations/",
            "purpose": "Third-party service integrations",
            "location": ".claude/integrations/",
            "module_type": "extension",
            "dependencies": ["core"],
            "read_frequency": "high",
            "write_frequency": "low"
        },
        {
            "id": "extensions",
            "name": "extensions/",
            "purpose": "Custom extensions and features",
            "location": ".claude/extensions/",
            "module_type": "extension",
            "dependencies": ["core", "plugins"],
            "read_frequency": "medium",
            "write_frequency": "low"
        },
        {
            "id": "storage",
            "name": "storage/",
            "purpose": "Persistent storage and archives",
            "location": ".claude/storage/",
            "module_type": "utility",
            "dependencies": ["core"],
            "read_frequency": "low",
            "write_frequency": "high"
        }
    ]
    
    trade_offs = [
        {
            "aspect": "Flexibility",
            "advantage": "Easy to add/remove modules independently",
            "disadvantage": "Requires dependency management"
        },
        {
            "aspect": "Maintenance",
            "advantage": "Each module can be maintained separately",
            "disadvantage": "More complex deployment procedures"
        },
        {
            "aspect": "Performance",
            "advantage": "Load only necessary modules on demand",
            "disadvantage": "Module initialization overhead"
        },
        {
            "aspect": "Complexity",
            "advantage": "Handles complex enterprise scenarios",
            "disadvantage": "Overkill for simple deployments"
        }
    ]
    
    recommendations = [
        "Use for extensible, plugin-based systems",
        "Implement module registry and loader",
        "Define clear module interfaces and contracts",
        "Use semantic versioning for module compatibility",
        "Implement health checks for critical modules"
    ]
    
    implementation_guide = [
        "Design module interface specification",
        "Create module loader with dependency resolution",
        "Implement plugin discovery mechanism",
        "Set up module initialization order",
        "Create module documentation templates",
        "Implement inter-module communication protocol"
    ]
    
    return ArchitectureDesign(
        strategy=StorageStrategy.MODULAR.value,
        timestamp=datetime.now().isoformat(),
        components=components,
        trade_offs=trade_offs,
        recommendations=recommendations,
        implementation_guide=implementation_guide
    )


def create_comparison_report(
    designs: Dict[str, ArchitectureDesign]
) -> Dict[str, Any]:
    """
    Create a comprehensive comparison report across all strategies.
    
    Args:
        designs: Dictionary mapping strategy names to designs
    
    Returns:
        Comparison report dictionary
    """
    report = {
        "title": "Claude Folder Architecture Comparison",
        "timestamp": datetime.now().isoformat(),
        "strategies_analyzed": len(designs),
        "comparison_criteria": [
            "Simplicity",
            "Scalability",
            "Maintenance Overhead",
            "Performance",
            "Enterprise Readiness",
            "Learning Curve"
        ],
        "strategy_details": {}
    }
    
    for strategy_name, design in designs.items():
        score_map = {
            "flat": {"simplicity": 10, "scalability": 3, "maintenance": 8, "performance": 8, "enterprise": 3, "learning": 10},
            "hierarchical": {"simplicity": 7, "scalability": 8, "maintenance": 7, "performance": 7, "enterprise": 7, "learning": 7},
            "modular": {"simplicity": 4, "scalability": 10, "maintenance": 6, "performance": 6, "enterprise": 10, "learning": 3}
        }
        
        scores = score_map.get(design.strategy, {})
        
        report["strategy_details"][strategy_name] = {
            "design": asdict(design),
            "scores": scores,
            "component_count": len(design.components),
            "trade_off_count": len(design.trade_offs)
        }
    
    return report


def output_results(
    report: Dict[str, Any],
    output_format: str = "json",
    output_file: Optional[str] = None
) -> None:
    """
    Output the architecture analysis report.
    
    Args:
        report: The report dictionary to output
        output_format: Format for output (json or text)
        output_file: Optional file to write to
    """
    if output_format == "json":
        output_text = json.dumps(report, indent=2)
    else:
        output_text = format_text_report(report)
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output_text)
        print(f"Report written to {output_file}")
    else:
        print(output_text)


def format_text_report(report: Dict[str, Any]) -> str:
    """
    Format report as human-readable text.
    
    Args:
        report: The report dictionary
    
    Returns:
        Formatted text report
    """
    lines = []
    lines.append("=" * 80)
    lines.append(report["title"])
    lines.append("=" * 80)
    lines.append(f"Generated: {report['timestamp']}")
    lines.append(f"Strategies Analyzed: {report['strategies_analyzed']}")
    lines.append("")
    
    for strategy_name, details in report["strategy_details"].items():
        design = details["design"]
        lines.append("-" * 80)
        lines.append(f"STRATEGY: {strategy_name.upper()}")
        lines.append("-" * 80)
        
        lines.append(f"\nComponents ({len(design['components'])}):")
        for component in design["components"]:
            lines.append(f"  - {component.get('name', component.get('id'))}: {component.get('purpose', 'N/A')}")
        
        lines.append(f"\nScores:")
        for criterion, score in details["scores"].items():
            lines.append(f"  {criterion.capitalize()}: {score}/10")
        
        lines.append(f"\nKey Trade-offs:")
        for tradeoff in design["trade_offs"][:2]:
            lines.append(f"  - {tradeoff['aspect']}: +{tradeoff['advantage']}, -{tradeoff['disadvantage']}")
        
        lines.append(f"\nTop Recommendations:")
        for rec in design["recommendations"][:3]:
            lines.append(f"  • {rec}")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    """Main entry point for the architecture analysis tool."""
    parser = argparse.ArgumentParser(
        description="Design and analyze .claude/ folder architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --analyze /home/user/.claude --format json
  %(prog)s --design all --output architecture.json
  %(prog)s --design hierarchical --format text
  %(prog)s --compare --output report.json
        """
    )
    
    parser.add_argument(
        "--analyze",
        type=str,
        help="Analyze existing .claude folder structure at path"
    )
    
    parser.add_argument(
        "--design",
        choices=["flat", "hierarchical", "modular", "all"],
        default="all",
        help="Generate architecture design(s) (default: all)"
    )
    
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Generate comparison report across all strategies"
    )
    
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format (default: json)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum depth for folder analysis (default: 3)"
    )
    
    args = parser.parse_args()
    
    # Handle analysis mode
    if args.analyze:
        if not os.path.exists(args.analyze):
            print(f"Error: Path {args.analyze} does not exist", file=sys.stderr)
            sys.exit(1)
        
        structure = analyze_claude_folder_structure(args.analyze, args.max_depth)
        output_results(structure, args.format, args.output)
        return
    
    # Generate designs
    designs = {}
    
    if args.design in ("flat", "all"):
        designs["flat"] = generate_flat_strategy()
    
    if args.design in ("hierarchical", "all"):
        designs["hierarchical"] = generate_hierarchical_strategy()
    
    if args.design in ("modular", "all"):
        designs["modular"] = generate_modular_strategy()
    
    # Handle comparison mode
    if args.compare:
        report = create_comparison_report(designs)
        output_results(report, args.format, args.output)
    else:
        # Output individual designs
        if len(designs) == 1:
            design = list(designs.values())[0]
            output_results(asdict(design), args.format, args.output)
        else:
            combined = {
                "timestamp": datetime.now().isoformat(),
                "designs": {name: asdict(design) for name, design in designs.items()}
            }
            output_results(combined, args.format, args.output)


if __name__ == "__main__":
    # Demo execution with sample data
    print("Claude Folder Architecture Analysis Tool")
    print("=" * 80)
    
    # Generate all architecture designs
    designs = {
        "flat": generate_flat_strategy(),
        "hierarchical": generate_hierarchical_strategy(),
        "modular": generate_modular_strategy()
    }
    
    # Create comparison report
    report = create_comparison_report(designs)
    
    # Output as JSON
    print("\nGenerated Comparison Report (JSON format):")
    print(json.dumps(report, indent=2))
    
    # Format and output as text
    print("\n\nFormatted Text Report:")
    print(format_text_report(report))
    
    # Demo: Analyze a sample structure if it exists
    sample_path = os.path.expanduser("~/.claude")
    if os.path.exists(sample_path):
        print(f"\n\nAnalysis of existing {sample_path}:")
        structure = analyze_claude_folder_structure(sample_path)
        print(json.dumps(structure, indent=2))
    else:
        print(f"\n\nNote: {sample_path} does not exist (this is expected in demo)")