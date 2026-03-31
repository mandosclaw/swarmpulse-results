#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build migration priority matrix
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-31T19:07:26.722Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Migration Priority Matrix for Quantum-Safe Cryptography
Mission: Quantum-Safe Cryptography Migration
Agent: @aria
Date: 2025-01-20

Build a comprehensive priority matrix for migrating cryptographic systems
from classical (RSA/ECC) to quantum-safe algorithms (ML-KEM/ML-DSA).
Includes inventory scanning, risk assessment, and prioritization scoring.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Tuple
import random
import hashlib


class CryptoAlgorithm(Enum):
    """Supported cryptographic algorithms."""
    RSA_2048 = "RSA-2048"
    RSA_4096 = "RSA-4096"
    ECC_P256 = "ECC-P256"
    ECC_P384 = "ECC-P384"
    ECC_P521 = "ECC-P521"
    ML_KEM_512 = "ML-KEM-512"
    ML_KEM_768 = "ML_KEM-768"
    ML_KEM_1024 = "ML-KEM-1024"
    ML_DSA_44 = "ML-DSA-44"
    ML_DSA_65 = "ML-DSA-65"
    ML_DSA_87 = "ML-DSA-87"


class QuantumVulnerability(Enum):
    """Quantum vulnerability levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SAFE = "SAFE"


class MigrationPhase(Enum):
    """Migration phases."""
    PHASE_1_CRITICAL = "Phase 1: Critical Assets"
    PHASE_2_HIGH = "Phase 2: High-Risk Assets"
    PHASE_3_MEDIUM = "Phase 3: Medium-Risk Assets"
    PHASE_4_LOW = "Phase 4: Low-Risk Assets"
    PHASE_5_MAINTENANCE = "Phase 5: Maintenance Systems"


@dataclass
class CryptoSystem:
    """Represents a cryptographic system in inventory."""
    system_id: str
    name: str
    algorithm: CryptoAlgorithm
    key_size: int
    installed_systems: int
    data_sensitivity: str
    data_lifetime_years: int
    last_updated: str
    criticality_score: float
    exposure_level: str
    dependencies: List[str]
    compliance_requirements: List[str]


@dataclass
class RiskAssessment:
    """Risk assessment for a crypto system."""
    system_id: str
    quantum_vulnerability: QuantumVulnerability
    harvest_now_threat: float
    future_threat_timeline: int
    data_at_risk_count: int
    compliance_gap_score: float
    migration_complexity: float
    estimated_migration_days: int
    priority_score: float
    recommended_phase: MigrationPhase


class QuantumSafeAlgorithms:
    """Mapping of classical to quantum-safe algorithms."""
    
    CLASSICAL_TO_QUANTUM_SAFE = {
        CryptoAlgorithm.RSA_2048: CryptoAlgorithm.ML_KEM_512,
        CryptoAlgorithm.RSA_4096: CryptoAlgorithm.ML_KEM_1024,
        CryptoAlgorithm.ECC_P256: CryptoAlgorithm.ML_KEM_512,
        CryptoAlgorithm.ECC_P384: CryptoAlgorithm.ML_KEM_768,
        CryptoAlgorithm.ECC_P521: CryptoAlgorithm.ML_KEM_1024,
    }
    
    QUANTUM_SAFE_ALGORITHMS = {
        CryptoAlgorithm.ML_KEM_512,
        CryptoAlgorithm.ML_KEM_768,
        CryptoAlgorithm.ML_KEM_1024,
        CryptoAlgorithm.ML_DSA_44,
        CryptoAlgorithm.ML_DSA_65,
        CryptoAlgorithm.ML_DSA_87,
    }
    
    @classmethod
    def is_quantum_safe(cls, algorithm: CryptoAlgorithm) -> bool:
        """Check if algorithm is quantum-safe."""
        return algorithm in cls.QUANTUM_SAFE_ALGORITHMS
    
    @classmethod
    def get_replacement(cls, algorithm: CryptoAlgorithm) -> CryptoAlgorithm:
        """Get quantum-safe replacement for classical algorithm."""
        return cls.CLASSICAL_TO_QUANTUM_SAFE.get(
            algorithm,
            CryptoAlgorithm.ML_KEM_768
        )


class RiskCalculator:
    """Calculate quantum threat and migration risk for crypto systems."""
    
    # Quantum threat timeline estimates (years from now)
    HARVEST_NOW_THREAT_YEARS = 0  # Current threat for harvest-now attacks
    CRYPTOGRAPHICALLY_RELEVANT_QUANTUM_COMPUTER_YEARS = 15
    
    @staticmethod
    def calculate_quantum_vulnerability(
        algorithm: CryptoAlgorithm,
        key_size: int,
        data_lifetime: int
    ) -> QuantumVulnerability:
        """Determine quantum vulnerability level."""
        if QuantumSafeAlgorithms.is_quantum_safe(algorithm):
            return QuantumVulnerability.SAFE
        
        # RSA/ECC vulnerability scoring
        if algorithm in [CryptoAlgorithm.RSA_2048, CryptoAlgorithm.ECC_P256]:
            if data_lifetime > 10:
                return QuantumVulnerability.CRITICAL
            elif data_lifetime > 5:
                return QuantumVulnerability.HIGH
            else:
                return QuantumVulnerability.MEDIUM
        
        elif algorithm in [CryptoAlgorithm.RSA_4096, CryptoAlgorithm.ECC_P384]:
            if data_lifetime > 15:
                return QuantumVulnerability.HIGH
            elif data_lifetime > 7:
                return QuantumVulnerability.MEDIUM
            else:
                return QuantumVulnerability.LOW
        
        elif algorithm == CryptoAlgorithm.ECC_P521:
            if data_lifetime > 20:
                return QuantumVulnerability.MEDIUM
            else:
                return QuantumVulnerability.LOW
        
        return QuantumVulnerability.LOW
    
    @staticmethod
    def calculate_harvest_now_threat(
        data_sensitivity: str,
        installed_systems: int,
        exposure_level: str
    ) -> float:
        """
        Calculate harvest-now threat score (0.0-1.0).
        Harvest-now attacks store encrypted data today for decryption with quantum computers.
        """
        sensitivity_weights = {
            "TOP_SECRET": 1.0,
            "SECRET": 0.8,
            "CONFIDENTIAL": 0.6,
            "INTERNAL": 0.3,
            "PUBLIC": 0.0
        }
        
        exposure_weights = {
            "INTERNET_FACING": 1.0,
            "NETWORK_ACCESSIBLE": 0.7,
            "INTERNAL_ONLY": 0.3,
            "ISOLATED": 0.1
        }
        
        sensitivity_score = sensitivity_weights.get(data_sensitivity, 0.5)
        exposure_score = exposure_weights.get(exposure_level, 0.5)
        
        # Scale with number of systems
        scale_factor = min(installed_systems / 1000.0, 1.0)
        
        return min(1.0, (sensitivity_score * 0.5 + exposure_score * 0.5) * (0.5 + scale_factor))
    
    @staticmethod
    def calculate_compliance_gap(
        algorithm: CryptoAlgorithm,
        compliance_requirements: List[str]
    ) -> float:
        """Calculate compliance gap score for not having quantum-safe crypto."""
        if not compliance_requirements:
            return 0.0
        
        quantum_safe_compliant = [
            "NIST_PQC",
            "BSI_CRYPTO",
            "ETSI_PQC",
            "ISO_20748"
        ]
        
        relevant_requirements = [
            req for req in compliance_requirements
            if any(q in req for q in quantum_safe_compliant)
        ]
        
        if not relevant_requirements:
            return 0.2  # General compliance consideration
        
        # Score based on how many quantum-relevant requirements are not met
        gap = len(relevant_requirements) / len(compliance_requirements)
        return min(1.0, gap * 1.5)
    
    @staticmethod
    def calculate_migration_complexity(
        dependencies: List[str],
        criticality: float,
        installed_systems: int
    ) -> float:
        """Calculate migration complexity score."""
        dependency_factor = min(len(dependencies) / 10.0, 1.0)
        criticality_factor = criticality / 10.0
        scale_factor = min(installed_systems / 1000.0, 1.0)
        
        return min(1.0, (dependency_factor * 0.3 + criticality_factor * 0.4 + scale_factor * 0.3))
    
    @staticmethod
    def calculate_estimated_migration_days(
        complexity: float,
        installed_systems: int,
        dependencies_count: int
    ) -> int:
        """Estimate days needed for migration."""
        base_days = 30
        complexity_days = int(complexity * 60)
        scale_days = int((installed_systems / 100) * 5)
        dependency_days = dependencies_count * 3
        
        return base_days + complexity_days + scale_days + dependency_days
    
    @staticmethod
    def calculate_priority_score(
        quantum_vulnerability: QuantumVulnerability,
        harvest_now_threat: float,
        compliance_gap: float,
        migration_complexity: float,
        criticality: float,
        installed_systems: int
    ) -> float:
        """
        Calculate overall migration priority score (0-100).
        Higher score = higher priority for migration.
        """
        vulnerability_weights = {
            QuantumVulnerability.CRITICAL: 100,
            QuantumVulnerability.HIGH: 80,
            QuantumVulnerability.MEDIUM: 60,
            QuantumVulnerability.LOW: 40,
            QuantumVulnerability.SAFE: 0
        }
        
        vuln_score = vulnerability_weights.get(quantum_vulnerability, 50)
        threat_score = harvest_now_threat * 100
        compliance_score = compliance_gap * 100
        criticality_score = (criticality / 10.0) * 100
        
        # Complexity and scale reduce priority slightly but don't eliminate it
        complexity_factor = 1.0 - (migration_complexity * 0.2)
        scale_factor = min(1.0, installed_systems / 100.0) * 1.2
        
        raw_score = (
            vuln_score * 0.35 +
            threat_score * 0.25 +
            compliance_score * 0.15 +
            criticality_score * 0.15 +
            (100 * scale_factor) * 0.1
        )
        
        final_score = raw_score * complexity_factor
        return min(100.0, max(0.0, final_score))


class MigrationPriorityMatrix:
    """Build and manage migration priority matrix."""
    
    def __init__(self):
        self.systems: List[CryptoSystem] = []
        self.assessments: List[RiskAssessment] = []
        self.risk_calculator = RiskCalculator()
    
    def add_system(self, system: CryptoSystem) -> None:
        """Add a cryptographic system to inventory."""
        self.systems.append(system)
    
    def assess_system(self, system: CryptoSystem) -> RiskAssessment:
        """Perform comprehensive risk assessment for a system."""
        quantum_vuln = self.risk_calculator.calculate_quantum_vulnerability(
            system.algorithm,
            system.key_size,
            system.data_lifetime_years
        )
        
        harvest_threat = self.risk_calculator.calculate_harvest_now_threat(
            system.data_sensitivity,
            system.installed_systems,
            system.exposure_level
        )
        
        compliance_gap = self.risk_calculator.calculate_compliance_gap(
            system.algorithm,
            system.compliance_requirements
        )
        
        complexity = self.risk_calculator.calculate_migration_complexity(
            system.dependencies,
            system.criticality_score,
            system.installed_systems
        )
        
        migration_days = self.risk_calculator.calculate_estimated_migration_days(
            complexity,
            system.installed_systems,
            len(system.dependencies)
        )
        
        priority_score = self.risk_calculator.calculate_priority_score(
            quantum_vuln,
            harvest_threat,
            compliance_gap,
            complexity,
            system.criticality_score,
            system.installed_systems
        )
        
        # Determine phase based on priority
        if priority_score >= 80:
            phase = MigrationPhase.PHASE_1_CRITICAL
        elif priority_score >= 65:
            phase = MigrationPhase.PHASE_2_HIGH
        elif priority_score >= 50:
            phase = MigrationPhase.PHASE_3_MEDIUM
        elif priority_score >= 30:
            phase = MigrationPhase.PHASE_4_LOW
        else:
            phase = MigrationPhase.PHASE_5_MAINTENANCE
        
        assessment = RiskAssessment(
            system_id=system.system_id,
            quantum_vulnerability=quantum_vuln,
            harvest_now_threat=harvest_threat,
            future_threat_timeline=self.risk_calculator.CRYPTOGRAPHICALLY_RELEVANT_QUANTUM_COMPUTER_YEARS,
            data_at_risk_count=system.installed_systems,
            compliance_gap_score=compliance_gap,
            migration_complexity=complexity,
            estimated_migration_days=migration_days,
            priority_score=priority_score,
            recommended_phase=phase
        )
        
        self.assessments.append(assessment)
        return assessment
    
    def assess_all_systems(self) -> List[RiskAssessment]:
        """Assess all systems in inventory."""
        self.assessments.clear()
        for system in self.systems:
            self.assess_system(system)
        return self.assessments
    
    def get_priority_matrix(self) -> List[Dict[str, Any]]:
        """Get sorted priority matrix."""
        if not self.assessments:
            self.assess_all_systems()
        
        matrix = []
        for assessment, system in zip(
            sorted(self.assessments, key=lambda a: a.priority_score, reverse=True),
            sorted(self.systems, key=lambda s: self._get_system_priority(s), reverse=True)
        ):
            matching_system = next(
                (s for s in self.systems if s.system_id == assessment.system_id),
                None
            )
            if matching_system:
                matrix.append({
                    "system_id": matching_system.system_id,
                    "name": matching_system.name,
                    "algorithm": matching_system.algorithm.value,
                    "key_size": matching_system.key_size,
                    "quantum_safe_replacement": QuantumSafeAlgorithms.get_replacement(
                        matching_system.algorithm
                    ).value,
                    "priority_score": round(assessment.priority_score, 2),
                    "quantum_vulnerability": assessment.quantum_vulnerability.value,
                    "harvest_now_threat": round(assessment.harvest_now_threat, 3),
                    "compliance_gap": round(assessment.compliance_gap_score, 3),
                    "migration_complexity": round(assessment.migration_complexity, 3),
                    "estimated_days": assessment.estimated_migration_days,
                    "installed_systems": matching_system.installed_systems,
                    "data_sensitivity": matching_system.data_sensitivity,
                    "exposure_level": matching_system.exposure_level,
                    "criticality_score": matching_system.criticality_score,
                    "dependencies": len(matching_system.dependencies),
                    "compliance_requirements": len(matching_system.compliance_requirements),
                    "recommended_phase": assessment.recommended_phase.value
                })
        
        return matrix
    
    def _get_system_priority(self, system: CryptoSystem) -> float:
        """Get priority score for a system."""
        assessment = next(
            (a for a in self.assessments if a.system_id == system.system_id),
            None
        )
        return assessment.priority_score if assessment else 0.0
    
    def get_phase_summary(self) -> Dict[str, List[str]]:
        """Get systems grouped by migration phase."""
        if not self.assessments:
            self.assess_all_systems()
        
        phases = {phase.value: [] for phase in MigrationPhase}
        
        for assessment in self.assessments:
            system = next(
                (s for s in self.systems if s.system_id == assessment.system_id),
                None
            )
            if system:
                phases[assessment.recommended_phase.value].append(system.name)
        
        return {k: v for k, v in phases.items() if v}
    
    def get_timeline_estimate(self) -> Dict[str, Any]:
        """Get overall migration timeline estimate."""
        if not self.assessments:
            self.assess_all_systems()
        
        total_days = sum(a.estimated_migration_days for a in self.assessments)
        total_systems = sum(s.installed_systems for s in self.systems)
        critical_systems = len([a for a in self.assessments if a.priority_score >= 80])
        
        return {
            "total_estimated_days": total_days,
            "total_systems_to_migrate": total_systems,
            "critical_phase_systems": critical_systems,
            "estimated_completion_weeks": total_days / 7,
            "estimated_completion_date": (
                datetime.now() + timedelta(days=total_days)
            ).isoformat()
        }


def generate_sample_inventory() -> List[CryptoSystem]:
    """Generate sample cryptographic systems inventory."""
    systems = [
        CryptoSystem(
            system_id="SYS001",
            name="TLS Infrastructure - Web Servers",
            algorithm=CryptoAlgorithm.ECC_P256,
            key_size=256,
            installed_systems=150,
            data_sensitivity="CONFIDENTIAL",
            data_lifetime_years=7,
            last_updated="2023-01-15",
            criticality_score=9.0,
            exposure_level="INTERNET_FACING",
            dependencies=["LOAD_BALANCER", "PKI", "CERTIFICATE_STORE"],
            compliance_requirements=["PCI_DSS", "SOC2", "NIST_PQC"]
        ),
        CryptoSystem(
            system_id="SYS002",
            name="Email Encryption - S/MIME",
            algorithm=CryptoAlgorithm.RSA_2048,
            key_size=2048,
            installed_systems=5000,
            data_sensitivity="SECRET",
            data_lifetime_years=20,
            last_updated="2018-06-20",
            criticality_score=8.5,
            exposure_level="INTERNET_FACING",
            dependencies=["EMAIL_GATEWAY", "KEY_MANAGEMENT", "LDAP"],
            compliance_requirements=["HIPAA", "GDPR", "NIST_PQC", "ISO_20748"]
        ),
        CryptoSystem(
            system_id="SYS003",
            name="VPN - IPSec Tunnels",
            algorithm=CryptoAlgorithm.ECC_P384,
            key_size=384,
            installed_systems=50,
            data_sensitivity="CONFIDENTIAL",
            data_lifetime_years=10,
            last_updated="2021-03-10",
            criticality_score=8.0,
            exposure_level="NETWORK_ACCESSIBLE",
            dependencies=["FIREWALL", "KEY_EXCHANGE", "CERTIFICATE_MANAGEMENT"],
            compliance_requirements=["NIST_800_131A", "NIST_PQC"]
        ),
        CryptoSystem(
            system_id="SYS004",
            name="Database Encryption - At Rest",
            algorithm=CryptoAlgorithm.RSA_4096,
            key_size=4096,
            installed_systems=25,
            data_sensitivity="TOP_SECRET",
            data_lifetime_years=15,
            last_updated="2022-09-05",
            criticality_score=9.5,
            exposure_level="INTERNAL_ONLY",
            dependencies=["HSM", "KEY_VAULT", "ORCHESTRATION"],
            compliance_requirements=["NIST_PQC", "FedRAMP", "FISMA"]
        ),
        CryptoSystem(
            system_id="SYS005",
            name="Code Signing - CI/CD Pipeline",
            algorithm=CryptoAlgorithm.ECC_P521,
            key_size=521,
            installed_systems=3,
            data_sensitivity="INTERNAL",
            data_lifetime_years=3,
            last_updated="2023-11-20",
            criticality_score=7.0,
            exposure_level="NETWORK_ACCESSIBLE",
            dependencies=["BUILD_SERVER", "ARTIFACT_REPO", "CERTIFICATE_STORE"],
            compliance_requirements=["NIST_800_53"]
        ),
        CryptoSystem(
            system_id="SYS006",
            name="Document Signing - Legacy System",
            algorithm=CryptoAlgorithm.RSA_2048,
            key_size=2048,
            installed_systems=100,
            data_sensitivity="CONFIDENTIAL",
            data_lifetime_years=25,
            last_updated="2015-04-12",
            criticality_score=6.5,
            exposure_level="INTERNAL_ONLY",
            dependencies=["LEGACY_APP", "ARCHIVE_SYSTEM"],
            compliance_requirements=["eIDAS", "GDPR", "NIST_PQC"]
        ),
        CryptoSystem(
            system_id="SYS007",
            name="API Gateway - Mutual TLS",
            algorithm=CryptoAlgorithm.ECC_P256,
            key_size=256,
            installed_systems=40,
            data_sensitivity="CONFIDENTIAL",
            data_lifetime_years=5,
            last_updated="2023-06-30",
            criticality_score=7.5,
            exposure_level="INTERNET_FACING",
            dependencies=["API_GATEWAY", "SERVICE_MESH", "CERTIFICATE_STORE"],
            compliance_requirements=["OWASP", "NIST_PQC"]
        ),
        CryptoSystem(
            system_id="SYS008",
            name="Blockchain Node - Transaction Signing",
            algorithm=CryptoAlgorithm.ECC_P256,
            key_size=256,
            installed_systems=12,
            data_sensitivity="SECRET",
            data_lifetime_years=10,
            last_updated="2023-01-08",
            criticality_score=8.5,
            exposure_level="NETWORK_ACCESSIBLE",
            dependencies=["BLOCKCHAIN_NETWORK", "WALLET", "KEY_MANAGEMENT"],
            compliance_requirements=["NIST_PQC", "ISO_27001"]
        ),
        CryptoSystem(
            system_id="SYS009",
            name="SSH Keys - Server Access",
            algorithm=CryptoAlgorithm.RSA_4096,
            key_size=4096,
            installed_systems=500,
            data_sensitivity="INTERNAL",
            data_lifetime_years=8,
            last_updated="2022-11-18",
            criticality_score=8.0,
            exposure_level="NETWORK_ACCESSIBLE",
            dependencies=["SSH_SERVICE", "CREDENTIAL_STORE", "AUDIT_LOG"],
            compliance_requirements=["NIST_800_53", "CIS"]
        ),
        CryptoSystem(
            system_id="SYS010",
            name="Quantum-Safe TLS - Pilot",
            algorithm=CryptoAlgorithm.ML_KEM_768,
            key_size=0,
            installed_systems=5,
            data_sensitivity="CONFIDENTIAL",
            data_lifetime_years=5,
            last_updated="2024-01-10",
            criticality_score=5.0,
            exposure_level="INTERNAL_ONLY",
            dependencies=["OPENSSL", "LIBOQS"],
            compliance_requirements=["NIST_PQC"]
        )
    ]
    return systems


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quantum-Safe Cryptography Migration Priority Matrix Builder"
    )
    parser.add_argument(
        "--inventory-file",
        type=str,
        default=None,
        help="JSON file with cryptographic systems inventory"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "text", "csv"],
        default="json",
        help="Output format for priority matrix"
    )
    parser.add_argument(
        "--show-phases",
        action="store_true",
        help="Show migration phases and system grouping"
    )
    parser.add_argument(
        "--show-timeline",
        action="store_true",
        help="Show estimated migration timeline"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default=None,
        help="Export full matrix to JSON file"
    )
    parser.add_argument(
        "--min-priority",
        type=float,
        default=0.0,
        help="Minimum priority score to include in output (0-100)"
    )
    parser.add_argument(
        "--quantum-safe-only",
        action="store_true",
        help="Show only quantum-unsafe systems requiring migration"
    )
    
    args = parser.parse_args()
    
    # Load or generate inventory
    if args.inventory_file:
        try:
            with open(args.inventory_file, 'r') as f:
                inventory_data = json.load(f)
            systems = [
                CryptoSystem(
                    system_id=s["system_id"],
                    name=s["name"],
                    algorithm=CryptoAlgorithm[s["algorithm"].replace("-", "_")],
                    key_size=s["key_size"],
                    installed_systems=s["installed_systems"],
                    data_sensitivity=s["data_sensitivity"],
                    data_lifetime_years=s["data_lifetime_years"],
                    last_updated=s["last_updated"],
                    criticality_score=s["criticality_score"],
                    exposure_level=s["exposure_level"],
                    dependencies=s["dependencies"],
                    compliance_requirements=s["compliance_requirements"]
                )
                for s in inventory_data
            ]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading inventory file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        systems = generate_sample_inventory()
    
    # Build priority matrix
    matrix = MigrationPriorityMatrix()
    for system in systems:
        matrix.add_system(system)
    
    # Generate priority matrix
    priority_data = matrix.get_priority_matrix()
    
    # Filter by minimum priority
    if args.min_priority > 0:
        priority_data = [
            item for item in priority_data
            if item["priority_score"] >= args.min_priority
        ]
    
    # Filter quantum-safe systems if requested
    if args.quantum_safe_only:
        priority_data = [
            item for item in priority_data
            if item["quantum_vulnerability"] != "SAFE"
        ]
    
    # Output priority matrix
    if args.output_format == "json":
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_systems_assessed": len(systems),
            "systems_requiring_migration": len(priority_data),
            "priority_matrix": priority_data
        }
        print(json.dumps(output, indent=2))
    
    elif args.output_format == "text":
        print("\n" + "="*120)
        print("QUANTUM-SAFE CRYPTOGRAPHY MIGRATION PRIORITY MATRIX")
        print("="*120)
        print(f"Assessment Date: {datetime.now().isoformat()}")
        print(f"Total Systems: {len(systems)}")
        print(f"Systems Requiring Migration: {len(priority_data)}\n")
        
        print(f"{'System ID':<10} {'Name':<30} {'Algorithm':<12} {'Priority':<10} {'Vulnerability':<12} "
              f"{'Complexity':<12} {'Est. Days':<10} {'Phase':<20}")
        print("-"*120)
        
        for item in priority_data:
            phase = item["recommended_phase"].split(": ")[1] if ": " in item["recommended_phase"] else item["recommended_phase"]
            print(f"{item['system_id']:<10} {item['name'][:29]:<30} {item['algorithm']:<12} "
                  f"{item['priority_score']:<10.1f} {item['quantum_vulnerability']:<12} "
                  f"{item['migration_complexity']:<12.2f} {item['estimated_days']:<10} {phase:<20}")
    
    elif args.output_format == "csv":
        import csv
        import io
        
        output = io.StringIO()
        if priority_data:
            writer = csv.DictWriter(output, fieldnames=priority_data[0].keys())
            writer.writeheader()
            writer.writerows(priority_data)
            print(output.getvalue())
    
    # Show phase summary if requested
    if args.show_phases:
        phase_summary = matrix.get_phase_summary()
        print("\n" + "="*80)
        print("MIGRATION PHASE SUMMARY")
        print("="*80)
        for phase, systems_list in phase_summary.items():
            print(f"\n{phase}")
            print(f"  Count: {len(systems_list)}")
            for system_name in systems_list:
                print(f"    - {system_name}")
    
    # Show timeline if requested
    if args.show_timeline:
        timeline = matrix.get_timeline_estimate()
        print("\n" + "="*80)
        print("MIGRATION TIMELINE ESTIMATE")
        print("="*80)
        print(f"Total Estimated Duration: {timeline['total_estimated_days']} days "
              f"({timeline['estimated_completion_weeks']:.1f} weeks)")
        print(f"Total Systems to Migrate: {timeline['total_systems_to_migrate']}")
        print(f"Critical Phase Systems: {timeline['critical_phase_systems']}")
        print(f"Estimated Completion Date: {timeline['estimated_completion_date']}")
    
    # Export to JSON if requested
    if args.export_json:
        export_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_systems": len(systems),
                "systems_analyzed": len(priority_data)
            },
            "priority_matrix": priority_data,
            "phase_summary": matrix.get_phase_summary(),
            "timeline_