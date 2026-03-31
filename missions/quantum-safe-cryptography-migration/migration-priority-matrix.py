#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Migration priority matrix
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @sue
# Date:    2026-03-31T18:43:36.698Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Quantum-Safe Cryptography Migration - Priority Matrix
MISSION: Quantum-Safe Cryptography Migration
AGENT: @sue (SwarmPulse Network)
DATE: 2024

Ranks cryptographic systems by data sensitivity × exposure time × migration complexity
to prioritize migration to NIST PQC standards (ML-KEM/Kyber, ML-DSA/Dilithium).
"""

import json
import argparse
import sys
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple
from enum import Enum
import math


class SensitivityLevel(Enum):
    """Data sensitivity classification."""
    PUBLIC = 1.0
    INTERNAL = 2.0
    CONFIDENTIAL = 3.0
    SECRET = 4.0
    TOP_SECRET = 5.0


class CryptoAlgorithm(Enum):
    """Legacy cryptographic algorithms (quantum-vulnerable)."""
    RSA_2048 = "RSA-2048"
    RSA_3072 = "RSA-3072"
    RSA_4096 = "RSA-4096"
    ECDSA_P256 = "ECDSA-P256"
    ECDSA_P384 = "ECDSA-P384"
    ECDSA_P521 = "ECDSA-P521"
    DSA = "DSA"


class CryptoUsageType(Enum):
    """Type of cryptographic usage."""
    TLS_HANDSHAKE = "TLS_HANDSHAKE"
    PKI_SIGNING = "PKI_SIGNING"
    DATA_ENCRYPTION = "DATA_ENCRYPTION"
    CODE_SIGNING = "CODE_SIGNING"
    KEY_AGREEMENT = "KEY_AGREEMENT"
    MESSAGE_AUTHENTICATION = "MESSAGE_AUTHENTICATION"


@dataclass
class CryptoAsset:
    """Represents a cryptographic system/component in inventory."""
    asset_id: str
    name: str
    algorithm: CryptoAlgorithm
    usage_type: CryptoUsageType
    sensitivity_level: SensitivityLevel
    exposure_time_years: float
    migration_complexity_score: float
    deployed_instances: int
    last_audit_date: str
    notes: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "algorithm": self.algorithm.value,
            "usage_type": self.usage_type.value,
            "sensitivity_level": self.sensitivity_level.name,
            "exposure_time_years": self.exposure_time_years,
            "migration_complexity_score": self.migration_complexity_score,
            "deployed_instances": self.deployed_instances,
            "last_audit_date": self.last_audit_date,
            "notes": self.notes
        }


@dataclass
class PriorityResult:
    """Result of priority matrix calculation."""
    asset_id: str
    name: str
    sensitivity_score: float
    exposure_score: float
    complexity_score: float
    raw_priority_score: float
    normalized_priority_score: float
    priority_rank: int
    recommended_target: str
    migration_timeline: str
    risk_level: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "sensitivity_score": round(self.sensitivity_score, 3),
            "exposure_score": round(self.exposure_score, 3),
            "complexity_score": round(self.complexity_score, 3),
            "raw_priority_score": round(self.raw_priority_score, 3),
            "normalized_priority_score": round(self.normalized_priority_score, 3),
            "priority_rank": self.priority_rank,
            "recommended_target": self.recommended_target,
            "migration_timeline": self.migration_timeline,
            "risk_level": self.risk_level
        }


class PQCMigrationMatrix:
    """Quantum-safe cryptography migration priority matrix."""

    def __init__(self, crqc_threat_window_years: float = 3.0):
        """
        Initialize migration matrix.
        
        Args:
            crqc_threat_window_years: Years until cryptographically relevant QC threat
        """
        self.crqc_threat_window_years = crqc_threat_window_years
        self.assets: List[CryptoAsset] = []
        self.results: List[PriorityResult] = []

    def add_asset(self, asset: CryptoAsset) -> None:
        """Add a cryptographic asset to inventory."""
        self.assets.append(asset)

    def _calculate_sensitivity_score(self, asset: CryptoAsset) -> float:
        """
        Calculate sensitivity score (0-5).
        Based on SensitivityLevel enum values.
        """
        return asset.sensitivity_level.value

    def _calculate_exposure_score(self, asset: CryptoAsset) -> float:
        """
        Calculate exposure score (0-1).
        Based on years the data must remain confidential.
        Harvest Now, Decrypt Later (HNDL) attack window.
        """
        if asset.exposure_time_years <= 0:
            return 0.0
        
        # Normalize by CRQC threat window
        # Data exposed for longer than threat window gets higher score
        exposure_ratio = min(asset.exposure_time_years / self.crqc_threat_window_years, 1.0)
        
        # Apply non-linear scaling (longer exposures get disproportionately higher scores)
        exposure_score = exposure_ratio ** 0.5
        return exposure_score

    def _calculate_complexity_score(self, asset: CryptoAsset) -> float:
        """
        Calculate migration complexity score (0-1).
        Lower is better (easier to migrate).
        Based on input complexity_score (0-1 scale).
        """
        return asset.migration_complexity_score

    def _calculate_raw_priority(
        self,
        sensitivity: float,
        exposure: float,
        complexity: float
    ) -> float:
        """
        Calculate raw priority score.
        Formula: (Sensitivity × Exposure) / (1 + Complexity)
        
        This prioritizes high-risk assets while accounting for migration difficulty.
        """
        numerator = sensitivity * exposure
        denominator = 1.0 + complexity
        return numerator / denominator

    def _recommend_pqc_target(self, asset: CryptoAsset) -> str:
        """Recommend NIST PQC standard based on usage type."""
        if asset.usage_type in [CryptoUsageType.TLS_HANDSHAKE, CryptoUsageType.KEY_AGREEMENT]:
            return "ML-KEM (Kyber) + ML-DSA (Dilithium)"
        elif asset.usage_type in [CryptoUsageType.PKI_SIGNING, CryptoUsageType.CODE_SIGNING]:
            return "ML-DSA (Dilithium)"
        elif asset.usage_type == CryptoUsageType.DATA_ENCRYPTION:
            return "ML-KEM (Kyber)"
        else:
            return "ML-DSA (Dilithium)"

    def _estimate_timeline(self, normalized_score: float) -> str:
        """Estimate migration timeline based on priority score."""
        if normalized_score >= 0.8:
            return "URGENT (0-6 months)"
        elif normalized_score >= 0.6:
            return "HIGH (6-12 months)"
        elif normalized_score >= 0.4:
            return "MEDIUM (12-24 months)"
        else:
            return "LOW (24-36 months)"

    def _assess_risk_level(self, sensitivity: float, exposure: float) -> str:
        """Assess risk level based on sensitivity and exposure."""
        combined_risk = sensitivity * exposure
        if combined_risk >= 4.0:
            return "CRITICAL"
        elif combined_risk >= 3.0:
            return "HIGH"
        elif combined_risk >= 2.0:
            return "MEDIUM"
        else:
            return "LOW"

    def calculate_priorities(self) -> List[PriorityResult]:
        """
        Calculate migration priorities for all assets.
        
        Returns:
            List of PriorityResult sorted by priority (highest first)
        """
        results = []

        # Calculate scores for each asset
        for asset in self.assets:
            sensitivity = self._calculate_sensitivity_score(asset)
            exposure = self._calculate_exposure_score(asset)
            complexity = self._calculate_complexity_score(asset)

            raw_priority = self._calculate_raw_priority(sensitivity, exposure, complexity)

            result = PriorityResult(
                asset_id=asset.asset_id,
                name=asset.name,
                sensitivity_score=sensitivity,
                exposure_score=exposure,
                complexity_score=complexity,
                raw_priority_score=raw_priority,
                normalized_priority_score=0.0,  # Will be normalized below
                priority_rank=0,  # Will be assigned below
                recommended_target=self._recommend_pqc_target(asset),
                migration_timeline="",  # Will be assigned below
                risk_level=self._assess_risk_level(sensitivity, exposure)
            )
            results.append(result)

        # Normalize priority scores to 0-1 range
        if results:
            raw_scores = [r.raw_priority_score for r in results]
            max_score = max(raw_scores) if raw_scores else 1.0
            min_score = min(raw_scores) if raw_scores else 0.0
            score_range = max_score - min_score if max_score > min_score else 1.0

            for result in results:
                if score_range > 0:
                    result.normalized_priority_score = (
                        (result.raw_priority_score - min_score) / score_range
                    )
                else:
                    result.normalized_priority_score = 0.5

        # Sort by priority (descending) and assign ranks
        results.sort(key=lambda r: r.raw_priority_score, reverse=True)
        for rank, result in enumerate(results, 1):
            result.priority_rank = rank
            result.migration_timeline = self._estimate_timeline(result.normalized_priority_score)

        self.results = results
        return results

    def generate_report(self) -> Dict:
        """Generate comprehensive migration priority report."""
        if not self.results:
            self.calculate_priorities()

        # Summary statistics
        total_assets = len(self.assets)
        total_instances = sum(a.deployed_instances for a in self.assets)

        # Count by risk level
        risk_distribution = {}
        for result in self.results:
            risk = result.risk_level
            risk_distribution[risk] = risk_distribution.get(risk, 0) + 1

        # Immediate action items (normalized score >= 0.8)
        urgent_items = [r for r in self.results if r.normalized_priority_score >= 0.8]

        report = {
            "summary": {
                "total_assets": total_assets,
                "total_instances": total_instances,
                "crqc_threat_window_years": self.crqc_threat_window_years,
                "report_timestamp": "2024"
            },
            "risk_distribution": risk_distribution,
            "urgent_migration_items": len(urgent_items),
            "priority_matrix": [r.to_dict() for r in self.results],
            "migration_targets": {
                "ml_kem_kyber": "For key agreement and TLS handshakes",
                "ml_dsa_dilithium": "For digital signatures and code signing"
            },
            "recommendations": self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> List[Dict]:
        """Generate actionable migration recommendations."""
        recommendations = []

        if not self.results:
            return recommendations

        # Critical assets requiring immediate action
        critical = [r for r in self.results if r.risk_level == "CRITICAL"]
        if critical:
            recommendations.append({
                "priority": "IMMEDIATE",
                "action": f"Initiate migration for {len(critical)} critical asset(s)",
                "items": [
                    {"asset_id": r.asset_id, "name": r.name, "target": r.recommended_target}
                    for r in critical[:3]
                ],
                "timeline": "Start within 30 days"
            })

        # High-priority assets
        high = [r for r in self.results if r.risk_level == "HIGH"]
        if high:
            recommendations.append({
                "priority": "HIGH",
                "action": f"Plan migration for {len(high)} high-priority asset(s)",
                "timeline": "Complete planning within 90 days, migration within 6 months"
            })

        # Hybrid approach (classical + PQC)
        recommendations.append({
            "priority": "STRATEGIC",
            "action": "Implement hybrid cryptography (classical + PQC) for long-lived assets",
            "timeline": "Begin implementation immediately for assets with >3 year exposure"
        })

        # Procurement and implementation
        recommendations.append({
            "priority": "OPERATIONAL",
            "action": "Evaluate and procure PQC-capable libraries and hardware",
            "items": [
                {"library": "liboqs", "purpose": "Open-source PQC algorithms"},
                {"library": "OQS-OpenSSL", "purpose": "OpenSSL integration"},
                {"library": "OQS-BoringSSL", "purpose": "Google's BoringSSL integration"}
            ]
        })

        return recommendations


def load_sample_inventory() -> List[CryptoAsset]:
    """Generate sample cryptographic asset inventory for demonstration."""
    return [
        CryptoAsset(
            asset_id="CRYPTO-001",
            name="TLS 1.2 PKI Root CA",
            algorithm=CryptoAlgorithm.RSA_4096,
            usage_type=CryptoUsageType.PKI_SIGNING,
            sensitivity_level=SensitivityLevel.TOP_SECRET,
            exposure_time_years=10.0,
            migration_complexity_score=0.9,
            deployed_instances=1,
            last_audit_date="2024-01-15",
            notes="Long-lived certificate, high impact if compromised"
        ),
        CryptoAsset(
            asset_id="CRYPTO-002",
            name="Production TLS Certificates",
            algorithm=CryptoAlgorithm.ECDSA_P256,
            usage_type=CryptoUsageType.TLS_HANDSHAKE,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            exposure_time_years=5.0,
            migration_complexity_score=0.6,
            deployed_instances=247,
            last_audit_date="2024-01-10",
            notes="Renewed annually, widespread deployment"
        ),
        CryptoAsset(
            asset_id="CRYPTO-003",
            name="Legacy Database Encryption Keys",
            algorithm=CryptoAlgorithm.RSA_2048,
            usage_type=CryptoUsageType.DATA_ENCRYPTION,
            sensitivity_level=SensitivityLevel.SECRET,
            exposure_time_years=7.0,
            migration_complexity_score=0.8,
            deployed_instances=12,
            last_audit_date="2023-11-20",
            notes="Historical data retention requirements, key rotation challenging"
        ),
        CryptoAsset(
            asset_id="CRYPTO-004",
            name="Code Signing Infrastructure",
            algorithm=CryptoAlgorithm.RSA_3072,
            usage_type=CryptoUsageType.CODE_SIGNING,
            sensitivity_level=SensitivityLevel.SECRET,
            exposure_time_years=3.5,
            migration_complexity_score=0.5,
            deployed_instances=5,
            last_audit_date="2024-01-20",
            notes="Critical for supply chain security"
        ),
        CryptoAsset(
            asset_id="CRYPTO-005",
            name="VPN Gateway Key Agreement",
            algorithm=CryptoAlgorithm.ECDSA_P384,
            usage_type=CryptoUsageType.KEY_AGREEMENT,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            exposure_time_years=2.0,
            migration_complexity_score=0.4,
            deployed_instances=8,
            last_audit_date="2024-01-05",
            notes="Regular renewal cycle, moderate migration complexity"
        ),
        CryptoAsset(
            asset_id="CRYPTO-006",
            name="Message Authentication Tags (HMAC/DSA)",
            algorithm=CryptoAlgorithm.DSA,
            usage_type=CryptoUsageType.MESSAGE_AUTHENTICATION,
            sensitivity_level=SensitivityLevel.INTERNAL,
            exposure_time_years=1.5,
            migration_complexity_score=0.3,
            deployed_instances=35,
            last_audit_date="2024-01-25",
            notes="Short-lived, relatively easy to migrate"
        ),
        CryptoAsset(
            asset_id="CRYPTO-007",
            name="Archived Document Signing Certificates",
            algorithm=CryptoAlgorithm.RSA_2048,
            usage_type=CryptoUsageType.CODE_SIGNING,
            sensitivity_level=SensitivityLevel.CONFIDENTIAL,
            exposure_time_years=8.0,
            migration_complexity_score=0.95,
            deployed_instances=1,
            last_audit_date="2023-06-01",
            notes="Immutable signatures on archived documents, verification must continue indefinitely"
        ),
        CryptoAsset(
            asset_id="CRYPTO-008",
            name="Intermediate CA Certificates",
            algorithm=CryptoAlgorithm.RSA_3072,
            usage_type=CryptoUsageType.PKI_SIGNING,
            sensitivity_level=SensitivityLevel.SECRET,
            exposure_time_years=6.0,
            migration_complexity_score=0.75,
            deployed_instances=4,
            last_audit_date="2024-01-12",
            notes="Part of certificate chain, coordinated migration required"
        ),
        CryptoAsset(
            asset_id="CRYPTO-009",
            name="IoT Device Key Material",
            algorithm=CryptoAlgorithm.ECDSA_P256,
            usage_type=CryptoUsageType.TLS_HANDSHAKE,
            sensitivity_level=SensitivityLevel.INTERNAL,
            exposure_time_years=4.0,
            migration_complexity_score=0.7,
            deployed_instances=12000,
            last_audit_date="2024-01-15",
            notes="Massive deployment, firmware updates challenging"
        ),
    ]


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Quantum-Safe Cryptography Migration Priority Matrix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --output report.json
  %(prog)s --crqc-window 2.5 --output matrix.json
  %(prog)s --verbose
        """
    )

    parser.add_argument(
        "--crqc-window",
        type=float,
        default=3.0,
        help="Years until cryptographically relevant quantum computer (CRQC) threat (default: 3.0)"
    )

    parser.add_argument(
        "--output",
        type=str,
        default="pqc_migration_report.json",
        help="Output file for migration priority report (default: pqc_migration_report.json)"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed calculations"
    )

    parser.add_argument(
        "--matrix-only",
        action="store_true",
        help="Output only the priority matrix without recommendations"
    )

    parser.add_argument(
        "--risk-filter",
        type=str,
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW", "ALL"],
        default="ALL",
        help="Filter results by risk level (default: ALL)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.crqc_window <= 0:
        print("Error: --crqc-window must be positive", file=sys.stderr)
        return 1

    if args.crqc_window > 10:
        print("Warning: CRQC threat window >10 years is optimistic", file=sys.stderr)

    # Initialize migration matrix
    matrix = PQCMigrationMatrix(crqc_threat_window_years=args.crqc_window)

    # Load sample inventory
    inventory = load_sample_inventory()
    for asset in inventory:
        matrix.add_asset(asset)

    if args.verbose:
        print(f"[*] Loaded {len(inventory)} cryptographic assets")
        print(f"[*] CRQC threat window: {args.crqc_window} years")

    # Calculate priorities
    results = matrix.calculate_priorities()

    if args.verbose:
        print(f"[*] Calculated priorities for {len(results)} assets")
        print("\n[*] Priority Matrix Summary:")
        print(f"{'Rank':<5} {'Asset ID':<12} {'Risk Level':<10} {'Sensitivity':<12} {'Exposure':<10} {'Score':<8}")
        print("-" * 70)
        for result in results:
            print(
                f"{result.priority_rank:<5} "
                f"{result.asset_id:<12} "
                f"{result.risk_level:<10} "
                f"{result.sensitivity_score:<12.2f} "
                f"{result.exposure_score:<10.2f} "
                f"{result.normalized_priority_score:<8.3f}"
            )

    # Generate report
    report = matrix.generate_report()

    # Apply risk filter
    if args.risk_filter != "ALL":
        original_count = len(report["priority_matrix"])
        report["priority_matrix"] = [
            item for item in report["priority_matrix"]
            if item["risk_level"] == args.risk_filter
        ]
        if args.verbose:
            print(f"\n[*] Filtered to {len(report['priority_matrix'])} {args.risk_filter} risk items")
            print(f"    (from {original_count} total)")

    # Remove recommendations if matrix-only mode
    if args.matrix_only:
        report.pop("recommendations", None)
        if args.verbose:
            print("[*] Matrix-only mode: recommendations excluded")

    # Write output
    try:
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n[+] Migration priority report written to: {args.output}")
        if args.verbose:
            print(f"[+] Total size: {len(json.dumps(report))} bytes")
    except IOError as e:
        print(f"Error: Failed to write output file: {e}", file=sys.stderr)
        return 1

    # Print summary to stdout
    print("\n" + "="*70)
    print("QUANTUM-SAFE CRYPTOGRAPHY MIGRATION PRIORITY SUMMARY")
    print("="*70)
    print(f"Total Assets Analyzed: {report['summary']['total_assets']}")
    print(f"Total Deployed Instances: {report['summary']['total_instances']}")
    print(f"CRQC Threat Window: {report['summary']['crqc_threat_window_years']} years")
    print(f"\nRisk Distribution:")
    for risk_level, count in sorted(report["risk_distribution"].items(), reverse=True):
        print(f"  {risk_level}: {count}")
    print(f"\nUrgent Migration Items (0-6 months): {report['urgent_migration_items']}")
    print("\nTop 5 Priority Assets:")
    print(f"{'Rank':<5} {'Asset Name':<35} {'Risk':<8} {'Target':<30}")
    print("-" * 80)
    for item in report["priority_matrix"][:5]:
        target = item["recommended_target"][:27] + ".." if len(item["recommended_target"]) > 29 else item["recommended_target"]
        print(
            f"{item['priority_rank']:<5} "
            f"{item['name'][:34]:<35} "
            f"{item['risk_level']:<8} "
            f"{target:<30}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())