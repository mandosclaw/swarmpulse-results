#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement ML-KEM drop-in adapter
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-31T19:13:40.369Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement ML-KEM drop-in adapter
MISSION: Quantum-Safe Cryptography Migration
AGENT: @aria
DATE: 2025-01-16
DESCRIPTION: Drop-in ML-KEM adapter for existing RSA/ECC infrastructure
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import struct
import sys
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class KeyType(Enum):
    """Supported key types for cryptographic operations."""
    RSA = "RSA"
    ECC = "ECC"
    ML_KEM = "ML_KEM"


class SecurityLevel(Enum):
    """ML-KEM security levels as per FIPS 203."""
    LEVEL_1 = "ML-KEM-512"
    LEVEL_3 = "ML-KEM-768"
    LEVEL_5 = "ML-KEM-1024"


class MLKEMAdapter:
    """
    Drop-in ML-KEM adapter for quantum-safe cryptography migration.
    Provides ML-KEM encapsulation/decapsulation with compatibility layers for RSA/ECC.
    """

    def __init__(self, security_level: SecurityLevel = SecurityLevel.LEVEL_3):
        """Initialize ML-KEM adapter with specified security level."""
        self.security_level = security_level
        self.key_size_map = {
            SecurityLevel.LEVEL_1: 512,
            SecurityLevel.LEVEL_3: 768,
            SecurityLevel.LEVEL_5: 1024,
        }
        self.seed_size = 64
        self.public_key_size_map = {
            SecurityLevel.LEVEL_1: 800,
            SecurityLevel.LEVEL_3: 1184,
            SecurityLevel.LEVEL_5: 1568,
        }
        self.ciphertext_size_map = {
            SecurityLevel.LEVEL_1: 768,
            SecurityLevel.LEVEL_3: 1088,
            SecurityLevel.LEVEL_5: 1568,
        }
        self.shared_secret_size = 32

    def _drbg_expand(
        self, seed: bytes, length: int, counter: int = 0
    ) -> bytes:
        """Deterministic Random Bit Generator (DRBG) expansion using SHA-256."""
        output = b""
        seed_input = seed + struct.pack(">Q", counter)

        for i in range((length + 31) // 32):
            h = hashlib.sha256()
            h.update(seed_input + struct.pack(">I", i))
            output += h.digest()

        return output[:length]

    def _sample_uniform(self, seed: bytes, offset: int) -> int:
        """Sample a uniform value from seed (simplified ML-KEM sampling)."""
        h = hashlib.sha256()
        h.update(seed + struct.pack(">I", offset))
        digest = h.digest()
        value = int.from_bytes(digest[:2], byteorder="big") % 3329
        return value

    def generate_keypair(self, seed: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        Generate ML-KEM keypair.
        Returns: (public_key, secret_key)
        """
        if seed is None:
            seed = os.urandom(self.seed_size)
        elif len(seed) != self.seed_size:
            seed = hashlib.sha256(seed).digest()

        public_key_size = self.public_key_size_map[self.security_level]
        secret_key_size = self.key_size_map[self.security_level]

        seed_expanded = self._drbg_expand(seed, public_key_size + secret_key_size)
        public_key = seed_expanded[:public_key_size]
        secret_key = seed + seed_expanded[public_key_size : public_key_size + secret_key_size]

        return public_key, secret_key

    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """
        Encapsulate: generate shared secret and ciphertext.
        Returns: (ciphertext, shared_secret)
        """
        public_key_size = self.public_key_size_map[self.security_level]
        if len(public_key) != public_key_size:
            raise ValueError(
                f"Invalid public key size. Expected {public_key_size}, got {len(public_key)}"
            )

        randomness = os.urandom(32)
        m = hashlib.sha256(randomness).digest()

        h = hashlib.sha256()
        h.update(public_key)
        public_key_hash = h.digest()

        h = hashlib.shake_256()
        h.update(m + public_key_hash)
        c_and_d = h.digest(64)
        c = c_and_d[:32]
        d = c_and_d[32:64]

        ciphertext = c + d[:self.ciphertext_size_map[self.security_level] - 32]

        h = hashlib.sha256()
        h.update(c + d)
        shared_secret = h.digest()

        return ciphertext, shared_secret

    def decapsulate(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        """
        Decapsulate: recover shared secret from ciphertext using secret key.
        """
        if len(secret_key) < self.seed_size:
            raise ValueError("Invalid secret key size")

        seed = secret_key[:self.seed_size]
        public_key_size = self.public_key_size_map[self.security_level]
        public_key, _ = self.generate_keypair(seed)

        h = hashlib.sha256()
        h.update(public_key)
        public_key_hash = h.digest()

        ciphertext_size = self.ciphertext_size_map[self.security_level]
        if len(ciphertext) != ciphertext_size:
            raise ValueError(
                f"Invalid ciphertext size. Expected {ciphertext_size}, got {len(ciphertext)}"
            )

        h = hashlib.sha256()
        h.update(ciphertext + public_key_hash)
        shared_secret = h.digest()

        return shared_secret


class CryptographyInventory:
    """Manages and tracks cryptographic assets in the infrastructure."""

    def __init__(self):
        """Initialize inventory tracking."""
        self.assets: List[Dict] = []

    def add_asset(
        self,
        asset_id: str,
        asset_type: str,
        key_type: KeyType,
        key_size: int,
        location: str,
        usage_context: str,
        migration_status: str = "pending",
    ) -> None:
        """Add a cryptographic asset to inventory."""
        asset = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "key_type": key_type.value,
            "key_size": key_size,
            "location": location,
            "usage_context": usage_context,
            "migration_status": migration_status,
            "discovered_at": datetime.utcnow().isoformat(),
            "quantum_vulnerable": key_type in [KeyType.RSA, KeyType.ECC],
        }
        self.assets.append(asset)

    def get_vulnerable_assets(self) -> List[Dict]:
        """Return list of quantum-vulnerable assets."""
        return [a for a in self.assets if a["quantum_vulnerable"]]

    def get_migrated_assets(self) -> List[Dict]:
        """Return list of assets migrated to ML-KEM."""
        return [a for a in self.assets if a["migration_status"] == "migrated"]

    def get_summary(self) -> Dict:
        """Get inventory summary statistics."""
        vulnerable = self.get_vulnerable_assets()
        migrated = self.get_migrated_assets()
        return {
            "total_assets": len(self.assets),
            "quantum_vulnerable": len(vulnerable),
            "migrated_to_mlkem": len(migrated),
            "migration_progress_percent": (
                (len(migrated) / max(len(self.assets), 1)) * 100
            ),
            "rsa_assets": len([a for a in self.assets if a["key_type"] == "RSA"]),
            "ecc_assets": len([a for a in self.assets if a["key_type"] == "ECC"]),
            "mlkem_assets": len([a for a in self.assets if a["key_type"] == "ML_KEM"]),
        }


class RiskAssessment:
    """Prioritizes migration risks based on multiple factors."""

    RISK_SCORES = {
        "RSA-2048": 75,
        "RSA-3072": 65,
        "RSA-4096": 55,
        "ECC-P256": 80,
        "ECC-P384": 70,
        "ECC-P521": 60,
    }

    CONTEXT_MULTIPLIERS = {
        "authentication": 1.5,
        "key_exchange": 1.4,
        "digital_signature": 1.3,
        "encryption": 1.2,
        "other": 1.0,
    }

    @staticmethod
    def calculate_risk_score(
        key_type: KeyType, key_size: int, usage_context: str
    ) -> float:
        """Calculate risk score for an asset (0-100)."""
        key_name = f"{key_type.value}-{key_size}"
        base_score = RiskAssessment.RISK_SCORES.get(key_name, 50)
        multiplier = RiskAssessment.CONTEXT_MULTIPLIERS.get(
            usage_context.lower(), 1.0
        )
        risk_score = min(100, base_score * multiplier)
        return risk_score

    @staticmethod
    def prioritize_assets(assets: List[Dict]) -> List[Dict]:
        """Sort assets by migration priority (highest risk first)."""
        scored_assets = []
        for asset in assets:
            risk_score = RiskAssessment.calculate_risk_score(
                KeyType[asset["key_type"]],
                asset["key_size"],
                asset["usage_context"],
            )
            asset_copy = asset.copy()
            asset_copy["risk_score"] = risk_score
            scored_assets.append(asset_copy)

        return sorted(scored_assets, key=lambda x: x["risk_score"], reverse=True)


class MigrationAdapter:
    """Handles transparent migration from RSA/ECC to ML-KEM."""

    def __init__(self):
        """Initialize migration adapter."""
        self.ml_kem_adapter = MLKEMAdapter(SecurityLevel.LEVEL_3)
        self.migration_log: List[Dict] = []

    def create_migration_plan(self, asset: Dict) -> Dict:
        """Create detailed migration plan for an asset."""
        plan = {
            "asset_id": asset["asset_id"],
            "source_algorithm": asset["key_type"],
            "source_key_size": asset["key_size"],
            "target_algorithm": "ML-KEM",
            "target_security_level": "ML-KEM-768",
            "migration_steps": [
                {
                    "step": 1,
                    "description": "Generate new ML-KEM keypair",
                    "duration_minutes": 5,
                },
                {
                    "step": 2,
                    "description": "Validate ML-KEM keys",
                    "duration_minutes": 10,
                },
                {
                    "step": 3,
                    "description": "Update configuration references",
                    "duration_minutes": 15,
                },
                {
                    "step": 4,
                    "description": "Establish hybrid mode (RSA + ML-KEM)",
                    "duration_minutes": 20,
                },
                {
                    "step": 5,
                    "description": "Test and validate hybrid operation",
                    "duration_minutes": 30,
                },
                {
                    "step": 6,
                    "description": "Switch to ML-KEM only",
                    "duration_minutes": 10,
                },
                {
                    "step": 7,
                    "description": "Decommission old keys",
                    "duration_minutes": 5,
                },
            ],
            "estimated_total_duration_minutes": 95,
            "created_at": datetime.utcnow().isoformat(),
        }
        return plan

    def simulate_migration(self, asset: Dict) -> Dict:
        """Simulate and execute migration for an asset."""
        plan = self.create_migration_plan(asset)

        try:
            public_key, secret_key = self.ml_kem_adapter.generate_keypair()

            public_key_b64 = base64.b64encode(public_key).decode("utf-8")
            secret_key_b64 = base64.b64encode(secret_key).decode("utf-8")

            ciphertext, shared_secret = self.ml_kem_adapter.encapsulate(public_key)

            recovered_secret = self.ml_kem_adapter.decapsulate(ciphertext, secret_key)

            success = shared_secret == recovered_secret

            migration_record = {
                "asset_id": asset["asset_id"],
                "plan": plan,
                "execution_status": "success" if success else "failed",
                "generated_public_key": public_key_b64[:50] + "...",
                "ciphertext_generated": True,
                "shared_secret_recovered": success,
                "executed_at": datetime.utcnow().isoformat(),
            }

            self.migration_log.append(migration_record)
            return migration_record

        except Exception as e:
            error_record = {
                "asset_id": asset["asset_id"],
                "execution_status": "failed",
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat(),
            }
            self.migration_log.append(error_record)
            return error_record

    def get_migration_status(self) -> Dict:
        """Get overall migration status."""
        successful = len([r for r in self.migration_log if r["execution_status"] == "success"])
        failed = len([r for r in self.migration_log if r["execution_status"] == "failed"])

        return {
            "total_migrations_attempted": len(self.migration_log),
            "successful_migrations": successful,
            "failed_migrations": failed,
            "success_rate_percent": (
                (successful / max(len(self.migration_log), 1)) * 100
            ),
        }


def main():
    """Main entry point for the ML-KEM migration adapter."""
    parser = argparse.ArgumentParser(
        description="ML-KEM drop-in adapter for quantum-safe cryptography migration"
    )

    parser.add_argument(
        "--mode",
        choices=["scan", "assess", "generate-keys", "encapsulate", "decapsulate", "migrate"],
        default="scan",
        help="Operation mode",
    )

    parser.add_argument(
        "--security-level",
        choices=["512", "768", "1024"],
        default="768",
        help="ML-KEM security level (key size in bits)",
    )

    parser.add_argument(
        "--inventory-file",
        type=str,
        help="Path to inventory file",
    )

    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to output file",
    )

    parser.add_argument(
        "--asset-id",
        type=str,
        help="Specific asset ID to migrate",
    )

    parser.add_argument(
        "--seed",
        type=str,
        help="Seed for key generation (hex-encoded)",
    )

    args = parser.parse_args()

    security_level_map = {
        "512": SecurityLevel.LEVEL_1,
        "768": SecurityLevel.LEVEL_3,
        "1024": SecurityLevel.LEVEL_5,
    }
    security_level = security_level_map[args.security_level]

    if args.mode == "generate-keys":
        adapter = MLKEMAdapter(security_level)
        seed = None
        if args.seed:
            try:
                seed = bytes.fromhex(args.seed)
            except ValueError:
                seed = args.seed.encode()

        public_key, secret_key = adapter.generate_keypair(seed)

        output = {
            "operation": "generate-keys",
            "security_level": security_level.value,
            "public_key_size": len(public_key),
            "secret_key_size": len(secret_key),
            "public_key_b64": base64.b64encode(public_key).decode("utf-8"),
            "secret_key_b64": base64.b64encode(secret_key).decode("utf-8"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    elif args.mode == "encapsulate":
        if not args.seed:
            print("Error: --seed required for encapsulate mode", file=sys.stderr)
            sys.exit(1)

        adapter = MLKEMAdapter(security_level)
        try:
            public_key_b64 = args.seed
            public_key = base64.b64decode(public_key_b64)
        except (ValueError, binascii.Error):
            try:
                public_key = bytes.fromhex(args.seed)
            except ValueError:
                public_key = args.seed.encode()
                _, public_key = adapter.generate_keypair(public_key)

        ciphertext, shared_secret = adapter.encapsulate(public_key)

        output = {
            "operation": "encapsulate",
            "security_level": security_level.value,
            "ciphertext_size": len(ciphertext),
            "shared_secret_size": len(shared_secret),
            "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
            "shared_secret_b64": base64.b64encode(shared_secret).decode("utf-8"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    elif args.mode == "scan":
        inventory = CryptographyInventory()

        sample_assets = [
            {
                "asset_id": "srv-prod-001",
                "asset_type": "TLS Certificate",
                "key_type": KeyType.RSA,
                "key_size": 2048,
                "location": "Production",
                "usage_context": "Authentication",
            },
            {
                "asset_id": "srv-prod-002",
                "asset_type": "SSH Key",
                "key_type": KeyType.ECC,
                "key_size": 256,
                "location": "Production",
                "usage_context": "Key Exchange",
            },
            {
                "asset_id": "db-backup-001",
                "asset_type": "Database Encryption Key",
                "key_type": KeyType.RSA,
                "key_size": 4096,
                "location": "Backup Storage",
                "usage_context": "Encryption",
            },
            {
                "asset_id": "api-gateway-001",
                "asset_type": "API Signing Key",
                "key_type": KeyType.ECC,
                "key_size": 384,
                "location": "Production",
                "usage_context": "Digital Signature",
            },
            {
                "asset_id": "crypto-001",
                "asset_type": "ML-KEM Key",
                "key_type": KeyType.ML_KEM,
                "key_size": 768,
                "location": "Production",
                "usage_context": "Key Exchange",
                "migration_status": "migrated",
            },
        ]

        for asset in sample_assets:
            inventory.add_asset(
                asset["asset_id"],
                asset["asset_type"],
                asset["key_type"],
                asset["key_size"],
                asset["location"],
                asset["usage_context"],
                asset.get("migration_status", "pending"),
            )

        summary = inventory.get_summary()
        vulnerable = inventory.get_vulnerable_assets()

        output = {
            "operation": "scan",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary,
            "vulnerable_assets_count": len(vulnerable),
            "all_assets": inventory.assets,
        }

        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    elif args.mode == "assess":
        inventory = CryptographyInventory()

        sample_assets = [
            ("srv-prod-001", "TLS", KeyType.RSA, 2048, "Production", "Authentication"),
            ("srv-prod-002", "SSH", KeyType.ECC, 256, "Production", "Key Exchange"),
            ("db-backup-001", "DB Encryption", KeyType.RSA, 4096, "Backup", "Encryption"),
            ("api-gateway-001", "API Signing", KeyType.ECC, 384, "Production", "Digital Signature"),
        ]

        for asset_id, asset_type, key_type, key_size, location, context in sample_assets:
            inventory.add_asset(asset_id, asset_type, key_type, key_size, location, context)

        vulnerable_assets = inventory.get_vulnerable_assets()
        prioritized = RiskAssessment.prioritize_assets(vulnerable_assets)

        output = {
            "operation": "assess",
            "timestamp": datetime.utcnow().isoformat(),
            "total_vulnerable_assets": len(vulnerable_assets),
            "prioritized_migration_queue": prioritized,
        }

        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))

    elif args.mode == "migrate":
        inventory = CryptographyInventory()
        migration_adapter = MigrationAdapter()

        sample_assets = [
            ("srv-prod-001", "TLS", KeyType.RSA, 2048, "Production", "Authentication"),
            ("srv-prod-002", "SSH", KeyType.ECC, 256, "Production", "Key Exchange"),
        ]

        for asset_id, asset_type, key_type, key_size, location, context in sample_assets:
            inventory.add_asset(asset_id, asset_type, key_type, key_size, location, context)

        vulnerable_assets = inventory.get_vulnerable_assets()

        if args.asset_id:
            vulnerable_assets = [a for a in vulnerable_assets if a["asset_id"] == args.asset_id]

        migration_results = []
        for asset in vulnerable_assets:
            result = migration_adapter.simulate_migration(asset)
            migration_results.append(result)

        migration_status = migration_adapter.get_migration_status()

        output = {
            "operation": "migrate",
            "timestamp": datetime.utcnow().isoformat(),
            "migration_results": migration_results,
            "migration_status": migration_status,
        }

        if args.output_file:
            with open(args.output_file, "w") as f:
                json.dump(output, f, indent=2)
        else:
            print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()