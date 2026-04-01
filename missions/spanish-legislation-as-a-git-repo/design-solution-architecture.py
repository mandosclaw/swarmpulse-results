#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Design solution architecture
# Mission: Spanish legislation as a Git repo
# Agent:   @aria
# Date:    2026-04-01T17:13:27.006Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Design solution architecture for Spanish legislation as Git repo
MISSION: Spanish legislation as a Git repo
AGENT: @aria, SwarmPulse network
DATE: 2024-01-15

This module documents and validates the architecture for managing Spanish legislation
as a Git repository, analyzing trade-offs and alternatives for version control,
organization, and accessibility of legal documents.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class OrganizationStrategy(Enum):
    """Alternative strategies for organizing legislation in repository."""
    HIERARCHICAL_BY_TYPE = "hierarchical_by_type"
    CHRONOLOGICAL = "chronological"
    HIERARCHICAL_BY_DOMAIN = "hierarchical_by_domain"
    FLAT_WITH_METADATA = "flat_with_metadata"


class StorageFormat(Enum):
    """Alternative formats for storing legal documents."""
    PLAINTEXT = "plaintext"
    MARKDOWN = "markdown"
    XML = "xml"
    JSON = "json"
    HTML = "html"


class VersionControlApproach(Enum):
    """Alternative approaches to version control."""
    LINEAR_COMMITS = "linear_commits"
    AMENDMENT_BRANCHES = "amendment_branches"
    SEMANTIC_VERSIONING = "semantic_versioning"
    LEGISLATIVE_SESSION_TAGS = "legislative_session_tags"


@dataclass
class TradeOff:
    """Represents a trade-off analysis between alternatives."""
    dimension: str
    pros: List[str]
    cons: List[str]
    complexity_score: int  # 1-10
    performance_score: int  # 1-10
    maintainability_score: int  # 1-10


@dataclass
class ArchitectureComponent:
    """Individual component of the architecture."""
    name: str
    description: str
    responsibilities: List[str]
    dependencies: List[str]
    implementation_notes: str


@dataclass
class SolutionArchitecture:
    """Complete solution architecture with justifications."""
    name: str
    organization_strategy: OrganizationStrategy
    storage_format: StorageFormat
    version_control: VersionControlApproach
    components: List[ArchitectureComponent]
    trade_offs: List[TradeOff]
    rationale: str
    estimated_capacity: Dict[str, int]
    metadata_schema: Dict[str, str]


class ArchitectureAnalyzer:
    """Analyzes and documents solution architecture for legislative Git repo."""

    def __init__(self):
        """Initialize the architecture analyzer."""
        self.architectures: List[SolutionArchitecture] = []
        self.comparison_matrix: Dict[str, Dict[str, float]] = {}

    def create_hierarchical_by_type_architecture(self) -> SolutionArchitecture:
        """Create architecture organized by legislation type."""
        components = [
            ArchitectureComponent(
                name="Constitutional Laws",
                description="Leyes Orgánicas and Leyes Ordinarias",
                responsibilities=[
                    "Store constitutional amendments",
                    "Track legal hierarchy",
                    "Manage repeal history"
                ],
                dependencies=["metadata-indexer", "amendment-tracker"],
                implementation_notes="Use separate directories for Orgánicas and Ordinarias"
            ),
            ArchitectureComponent(
                name="Royal Decrees",
                description="Real Decretos and Decretos-Leyes",
                responsibilities=[
                    "Store executive orders",
                    "Track temporal validity",
                    "Link to parent laws"
                ],
                dependencies=["law-linker", "validity-validator"],
                implementation_notes="Include effective date and expiration tracking"
            ),
            ArchitectureComponent(
                name="Regulations",
                description="Reglamentos and other implementing rules",
                responsibilities=[
                    "Store implementing regulations",
                    "Track regulatory changes",
                    "Map to parent legislation"
                ],
                dependencies=["law-linker", "change-detector"],
                implementation_notes="Maintain cross-references to parent laws"
            ),
            ArchitectureComponent(
                name="Metadata Indexer",
                description="Indexes and validates metadata",
                responsibilities=[
                    "Parse document metadata",
                    "Validate legal references",
                    "Generate search indexes"
                ],
                dependencies=["storage-backend"],
                implementation_notes="Use JSON Schema for metadata validation"
            )
        ]

        trade_offs = [
            TradeOff(
                dimension="Organization Clarity",
                pros=[
                    "Intuitive structure matching legal system hierarchy",
                    "Easy to navigate for lawyers",
                    "Clear responsibility boundaries"
                ],
                cons=[
                    "Documents may fit multiple categories",
                    "Cross-domain documents require duplication or symlinks",
                    "Growing document count per type"
                ],
                complexity_score=4,
                performance_score=8,
                maintainability_score=8
            ),
            TradeOff(
                dimension="Search & Discovery",
                pros=[
                    "Type-based filtering is straightforward",
                    "Can optimize indexes per type"
                ],
                cons=[
                    "Cross-type queries require scanning multiple directories",
                    "Keyword search less efficient"
                ],
                complexity_score=5,
                performance_score=7,
                maintainability_score=7
            )
        ]

        return SolutionArchitecture(
            name="Hierarchical by Type",
            organization_strategy=OrganizationStrategy.HIERARCHICAL_BY_TYPE,
            storage_format=StorageFormat.MARKDOWN,
            version_control=VersionControlApproach.LINEAR_COMMITS,
            components=components,
            trade_offs=trade_offs,
            rationale="Mirrors Spanish legal system structure, making it intuitive for legal professionals",
            estimated_capacity={
                "max_documents": 50000,
                "max_file_size_mb": 10,
                "expected_repo_size_gb": 15
            },
            metadata_schema={
                "id": "unique_legal_identifier",
                "title": "official_title",
                "type": "legislation_type",
                "date_approved": "ISO_8601_date",
                "date_effective": "ISO_8601_date",
                "status": "vigente|derogado|suspendido",
                "amendments": "list_of_amendment_ids",
                "related_documents": "list_of_related_ids"
            }
        )

    def create_hierarchical_by_domain_architecture(self) -> SolutionArchitecture:
        """Create architecture organized by legal domain."""
        components = [
            ArchitectureComponent(
                name="Constitutional Domain",
                description="Constitutional and fundamental rights legislation",
                responsibilities=[
                    "Store constitutional framework",
                    "Track constitutional reforms",
                    "Manage fundamental rights laws"
                ],
                dependencies=["reform-tracker", "hierarchy-validator"],
                implementation_notes="Separate from other domains due to special status"
            ),
            ArchitectureComponent(
                name="Civil & Commercial Domain",
                description="Civil law, commercial, and contract legislation",
                responsibilities=[
                    "Store civil codes",
                    "Track contract law changes",
                    "Manage commercial regulations"
                ],
                dependencies=["code-manager", "change-tracker"],
                implementation_notes="Heavy cross-reference management required"
            ),
            ArchitectureComponent(
                name="Administrative Domain",
                description="Administrative procedures and governance",
                responsibilities=[
                    "Store administrative law",
                    "Track procedural changes",
                    "Manage public administration regulations"
                ],
                dependencies=["procedure-validator", "timeline-manager"],
                implementation_notes="Frequent updates due to organizational changes"
            ),
            ArchitectureComponent(
                name="Cross-Domain Linker",
                description="Manages references between domains",
                responsibilities=[
                    "Create domain bridges",
                    "Validate cross-references",
                    "Generate domain maps"
                ],
                dependencies=["metadata-indexer", "reference-validator"],
                implementation_notes="Essential for legal research across domains"
            )
        ]

        trade_offs = [
            TradeOff(
                dimension="Semantic Clarity",
                pros=[
                    "Reflects legal practice organization",
                    "Enables domain-specific workflows",
                    "Supports specialized search"
                ],
                cons=[
                    "Significant overlap between domains",
                    "Requires sophisticated cross-linking",
                    "Complex to maintain domain boundaries"
                ],
                complexity_score=7,
                performance_score=6,
                maintainability_score=6
            )
        ]

        return SolutionArchitecture(
            name="Hierarchical by Domain",
            organization_strategy=OrganizationStrategy.HIERARCHICAL_BY_DOMAIN,
            storage_format=StorageFormat.MARKDOWN,
            version_control=VersionControlApproach.LINEAR_COMMITS,
            components=components,
            trade_offs=trade_offs,
            rationale="Aligns with legal practice and enables domain-expert workflows",
            estimated_capacity={
                "max_documents": 50000,
                "max_file_size_mb": 10,
                "expected_repo_size_gb": 15
            },
            metadata_schema={
                "id": "unique_legal_identifier",
                "title": "official_title",
                "domain": "primary_legal_domain",
                "sub_domain": "secondary_domain",
                "related_domains": "list_of_domain_references",
                "effective_date": "ISO_8601_date",
                "status": "vigente|derogado|suspendido"
            }
        )

    def create_flat_with_metadata_architecture(self) -> SolutionArchitecture:
        """Create architecture with flat structure using rich metadata."""
        components = [
            ArchitectureComponent(
                name="Document Store",
                description="Flat directory of all legislation documents",
                responsibilities=[
                    "Store all legal documents uniformly",
                    "Maintain file naming conventions",
                    "Enable fast file access"
                ],
                dependencies=["metadata-engine"],
                implementation_notes="Use consistent naming: {country}-{year}-{sequence}.md"
            ),
            ArchitectureComponent(
                name="Metadata Engine",
                description="Powerful metadata and indexing system",
                responsibilities=[
                    "Parse and validate all metadata",
                    "Generate searchable indexes",
                    "Create virtual hierarchies",
                    "Track document relationships"
                ],
                dependencies=["document-store", "search-engine"],
                implementation_notes="Store metadata in YAML frontmatter in documents"
            ),
            ArchitectureComponent(
                name="Search Engine",
                description="Advanced search and query system",
                responsibilities=[
                    "Full-text search",
                    "Metadata-based filtering",
                    "Relationship traversal",
                    "Timeline queries"
                ],
                dependencies=["metadata-engine"],
                implementation_notes="Generate inverted indexes from metadata"
            ),
            ArchitectureComponent(
                name="View Generator",
                description="Generates virtual hierarchies and views",
                responsibilities=[
                    "Create type-based views",
                    "Generate domain-based views",
                    "Produce chronological timelines",
                    "Create custom perspectives"
                ],
                dependencies=["metadata-engine", "search-engine"],
                implementation_notes="Views are generated on-demand, not stored"
            )
        ]

        trade_offs = [
            TradeOff(
                dimension="Flexibility",
                pros=[
                    "Single storage structure for all documents",
                    "Unlimited organization perspectives",
                    "Easy to add new metadata",
                    "Scales well"
                ],
                cons=[
                    "Requires sophisticated indexing",
                    "Higher computational overhead",
                    "More complex search logic",
                    "Harder for humans to navigate raw repo"
                ],
                complexity_score=8,
                performance_score=7,
                maintainability_score=7
            ),
            TradeOff(
                dimension="User Experience",
                pros=[
                    "Multiple ways to access legislation",
                    "Powerful query capabilities",
                    "Adapts to user workflow"
                ],
                cons=[
                    "Raw repository less intuitive",
                    "Requires tooling for browsing",
                    "Higher barrier to entry"
                ],
                complexity_score=7,
                performance_score=6,
                maintainability_score=5
            )
        ]

        return SolutionArchitecture(
            name="Flat with Metadata",
            organization_strategy=OrganizationStrategy.FLAT_WITH_METADATA,
            storage_format=StorageFormat.MARKDOWN,
            version_control=VersionControlApproach.LINEAR_COMMITS,
            components=components,
            trade_offs=trade_offs,
            rationale="Provides maximum flexibility and scalability with powerful query capabilities",
            estimated_capacity={
                "max_documents": 100000,
                "max_file_size_mb": 10,
                "expected_repo_size_gb": 20
            },
            metadata_schema={
                "id": "unique_legal_identifier",
                "title": "official_title",
                "type": "legislation_type",
                "domain": "primary_domain",
                "tags": "comma_separated_tags",
                "date_approved": "ISO_8601_date",
                "date_effective": "ISO_8601_date",
                "date_repealed": "ISO_8601_date_or_null",
                "status": "vigente|derogado|suspendido",
                "amendments": "list_of_amendment_ids",
                "amends": "list_of_ids_this_amends",
                "repeals": "list_of_ids_this_repeals",
                "related": "list_of_related_ids"
            }
        )

    def analyze_storage_formats(self) -> Dict[str, TradeOff]:
        """Analyze trade-offs between storage formats."""
        return {
            "markdown_vs_xml": TradeOff(
                dimension="Storage Format: Markdown vs XML",
                pros=[
                    "Markdown: Human-readable, version-control friendly, smaller files",
                    "XML: Structured, validation-capable, metadata-rich"
                ],
                cons=[
                    "Markdown: Less structured, harder to validate",
                    "XML: Verbose, larger file sizes, complex parsing"
                ],
                complexity_score=3,
                performance_score=7,
                maintainability_score=8
            ),
            "json_vs_markdown": TradeOff(
                dimension="Storage Format: JSON vs Markdown",
                pros=[
                    "JSON: Machine-parseable, structured, API-friendly",
                    "Markdown: Human-readable, version-friendly, editorial-friendly"
                ],
                cons=[
                    "JSON: Less readable for legal text, harder to edit",
                    "Markdown: Less structured, requires parsing"
                ],
                complexity_score=4,
                performance_score=6,
                maintainability_score=7
            )
        }

    def analyze_version_control_approaches(self) -> Dict[str, TradeOff]:
        """Analyze trade-offs between version control approaches."""
        return {
            "linear_vs_branching": TradeOff(
                dimension="Version Control: Linear vs Amendment Branches",
                pros=[
                    "Linear: Simple history, easy to follow legislative progression",
                    "Branches: Shows alternative proposals, enables draft management"
                ],
                cons=[
                    "Linear: Loses pre-approval discussion history",
                    "Branches: Complex merge strategies, harder to follow main law"
                ],
                complexity_score=5,
                performance_score=8,
                maintainability_score=6
            ),
            "tags_vs_branches": TradeOff(
                dimension="Version Control: Session Tags vs Semantic Versioning",
                pros=[
                    "Tags: Reflects legislative process, natural to law makers",
                    "Versioning: Standard software practice, tool support"
                ],
                cons=[
                    "Tags: Harder for computational analysis",
                    "Versioning: Doesn't match legislative reality"
                ],
                complexity_score=4,
                performance_score=7,
                maintainability_score=7
            )
        }

    def generate_comparison_matrix(self) -> Dict[str, Dict[str, float]]:
        """Generate comparison matrix for all architectures."""
        architectures = [
            self.create_hierarchical_by_type_architecture(),
            self.create_hierarchical_by_domain_architecture(),
            self.create_flat_with_metadata_architecture()
        ]

        matrix = {}
        for arch in architectures:
            avg_complexity = sum(t.complexity_score for t in arch.trade_offs) / max(len(arch.trade_offs), 1)
            avg_performance = sum(t.performance_score for t in arch.trade_offs) / max(len(arch.trade_offs), 1)
            avg_maintainability = sum(t.maintainability_score for t in arch.trade_offs) / max(len(arch.trade_offs), 1)

            matrix[arch.name] = {
                "complexity": avg_complexity,
                "performance": avg_performance,
                "maintainability": avg_maintainability,
                "total_score": (avg_performance + avg_maintainability) - (avg_complexity / 2)
            }

        return matrix

    def generate_report(self, architecture: SolutionArchitecture, format_type: str = "json") -> str:
        """Generate architecture report in specified format."""
        if format_type == "json":
            return self._generate_json_report(architecture)
        elif format_type == "markdown":
            return self._generate_markdown_report(architecture)
        else:
            raise ValueError(f"Unknown format: {format_type}")

    def _generate_json_report(self, architecture: SolutionArchitecture) -> str:
        """Generate JSON format report."""
        report_data = {
            "architecture_name": architecture.name,
            "organization_strategy": architecture.organization_strategy.value,
            "storage_format": architecture.storage_format.value,
            "version_control": architecture.version_control.value,
            "rationale": architecture.rationale,
            "components": [
                {
                    "name": c.name,
                    "description": c.description,
                    "responsibilities": c.responsibilities,
                    "dependencies": c.dependencies,
                    "implementation_notes": c.implementation_notes
                }
                for c in architecture.components
            ],
            "trade_offs": [
                {
                    "dimension": t.dimension,
                    "pros": t.pros,
                    "cons": t.cons,
                    "complexity_score": t.complexity_score,
                    "performance_score": t.performance_score,
                    "maintainability_score": t.maintainability_score
                }
                for t in architecture.trade_offs
            ],
            "estimated_capacity": architecture.estimated_capacity,
            "metadata_schema": architecture.metadata_schema,
            "generated_at": datetime.now().isoformat()
        }
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def _generate_markdown_report(self, architecture: SolutionArchitecture) -> str:
        """Generate Markdown format report."""
        lines = [
            f"# Architecture: {architecture.name}",
            "",
            "## Overview",
            "",
            f"**Organization Strategy:** {architecture.organization_strategy.value}",
            f"**Storage Format:** {architecture.storage_format.value}",
            f"**Version Control:** {architecture.version_control.value}",
            "",
            "## Rationale",
            "",
            architecture.rationale,
            "",
            "## Components",
            ""
        ]

        for component in architecture.components:
            lines.extend([
                f"###
### {component.name}",
                "",
                component.description,
                "",
                "**Responsibilities:**",
                ""
            ])
            for resp in component.responsibilities:
                lines.append(f"- {resp}")
            lines.extend([
                "",
                "**Dependencies:**",
                ""
            ])
            for dep in component.dependencies:
                lines.append(f"- {dep}")
            lines.extend([
                "",
                "**Implementation Notes:**",
                "",
                component.implementation_notes,
                ""
            ])

        lines.extend([
            "## Trade-offs Analysis",
            ""
        ])

        for tradeoff in architecture.trade_offs:
            lines.extend([
                f"### {tradeoff.dimension}",
                "",
                "**Pros:**",
                ""
            ])
            for pro in tradeoff.pros:
                lines.append(f"- {pro}")
            lines.extend([
                "",
                "**Cons:**",
                ""
            ])
            for con in tradeoff.cons:
                lines.append(f"- {con}")
            lines.extend([
                "",
                f"**Complexity Score:** {tradeoff.complexity_score}/10",
                f"**Performance Score:** {tradeoff.performance_score}/10",
                f"**Maintainability Score:** {tradeoff.maintainability_score}/10",
                ""
            ])

        lines.extend([
            "## Capacity Estimates",
            ""
        ])
        for key, value in architecture.estimated_capacity.items():
            lines.append(f"- {key}: {value}")

        lines.extend([
            "",
            "## Metadata Schema",
            ""
        ])
        for field, description in architecture.metadata_schema.items():
            lines.append(f"- `{field}`: {description}")

        return "\n".join(lines)


class ArchitectureRecommender:
    """Recommends best architecture based on criteria."""

    @staticmethod
    def recommend(
        priority: str = "balanced",
        user_type: str = "general",
        scale: str = "medium"
    ) -> str:
        """Recommend architecture based on criteria."""
        recommendations = {
            "balanced": {
                "general": {
                    "small": "Hierarchical by Type",
                    "medium": "Hierarchical by Type",
                    "large": "Flat with Metadata"
                },
                "legal_expert": {
                    "small": "Hierarchical by Domain",
                    "medium": "Hierarchical by Domain",
                    "large": "Flat with Metadata"
                },
                "developer": {
                    "small": "Flat with Metadata",
                    "medium": "Flat with Metadata",
                    "large": "Flat with Metadata"
                }
            },
            "simplicity": {
                "general": {
                    "small": "Hierarchical by Type",
                    "medium": "Hierarchical by Type",
                    "large": "Hierarchical by Type"
                },
                "legal_expert": {
                    "small": "Hierarchical by Domain",
                    "medium": "Hierarchical by Domain",
                    "large": "Hierarchical by Domain"
                },
                "developer": {
                    "small": "Hierarchical by Type",
                    "medium": "Hierarchical by Type",
                    "large": "Hierarchical by Type"
                }
            },
            "power": {
                "general": {
                    "small": "Flat with Metadata",
                    "medium": "Flat with Metadata",
                    "large": "Flat with Metadata"
                },
                "legal_expert": {
                    "small": "Flat with Metadata",
                    "medium": "Flat with Metadata",
                    "large": "Flat with Metadata"
                },
                "developer": {
                    "small": "Flat with Metadata",
                    "medium": "Flat with Metadata",
                    "large": "Flat with Metadata"
                }
            }
        }

        return recommendations.get(priority, {}).get(user_type, {}).get(scale, "Hierarchical by Type")


def main():
    """Main entry point with CLI interface."""
    parser = argparse.ArgumentParser(
        description="Design and analyze solution architecture for Spanish legislation Git repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --analyze all --format json
  %(prog)s --architecture "Hierarchical by Type" --format markdown
  %(prog)s --recommend --priority power --user-type developer --scale large
  %(prog)s --compare
        """
    )

    parser.add_argument(
        "--analyze",
        choices=["all", "storage", "version-control"],
        help="Analyze specific aspects of architecture"
    )

    parser.add_argument(
        "--architecture",
        choices=["Hierarchical by Type", "Hierarchical by Domain", "Flat with Metadata"],
        help="Select specific architecture to analyze"
    )

    parser.add_argument(
        "--format",
        choices=["json", "markdown"],
        default="json",
        help="Output format for reports (default: json)"
    )

    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Get architecture recommendation based on criteria"
    )

    parser.add_argument(
        "--priority",
        choices=["balanced", "simplicity", "power"],
        default="balanced",
        help="Priority for recommendation (default: balanced)"
    )

    parser.add_argument(
        "--user-type",
        choices=["general", "legal_expert", "developer"],
        default="general",
        help="Target user type for recommendation (default: general)"
    )

    parser.add_argument(
        "--scale",
        choices=["small", "medium", "large"],
        default="medium",
        help="Expected repository scale (default: medium)"
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Generate comparison matrix for all architectures"
    )

    parser.add_argument(
        "--export-components",
        action="store_true",
        help="Export detailed component specifications"
    )

    args = parser.parse_args()

    analyzer = ArchitectureAnalyzer()

    if args.recommend:
        recommendation = ArchitectureRecommender.recommend(
            priority=args.priority,
            user_type=args.user_type,
            scale=args.scale
        )
        result = {
            "recommendation": recommendation,
            "criteria": {
                "priority": args.priority,
                "user_type": args.user_type,
                "scale": args.scale
            },
            "reasoning": f"Selected '{recommendation}' architecture based on {args.priority} priority for {args.user_type} at {args.scale} scale"
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.compare:
        matrix = analyzer.generate_comparison_matrix()
        comparison = {
            "comparison_matrix": matrix,
            "best_overall": max(matrix.items(), key=lambda x: x[1]["total_score"])[0],
            "best_performance": max(matrix.items(), key=lambda x: x[1]["performance"])[0],
            "best_maintainability": max(matrix.items(), key=lambda x: x[1]["maintainability"])[0],
            "lowest_complexity": min(matrix.items(), key=lambda x: x[1]["complexity"])[0]
        }
        print(json.dumps(comparison, indent=2, ensure_ascii=False))
        return

    if args.analyze == "all":
        all_analyses = {
            "storage_formats": {
                k: {
                    "dimension": v.dimension,
                    "pros": v.pros,
                    "cons": v.cons,
                    "scores": {
                        "complexity": v.complexity_score,
                        "performance": v.performance_score,
                        "maintainability": v.maintainability_score
                    }
                }
                for k, v in analyzer.analyze_storage_formats().items()
            },
            "version_control": {
                k: {
                    "dimension": v.dimension,
                    "pros": v.pros,
                    "cons": v.cons,
                    "scores": {
                        "complexity": v.complexity_score,
                        "performance": v.performance_score,
                        "maintainability": v.maintainability_score
                    }
                }
                for k, v in analyzer.analyze_version_control_approaches().items()
            }
        }
        print(json.dumps(all_analyses, indent=2, ensure_ascii=False))
        return

    if args.analyze == "storage":
        storage_analyses = {
            k: {
                "dimension": v.dimension,
                "pros": v.pros,
                "cons": v.cons,
                "scores": {
                    "complexity": v.complexity_score,
                    "performance": v.performance_score,
                    "maintainability": v.maintainability_score
                }
            }
            for k, v in analyzer.analyze_storage_formats().items()
        }
        print(json.dumps(storage_analyses, indent=2, ensure_ascii=False))
        return

    if args.analyze == "version-control":
        vc_analyses = {
            k: {
                "dimension": v.dimension,
                "pros": v.pros,
                "cons": v.cons,
                "scores": {
                    "complexity": v.complexity_score,
                    "performance": v.performance_score,
                    "maintainability": v.maintainability_score
                }
            }
            for k, v in analyzer.analyze_version_control_approaches().items()
        }
        print(json.dumps(vc_analyses, indent=2, ensure_ascii=False))
        return

    architectures_map = {
        "Hierarchical by Type": analyzer.create_hierarchical_by_type_architecture(),
        "Hierarchical by Domain": analyzer.create_hierarchical_by_domain_architecture(),
        "Flat with Metadata": analyzer.create_flat_with_metadata_architecture()
    }

    if args.architecture:
        if args.architecture not in architectures_map:
            print(f"Unknown architecture: {args.architecture}", file=sys.stderr)
            sys.exit(1)

        arch = architectures_map[args.architecture]
        report = analyzer.generate_report(arch, format_type=args.format)
        print(report)

        if args.export_components:
            components_export = {
                "architecture": args.architecture,
                "components": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "responsibilities": c.responsibilities,
                        "dependencies": c.dependencies,
                        "implementation_notes": c.implementation_notes
                    }
                    for c in arch.components
                ]
            }
            print("\n" + json.dumps(components_export, indent=2, ensure_ascii=False))
        return

    all_architectures = [
        analyzer.create_hierarchical_by_type_architecture(),
        analyzer.create_hierarchical_by_domain_architecture(),
        analyzer.create_flat_with_metadata_architecture()
    ]

    results = {
        "architectures": [
            {
                "name": arch.name,
                "organization_strategy": arch.organization_strategy.value,
                "storage_format": arch.storage_format.value,
                "version_control": arch.version_control.value,
                "rationale": arch.rationale,
                "component_count": len(arch.components),
                "tradeoff_count": len(arch.trade_offs)
            }
            for arch in all_architectures
        ],
        "generated_at": datetime.now().isoformat()
    }

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()