#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build migration priority matrix
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-31T19:13:38.472Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build migration priority matrix
MISSION: Quantum-Safe Cryptography Migration
AGENT: @aria
DATE: 2025-01-16

A quantum-safe cryptography migration priority matrix builder that inventories
cryptographic systems, assesses quantum vulnerability risk, and generates
prioritized migration recommendations for ML-KEM adoption.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple, Optional
import re


class CryptoAlgorithm(Enum):
    """Known cryptographic algorithms and their quantum safety."""
    RSA = ("RSA", False, 2048)
    ECC = ("ECC", False, 256)
    AES = ("AES", True, 256)
    SHA256 = ("SHA-256", True, 256)
    SHA512 = ("SHA-512", True, 512)
    ML_KEM = ("ML-KEM", True, 1024)
    DH = ("Diffie-Hellman", False, 2048)
    ECDH = ("ECDH", False, 256)


class RiskLevel(Enum):
    """Risk assessment levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CryptoComponent:
    """Represents a cryptographic component in the inventory."""
    identifier: str
    name: str
    algorithm: str
    key_length: int
    deployment_count: int
    last_updated: str
    quantum_safe: bool
    usage_context: str
    dependencies: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskAssessment:
    """Risk assessment for a cryptographic component."""
    component_id: str
    risk_level: str
    quantum_vulnerability_score: float
    migration_urgency: float
    affected_systems: int
    potential_impact: str
    dependencies_blocking: List[str]
    estimated_effort: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MigrationPriority:
    """Migration priority for a component."""
    rank: int
    component_id: str
    component_name: str
    current_algorithm: str
    target_algorithm: str
    risk_level: str
    migration_score: float
    dependencies_to_migrate: int
    estimated_months: float
    business_impact: str
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


class QuantumVulnerabilityScorer:
    """Scores cryptographic components for quantum vulnerability."""

    def __init__(self):
        self.algorithm_base_scores = {
            "RSA": 0.95,
            "ECC": 0.85,
            "DH": 0.90,
            "ECDH": 0.80,
            "AES": 0.10,
            "SHA-256": 0.15,
            "SHA-512": 0.10,
            "ML-KEM": 0.05,
        }
        self.key_length_multiplier = {
            1024: 0.7,
            2048: 0.8,
            3072: 0.85,
            4096: 0.9,
            256: 0.6,
            384: 0.7,
            521: 0.75,
        }

    def calculate_vulnerability_score(self, component: CryptoComponent) -> float:
        """Calculate vulnerability score (0.0 to 1.0)."""
        base_score = self.algorithm_base_scores.get(component.algorithm, 0.5)

        key_mult = self.key_length_multiplier.get(
            component.key_length, 0.5
        )

        age_penalty = self._calculate_age_penalty(component.last_updated)

        deployment_multiplier = min(1.0, component.deployment_count / 1000.0)

        score = (
            base_score * key_mult * (1.0 + age_penalty) * deployment_multiplier
        )

        return min(1.0, max(0.0, score))

    def _calculate_age_penalty(self, last_updated: str) -> float:
        """Penalty for outdated crypto components."""
        try:
            update_date = datetime.fromisoformat(last_updated)
            days_old = (datetime.now() - update_date).days
            penalty = min(0.5, days_old / 3650.0)
            return penalty
        except (ValueError, TypeError):
            return 0.1

    def assess_component(self, component: CryptoComponent) -> RiskAssessment:
        """Perform full risk assessment on a component."""
        vulnerability_score = self.calculate_vulnerability_score(component)

        if vulnerability_score >= 0.8:
            risk_level = RiskLevel.CRITICAL.value
        elif vulnerability_score >= 0.6:
            risk_level = RiskLevel.HIGH.value
        elif vulnerability_score >= 0.4:
            risk_level = RiskLevel.MEDIUM.value
        else:
            risk_level = RiskLevel.LOW.value

        migration_urgency = vulnerability_score * 0.7 + (len(component.dependencies) / 10.0) * 0.3

        affected_systems = component.deployment_count
        potential_impact = self._determine_impact(
            vulnerability_score, affected_systems
        )

        blocking_deps = [d for d in component.dependencies if d.startswith("RSA") or d.startswith("ECC")]

        return RiskAssessment(
            component_id=component.identifier,
            risk_level=risk_level,
            quantum_vulnerability_score=round(vulnerability_score, 3),
            migration_urgency=round(min(1.0, migration_urgency), 3),
            affected_systems=affected_systems,
            potential_impact=potential_impact,
            dependencies_blocking=blocking_deps,
            estimated_effort=self._estimate_effort(
                component, vulnerability_score
            ),
        )

    def _determine_impact(self, score: float, count: int) -> str:
        """Determine potential business impact."""
        if score >= 0.8 and count >= 100:
            return "SEVERE - Critical infrastructure affected"
        elif score >= 0.8:
            return "HIGH - Sensitive operations affected"
        elif score >= 0.6 and count >= 100:
            return "MODERATE - Widespread deployment"
        elif score >= 0.6:
            return "MODERATE - Limited deployment"
        else:
            return "LOW - Isolated exposure"

    def _estimate_effort(self, component: CryptoComponent, score: float) -> str:
        """Estimate migration effort."""
        base_effort = len(component.dependencies) * 0.5 + component.deployment_count / 100.0
        urgency_factor = score * 2.0

        if base_effort >= 20:
            return "MAJOR (6-12 months)"
        elif base_effort >= 10:
            return "SIGNIFICANT (3-6 months)"
        elif base_effort >= 5:
            return "MODERATE (1-3 months)"
        else:
            return "MINOR (< 1 month)"


class MigrationPriorityMatrix:
    """Builds and manages the migration priority matrix."""

    def __init__(self):
        self.scorer = QuantumVulnerabilityScorer()
        self.components: List[CryptoComponent] = []
        self.assessments: Dict[str, RiskAssessment] = {}
        self.priorities: List[MigrationPriority] = []

    def add_component(self, component: CryptoComponent) -> None:
        """Add a cryptographic component to inventory."""
        self.components.append(component)

    def assess_all_components(self) -> None:
        """Assess all components in inventory."""
        self.assessments = {}
        for component in self.components:
            assessment = self.scorer.assess_component(component)
            self.assessments[component.identifier] = assessment

    def build_priority_matrix(self) -> List[MigrationPriority]:
        """Build migration priority matrix from assessments."""
        if not self.assessments:
            self.assess_all_components()

        priorities = []

        for component in self.components:
            assessment = self.assessments[component.identifier]

            if component.quantum_safe:
                priority_score = 0.0
            else:
                vuln_weight = assessment.quantum_vulnerability_score * 0.4
                urgency_weight = assessment.migration_urgency * 0.3
                impact_weight = (1.0 if assessment.risk_level in [RiskLevel.CRITICAL.value, RiskLevel.HIGH.value] else 0.0) * 0.2
                deps_weight = min(1.0, len(assessment.dependencies_blocking) / 5.0) * 0.1

                priority_score = vuln_weight + urgency_weight + impact_weight + deps_weight

            target_algo = self._select_target_algorithm(component)

            estimated_months = self._calculate_migration_time(component, assessment)

            priority = MigrationPriority(
                rank=0,
                component_id=component.identifier,
                component_name=component.name,
                current_algorithm=component.algorithm,
                target_algorithm=target_algo,
                risk_level=assessment.risk_level,
                migration_score=round(priority_score, 3),
                dependencies_to_migrate=len(assessment.dependencies_blocking),
                estimated_months=round(estimated_months, 1),
                business_impact=assessment.potential_impact,
                recommendation=self._generate_recommendation(
                    component, assessment, priority_score
                ),
            )

            priorities.append(priority)

        priorities.sort(key=lambda p: p.migration_score, reverse=True)
        for rank, priority in enumerate(priorities, 1):
            priority.rank = rank

        self.priorities = priorities
        return priorities

    def _select_target_algorithm(self, component: CryptoComponent) -> str:
        """Select appropriate post-quantum algorithm."""
        if component.algorithm in ["RSA", "DH"]:
            return "ML-KEM"
        elif component.algorithm in ["ECC", "ECDH"]:
            return "ML-KEM"
        elif component.algorithm in ["AES", "SHA-256", "SHA-512"]:
            return component.algorithm
        else:
            return "ML-KEM"

    def _calculate_migration_time(self, component: CryptoComponent, assessment: RiskAssessment) -> float:
        """Calculate estimated migration time in months."""
        base_time = 1.0

        deployment_factor = min(3.0, component.deployment_count / 100.0)

        dependency_factor = min(2.0, len(component.dependencies) / 3.0)

        effort_mapping = {
            "MAJOR (6-12 months)": 9.0,
            "SIGNIFICANT (3-6 months)": 4.5,
            "MODERATE (1-3 months)": 2.0,
            "MINOR (< 1 month)": 0.5,
        }
        effort_time = effort_mapping.get(assessment.estimated_effort, 2.0)

        total = base_time + deployment_factor + dependency_factor + effort_time
        return total

    def _generate_recommendation(
        self, component: CryptoComponent, assessment: RiskAssessment, score: float
    ) -> str:
        """Generate migration recommendation."""
        if score >= 0.75:
            return f"IMMEDIATE: Migrate {component.algorithm} to {self._select_target_algorithm(component)} - {assessment.potential_impact}"
        elif score >= 0.50:
            return f"HIGH PRIORITY: Plan migration of {component.algorithm} within next quarter"
        elif score >= 0.25:
            return f"PLANNED: Schedule {component.algorithm} migration for Q3/Q4"
        else:
            return f"LOW PRIORITY: Monitor {component.algorithm}, no immediate action required"

    def get_executive_summary(self) -> Dict:
        """Generate executive summary of migration matrix."""
        if not self.priorities:
            self.build_priority_matrix()

        critical_count = sum(1 for p in self.priorities if p.risk_level == RiskLevel.CRITICAL.value)
        high_count = sum(1 for p in self.priorities if p.risk_level == RiskLevel.HIGH.value)
        medium_count = sum(1 for p in self.priorities if p.risk_level == RiskLevel.MEDIUM.value)
        low_count = sum(1 for p in self.priorities if p.risk_level == RiskLevel.LOW.value)

        total_effort = sum(p.estimated_months for p in self.priorities if p.migration_score > 0.3)

        top_3 = self.priorities[:3]

        return {
            "timestamp": datetime.now().isoformat(),
            "total_components": len(self.components),
            "quantum_safe_components": sum(1 for c in self.components if c.quantum_safe),
            "vulnerable_components": len(self.components) - sum(1 for c in self.components if c.quantum_safe),
            "risk_distribution": {
                "CRITICAL": critical_count,
                "HIGH": high_count,
                "MEDIUM": medium_count,
                "LOW": low_count,
            },
            "total_estimated_effort_months": round(total_effort, 1),
            "top_priority_migrations": [asdict(p) for p in top_3],
            "recommendation": self._generate_strategy_recommendation(critical_count, high_count),
        }

    def _generate_strategy_recommendation(self, critical: int, high: int) -> str:
        """Generate overall migration strategy recommendation."""
        if critical > 0:
            return "CRITICAL: Begin immediate migration of critical components. Establish dedicated quantum-safe migration task force."
        elif high >= 3:
            return "HIGH RISK: Accelerate migration planning. Allocate resources for concurrent migrations across multiple components."
        elif high > 0:
            return "MODERATE RISK: Develop detailed migration roadmap for high-risk components. Begin ML-KEM adapter integration."
        else:
            return "LOW RISK: Standard migration schedule acceptable. Continue monitoring for emerging threats."


def generate_sample_inventory() -> List[CryptoComponent]:
    """Generate sample cryptographic component inventory."""
    components = [
        CryptoComponent(
            identifier="RSA-GATEWAY-001",
            name="API Gateway TLS",
            algorithm="RSA",
            key_length=2048,
            deployment_count=250,
            last_updated="2020-01-15",
            quantum_safe=False,
            usage_context="TLS 1.2/1.3 certificate signing",
            dependencies=["ECC-LOAD-BALANCER-001", "CERT-DB-001"],
        ),
        CryptoComponent(
            identifier="ECC-LOAD-BALANCER-001",
            name="Load Balancer ECDH",
            algorithm="ECC",
            key_length=256,
            deployment_count=180,
            last_updated="2019-06-20",
            quantum_safe=False,
            usage_context="Key exchange for TLS handshake",
            dependencies=["RSA-GATEWAY-001"],
        ),
        CryptoComponent(
            identifier="AES-VAULT-001",
            name="Database Encryption",
            algorithm="AES",
            key_length=256,
            deployment_count=50,
            last_updated="2023-01-10",
            quantum_safe=True,
            usage_context="At-rest encryption for sensitive data",
            dependencies=[],
        ),
        CryptoComponent(
            identifier="RSA-PKI-001",
            name="Certificate Authority",
            algorithm="RSA",
            key_length=4096,
            deployment_count=5,
            last_updated="2018-03-22",
            quantum_safe=False,
            usage_context="Root CA for internal PKI",
            dependencies=["CERT-DB-001", "BACKUP-VAULT-001"],
        ),
        CryptoComponent(
            identifier="DH-VPN-001",
            name="VPN Key Exchange",
            algorithm="DH",
            key_length=2048,
            deployment_count=120,
            last_updated="2021-09-05",
            quantum_safe=False,
            usage_context="IPSec IKE phase 1 key agreement",
            dependencies=["AES-VAULT-001"],
        ),
        CryptoComponent(
            identifier="SHA256-LOGGING-001",
            name="Event Log Hashing",
            algorithm="SHA-256",
            key_length=256,
            deployment_count=500,
            last_updated="2023-06-15",
            quantum_safe=True,
            usage_context="Audit trail integrity verification",
            dependencies=[],
        ),
        CryptoComponent(
            identifier="ECDH-IOT-001",
            name="IoT Device Communication",
            algorithm="ECDH",
            key_length=256,
            deployment_count=5000,
            last_updated="2022-03-10",
            quantum_safe=False,
            usage_context="Lightweight key exchange for IoT",
            dependencies=["AES-VAULT-001"],
        ),
        CryptoComponent(
            identifier="RSA-ARCHIVE-001",
            name="Legacy Archive Signing",
            algorithm="RSA",
            key_length=2048,
            deployment_count=10,
            last_updated="2017-11-30",
            quantum_safe=False,
            usage_context="Digital signature for compliance",
            dependencies=["CERT-DB-001"],
        ),
        CryptoComponent(
            identifier="AES-API-001",
            name="API Payload Encryption",
            algorithm="AES",
            key_length=256,
            deployment_count=150,
            last_updated="2023-10-20",
            quantum_safe=True,
            usage_context="Client-server communication encryption",
            dependencies=[],
        ),
        CryptoComponent(
            identifier="ML-KEM-PROTO-001",
            name="Prototype ML-KEM",
            algorithm="ML-KEM",
            key_length=1024,
            deployment_count=2,
            last_updated="2024-01-10",
            quantum_safe=True,
            usage_context="Post-quantum KEM prototype deployment",
            dependencies=[],
        ),
    ]
    return components


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quantum-Safe Cryptography Migration Priority Matrix Builder"
    )
    parser.add_argument(
        "--inventory",
        type=str,
        default=None,
        help="Path to inventory JSON file (uses sample if not provided)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="migration_matrix.json",
        help="Output file for migration priority matrix",
    )
    parser.add_argument(
        "--format",
        choices=["json", "human"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Output only executive summary",
    )
    parser.add_argument(
        "--risk-filter",
        choices=["ALL", "CRITICAL", "HIGH", "MEDIUM"],
        default="ALL",
        help="Filter results by risk level",
    )

    args = parser.parse_args()

    if args.inventory:
        try:
            with open(args.inventory, 'r') as f:
                inventory_data = json.load(f)
                components = [
                    CryptoComponent(**comp) for comp in inventory_data
                ]
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading inventory: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        components = generate_sample_inventory()

    matrix = MigrationPriorityMatrix()
    for component in components:
        matrix.add_component(component)

    matrix.assess_all_components()
    priorities = matrix.build_priority_matrix()

    if args.risk_filter != "ALL":
        priorities = [p for p in priorities if p.risk_level == args.risk_filter]
        priorities.sort(key=lambda p: p.migration_score, reverse=True)
        for rank, priority in enumerate(priorities, 1):
            priority.rank = rank

    summary = matrix.get_executive_summary()

    if args.format == "human":
        print("\n" + "=" * 80)
        print("QUANTUM-SAFE CRYPTOGRAPHY MIGRATION PRIORITY MATRIX")
        print("=" * 80)
        print(f"\nGenerated: {summary['timestamp']}")
        print(f"\nInventory Statistics:")
        print(f"  Total Components: {summary['total_components']}")
        print(f"  Quantum-Safe: {summary['quantum_safe_components']}")
        print(f"  Vulnerable: {summary['vulnerable_components']}")
        print(f"\nRisk Distribution:")
        for risk, count in summary['risk_distribution'].items():
            print(f"  {risk}: {count}")
        print(f"\nTotal Estimated Migration Effort: {summary['total_estimated_effort_months']} months")
        print(f"\nStrategy Recommendation: {summary['recommendation']}")

        print("\n" + "-" * 80)
        print("MIGRATION PRIORITY MATRIX")
        print("-" * 80)
        for priority in priorities:
            print(f"\n[{priority.rank}] {priority.component_name} ({priority.component_id})")
            print(f"    Current Algorithm: {priority.current_algorithm}")
            print(f"    Target Algorithm: {priority.target_algorithm}")
            print(f"    Risk Level: {priority.risk_level}")
            print(f"    Migration Score: {priority.migration_score}")
            print(f"    Blocking Dependencies: {priority.dependencies_to_migrate}")
            print(f"    Estimated Effort: {priority.estimated_months} months")
            print(f"    Business Impact: {priority.business_impact}")
            print(f"    Recommendation: {priority.recommendation}")
        print("\n" + "=" * 80 + "\n")

    output_data = {
        "summary": summary,
        "priority_matrix": [asdict(p) for p in priorities],
        "assessments": {
            comp_id: asdict(assessment)
            for comp_id, assessment in matrix.assessments.items()
        },
    }

    with open(args.output, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Migration matrix written to {args.output}")


if __name__ == "__main__":
    main()