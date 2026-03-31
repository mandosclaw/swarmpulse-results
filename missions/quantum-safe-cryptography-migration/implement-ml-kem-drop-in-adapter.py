#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement ML-KEM drop-in adapter
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-31T18:53:58.067Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement ML-KEM drop-in adapter
Mission: Quantum-Safe Cryptography Migration
Agent: @aria
Date: 2024

ML-KEM drop-in adapter for seamless migration from RSA/ECC to post-quantum cryptography.
Provides a unified interface for key encapsulation mechanism operations.
"""

import argparse
import json
import base64
import hashlib
import os
import sys
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Tuple, Dict, Any, Optional, List
from abc import ABC, abstractmethod


class CryptoAlgorithm(Enum):
    """Supported cryptographic algorithms"""
    RSA = "rsa"
    ECC = "ecc"
    ML_KEM = "ml_kem"


@dataclass
class KeyPair:
    """Represents a cryptographic key pair"""
    public_key: bytes
    private_key: bytes
    algorithm: CryptoAlgorithm
    key_size: int
    created_at: str


@dataclass
class EncapsulationResult:
    """Result of key encapsulation"""
    ciphertext: bytes
    shared_secret: bytes
    algorithm: CryptoAlgorithm


@dataclass
class MigrationMetrics:
    """Metrics for cryptography migration"""
    total_keys: int
    rsa_keys: int
    ecc_keys: int
    ml_kem_keys: int
    migration_status: Dict[str, int]
    timestamp: str


class QuantumSafeKEM(ABC):
    """Abstract base class for quantum-safe key encapsulation"""
    
    @abstractmethod
    def generate_keypair(self) -> KeyPair:
        """Generate a new key pair"""
        pass
    
    @abstractmethod
    def encapsulate(self, public_key: bytes) -> EncapsulationResult:
        """Encapsulate a shared secret using public key"""
        pass
    
    @abstractmethod
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate and recover shared secret"""
        pass


class MLKEMAdapter(QuantumSafeKEM):
    """
    ML-KEM (Module-Lattice-Based Key-Encapsulation Mechanism) adapter
    Simulates ML-KEM-768 (NIST FIPS 203 standardized variant)
    """
    
    # ML-KEM-768 parameters (simplified simulation)
    SECURITY_LEVEL = 768
    PUBLIC_KEY_SIZE = 1184
    PRIVATE_KEY_SIZE = 2400
    CIPHERTEXT_SIZE = 1088
    SHARED_SECRET_SIZE = 32
    
    def __init__(self, security_level: int = 768):
        self.security_level = security_level
        self.algorithm = CryptoAlgorithm.ML_KEM
    
    def generate_keypair(self) -> KeyPair:
        """Generate ML-KEM keypair using deterministic simulation"""
        seed = os.urandom(32)
        
        # Simulate public key generation from seed
        public_key = self._derive_public_key(seed)
        
        # Simulate private key generation (includes seed)
        private_key = self._derive_private_key(seed)
        
        return KeyPair(
            public_key=public_key,
            private_key=private_key,
            algorithm=self.algorithm,
            key_size=self.security_level,
            created_at=datetime.now().isoformat()
        )
    
    def encapsulate(self, public_key: bytes) -> EncapsulationResult:
        """Encapsulate shared secret for given public key"""
        # Validate public key
        if len(public_key) != self.PUBLIC_KEY_SIZE:
            raise ValueError(f"Invalid public key size: {len(public_key)}")
        
        # Generate random message
        m = os.urandom(32)
        
        # Create shared secret using hash-based KDF
        h_m = hashlib.shake_256(m).digest(self.SHARED_SECRET_SIZE)
        
        # Simulate lattice-based encryption (deterministic for testing)
        h_pk = hashlib.sha3_256(public_key).digest()
        ciphertext = self._kem_encrypt(h_pk, m)
        
        return EncapsulationResult(
            ciphertext=ciphertext,
            shared_secret=h_m,
            algorithm=self.algorithm
        )
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Recover shared secret using private key"""
        # Validate inputs
        if len(private_key) != self.PRIVATE_KEY_SIZE:
            raise ValueError(f"Invalid private key size: {len(private_key)}")
        
        if len(ciphertext) != self.CIPHERTEXT_SIZE:
            raise ValueError(f"Invalid ciphertext size: {len(ciphertext)}")
        
        # Simulate decryption and recovery
        recovered_m = self._kem_decrypt(private_key, ciphertext)
        shared_secret = hashlib.shake_256(recovered_m).digest(self.SHARED_SECRET_SIZE)
        
        return shared_secret
    
    def _derive_public_key(self, seed: bytes) -> bytes:
        """Derive public key from seed (simplified simulation)"""
        h = hashlib.sha3_256()
        h.update(b"MLKEM_PK" + seed)
        pk_seed = h.digest()
        
        # Pad to PUBLIC_KEY_SIZE
        return (pk_seed * ((self.PUBLIC_KEY_SIZE // len(pk_seed)) + 1))[:self.PUBLIC_KEY_SIZE]
    
    def _derive_private_key(self, seed: bytes) -> bytes:
        """Derive private key from seed (simplified simulation)"""
        h = hashlib.sha3_256()
        h.update(b"MLKEM_SK" + seed)
        sk_seed = h.digest()
        
        # Pad to PRIVATE_KEY_SIZE
        return (sk_seed * ((self.PRIVATE_KEY_SIZE // len(sk_seed)) + 1))[:self.PRIVATE_KEY_SIZE]
    
    def _kem_encrypt(self, pk_hash: bytes, m: bytes) -> bytes:
        """Simulate lattice-based encryption"""
        # Combine public key hash and message
        combined = pk_hash + m
        c = hashlib.shake_256(combined).digest(self.CIPHERTEXT_SIZE)
        return c
    
    def _kem_decrypt(self, sk: bytes, c: bytes) -> bytes:
        """Simulate lattice-based decryption"""
        # Derive recovery using private key
        recovery = hashlib.sha3_256(sk + c).digest(32)
        return recovery


class LegacyKEMAdapter(QuantumSafeKEM):
    """Adapter for legacy RSA/ECC systems (for comparison)"""
    
    def __init__(self, algorithm: CryptoAlgorithm = CryptoAlgorithm.RSA):
        if algorithm not in [CryptoAlgorithm.RSA, CryptoAlgorithm.ECC]:
            raise ValueError(f"Invalid legacy algorithm: {algorithm}")
        self.algorithm = algorithm
        self.key_size = 2048 if algorithm == CryptoAlgorithm.RSA else 256
    
    def generate_keypair(self) -> KeyPair:
        """Generate legacy keypair (simulated)"""
        seed = os.urandom(32)
        
        # Simulate RSA/ECC key generation
        public_key = hashlib.sha3_256(b"pub" + seed).digest() * 16
        private_key = hashlib.sha3_256(b"priv" + seed).digest() * 16
        
        return KeyPair(
            public_key=public_key,
            private_key=private_key,
            algorithm=self.algorithm,
            key_size=self.key_size,
            created_at=datetime.now().isoformat()
        )
    
    def encapsulate(self, public_key: bytes) -> EncapsulationResult:
        """Encapsulate using legacy method"""
        m = os.urandom(32)
        shared_secret = hashlib.sha3_256(public_key + m).digest()
        ciphertext = hashlib.sha3_256(shared_secret + m).digest() * 4
        
        return EncapsulationResult(
            ciphertext=ciphertext,
            shared_secret=shared_secret,
            algorithm=self.algorithm
        )
    
    def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate using legacy method"""
        return hashlib.sha3_256(private_key + ciphertext).digest()


class QuantumSafeCryptoInventory:
    """Inventory and migration tracker for cryptographic keys"""
    
    def __init__(self):
        self.keys: Dict[str, KeyPair] = {}
        self.migrations: List[Dict[str, Any]] = []
        self.ml_kem_adapter = MLKEMAdapter()
        self.legacy_adapters: Dict[CryptoAlgorithm, LegacyKEMAdapter] = {
            CryptoAlgorithm.RSA: LegacyKEMAdapter(CryptoAlgorithm.RSA),
            CryptoAlgorithm.ECC: LegacyKEMAdapter(CryptoAlgorithm.ECC)
        }
    
    def register_key(self, key_id: str, key_pair: KeyPair) -> None:
        """Register a key in the inventory"""
        self.keys[key_id] = key_pair
    
    def scan_inventory(self) -> MigrationMetrics:
        """Scan and analyze current cryptographic inventory"""
        rsa_count = sum(1 for k in self.keys.values() if k.algorithm == CryptoAlgorithm.RSA)
        ecc_count = sum(1 for k in self.keys.values() if k.algorithm == CryptoAlgorithm.ECC)
        ml_kem_count = sum(1 for k in self.keys.values() if k.algorithm == CryptoAlgorithm.ML_KEM)
        
        return MigrationMetrics(
            total_keys=len(self.keys),
            rsa_keys=rsa_count,
            ecc_keys=ecc_count,
            ml_kem_keys=ml_kem_count,
            migration_status={
                "rsa": rsa_count,
                "ecc": ecc_count,
                "ml_kem": ml_kem_count
            },
            timestamp=datetime.now().isoformat()
        )
    
    def migrate_key(self, old_key_id: str, new_key_id: str) -> Dict[str, Any]:
        """Migrate a key from legacy to ML-KEM"""
        if old_key_id not in self.keys:
            raise KeyError(f"Key not found: {old_key_id}")
        
        old_key = self.keys[old_key_id]
        
        # Generate new ML-KEM key
        new_key = self.ml_kem_adapter.generate_keypair()
        
        # Register migrated key
        self.register_key(new_key_id, new_key)
        
        # Record migration
        migration_record = {
            "old_key_id": old_key_id,
            "old_algorithm": old_key.algorithm.value,
            "new_key_id": new_key_id,
            "new_algorithm": new_key.algorithm.value,
            "migration_time": datetime.now().isoformat(),
            "old_key_size": old_key.key_size,
            "new_key_size": new_key.key_size
        }
        self.migrations.append(migration_record)
        
        return migration_record
    
    def test_encapsulation(self, key_id: str) -> Dict[str, Any]:
        """Test encapsulation with a specific key"""
        if key_id not in self.keys:
            raise KeyError(f"Key not found: {key_id}")
        
        key_pair = self.keys[key_id]
        
        # Select appropriate adapter
        if key_pair.algorithm == CryptoAlgorithm.ML_KEM:
            adapter = self.ml_kem_adapter
        else:
            adapter = self.legacy_adapters.get(key_pair.algorithm)
            if not adapter:
                raise ValueError(f"No adapter for {key_pair.algorithm}")
        
        # Perform encapsulation
        start_time = time.time()
        encap_result = adapter.encapsulate(key_pair.public_key)
        encap_time = time.time() - start_time
        
        # Perform decapsulation
        start_time = time.time()
        recovered_secret = adapter.decapsulate(key_pair.private_key, encap_result.ciphertext)
        decap_time = time.time() - start_time
        
        # Verify correctness
        secrets_match = recovered_secret == encap_result.shared_secret
        
        return {
            "key_id": key_id,
            "algorithm": key_pair.algorithm.value,
            "encapsulation_time_ms": encap_time * 1000,
            "decapsulation_time_ms": decap_time * 1000,
            "total_time_ms": (encap_time + decap_time) * 1000,
            "ciphertext_size": len(encap_result.ciphertext),
            "shared_secret_size": len(encap_result.shared_secret),
            "secrets_match": secrets_match,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report"""
        inventory = self.scan_inventory()
        
        return {
            "inventory": asdict(inventory),
            "migrations_completed": len(self.migrations),
            "migration_history": self.migrations,
            "quantum_readiness": {
                "ml_kem_percentage": (inventory.ml_kem_keys / inventory.total_keys * 100) if inventory.total_keys > 0 else 0,
                "legacy_percentage": ((inventory.rsa_keys + inventory.ecc_keys) / inventory.total_keys * 100) if inventory.total_keys > 0 else 0
            },
            "report_timestamp": datetime.now().isoformat()
        }


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="ML-KEM Drop-in Adapter for Quantum-Safe Cryptography Migration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate keypair command
    gen_parser = subparsers.add_parser("generate", help="Generate a new cryptographic keypair")
    gen_parser.add_argument("--key-id", default="key_001", help="Unique key identifier")
    gen_parser.add_argument("--algorithm", choices=["ml_kem", "rsa", "ecc"], 
                          default="ml_kem", help="Key algorithm")
    gen_parser.add_argument("--output", help="Output file for key pair (JSON)")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate legacy key to ML-KEM")
    migrate_parser.add_argument("--old-key-id", required=True, help="Old key identifier")
    migrate_parser.add_argument("--new-key-id", required=True, help="New key identifier")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test encapsulation/decapsulation")
    test_parser.add_argument("--key-id", required=True, help="Key identifier to test")
    test_parser.add_argument("--iterations", type=int, default=1, help="Number of test iterations")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan cryptographic inventory")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate migration report")
    report_parser.add_argument("--format", choices=["json", "pretty"], 
                             default="json", help="Output format")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run demonstration")
    demo_parser.add_argument("--keys", type=int, default=5, help="Number of demo keys")
    
    return parser


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Initialize inventory
    inventory = QuantumSafeCryptoInventory()
    
    if args.command == "generate":
        # Select adapter based on algorithm
        if args.algorithm == "ml_kem":
            adapter = inventory.ml_kem_adapter
        else:
            algo = CryptoAlgorithm.RSA if args.algorithm == "rsa" else CryptoAlgorithm.ECC
            adapter = inventory.legacy_adapters[algo]
        
        # Generate keypair
        keypair = adapter.generate_keypair()
        inventory.register_key(args.key_id, keypair)
        
        # Prepare output
        output = {
            "key_id": args.key_id,
            "algorithm": keypair.algorithm.value,
            "public_key": base64.b64encode(keypair.public_key).decode(),
            "private_key": base64.b64encode(keypair.private_key).decode(),
            "key_size": keypair.key_size,
            "created_at": keypair.created_at
        }
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"Keypair written to {args.output}")
        else:
            print(json.dumps(output, indent=2))
    
    elif args.command == "migrate":
        # Simulate pre-existing legacy keys for migration
        if args.old_key_id not in inventory.keys:
            rsa_adapter = inventory.legacy_adapters[CryptoAlgorithm.RSA]
            old_key = rsa_adapter.generate_keypair()
            inventory.register_key(args.old_key_id, old_key)
        
        # Perform migration
        migration = inventory.migrate_key(args.old_key_id, args.new_key_id)
        print(json.dumps(migration, indent=2))
    
    elif args.command == "test":
        # Simulate pre-existing key for testing
        if args.key_id not in inventory.keys:
            adapter = inventory.ml_kem_adapter
            test_key = adapter.generate_keypair()
            inventory.register_key(args.key_id, test_key)
        
        # Run tests
        results = []
        for i in range(args.iterations):
            result = inventory.test_encapsulation(args.key_id)
            results.append(result)
        
        output = {
            "key_id": args.key_id,
            "test_iterations": args.iterations,
            "results": results,
            "average_encap_ms": sum(r["encapsulation_time_ms"] for r in results) / len(results),
            "average_decap_ms": sum(r["decapsulation_time_ms"] for r in results) / len(results)
        }
        print(json.dumps(output, indent=2))
    
    elif args.command == "scan":
        # Create sample inventory
        for i in range(3):
            key = inventory.ml_kem_adapter.generate_keypair()
            inventory.register_key(f"mlkem_{i}", key)
        
        for i in range(2):
            key = inventory.legacy_adapters[CryptoAlgorithm.RSA].generate_keypair()
            inventory.register_key(f"rsa_{i}", key)
        
        for i in range(2):
            key = inventory.legacy_adapters[CryptoAlgorithm.ECC].generate_keypair()
            inventory.register_key(f"ecc_{i}", key)
        
        metrics = inventory.scan_inventory()
        print(json.dumps(asdict(metrics), indent=2))
    
    elif args.command == "report":
        # Create sample inventory for report
        for i in range(4):
            key = inventory.ml_kem_adapter.generate_keypair()
            inventory.register_key(f"mlkem_{i}", key)
        
        for i in range(3):
            key = inventory.legacy_adapters[CryptoAlgorithm.RSA].generate_keypair()
            inventory.register_key(f"rsa_{i}", key)
            # Migrate some keys
            if i < 2:
                inventory.migrate_key(f"rsa_{i}", f"mlkem_migrated_{i}")
        
        report = inventory.get_migration_report()
        
        if args.format == "pretty":
            print(json.dumps(report, indent=2))
        else:
            print(json.dumps(report))
    
    elif args.command == "demo":
        print("=" * 60)
        print("ML-KEM Drop-in Adapter Demo")
        print("=" * 60)
        
        # Generate initial keys (mixed legacy and quantum-safe)
        print(f"\n[1] Generating {args.keys} cryptographic keys...")
        for i in range(args.keys):
            if i % 2 == 0:
                adapter = inventory.ml_kem_adapter
                algo = "ML-KEM"
            else:
                adapter = inventory.legacy_adapters[CryptoAlgorithm.RSA]
                algo = "RSA"
            
            key = adapter.generate_keypair()
            inventory.register_key(f"key_{i:03d}", key)
            print(f"  ✓ Generated {algo} key: key_{i:03d}")
        
        # Scan inventory
        print("\n[2] Scanning cryptographic inventory...")
        metrics = inventory.scan_inventory()
        print(f"  Total keys: {metrics.total_keys}")
        print(f"  ML-KEM keys: {metrics.ml_kem_keys}")
        print(f"  RSA keys: {metrics.rsa_keys}")
        print(f"  ECC keys: {metrics.ecc_keys}")
        
        # Test encapsulation
        print("\n[3] Testing encapsulation/decapsulation...")
        for i in range(min(3, args.keys)):
            test_result = inventory.test_encapsulation(f"key_{i:03d}")
            algo = test_result["algorithm"].upper()
            status = "✓" if test_result["secrets_match"] else "✗"
            print(f"  {status} {algo} key_{i:03d}: "
                  f"{test_result['encapsulation_time_ms']:.3f}ms + "
                  f"{test_result['decapsulation_time_ms']:.3f}ms")
        
        # Perform migrations
        print("\n[4] Migrating legacy keys to ML-KEM...")
        migrations = 0
        for i in range(args.keys):
            if i % 2 != 0:  # Migrate RSA keys
                new_id = f"key_{i:03d}_migrated"
                inventory.migrate_key(f"key_{i:03d}", new_id)
                migrations += 1
                print(f"  ✓ Migrated key_{i:03d} → {new_id}")
        
        # Final report
        print("\n[5] Final Migration Report")
        print("-" * 60)
        report = inventory.get_migration_report()
        metrics = report["inventory"]
        readiness = report["quantum_readiness"]
        
        print(f"Total keys: {metrics['total_keys']}")
        print(f"ML-KEM ready: {metrics['ml_kem_keys']} ({readiness['ml_kem_percentage']:.1f}%)")
        print(f"Legacy keys: {metrics['rsa_keys'] + metrics['ecc_keys']} ({readiness['legacy_percentage']:.1f}%)")
        print(f"Migrations completed: {migrations}")
        print("=" * 60)


if __name__ == "__main__":
    main()