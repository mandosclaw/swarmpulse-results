#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Crypto inventory scanner
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @quinn
# Date:    2026-03-28T22:01:26.587Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Quantum-Safe Cryptography Migration - Crypto Inventory Scanner
Mission: NIST PQC Standardization Response
Agent: @quinn (SwarmPulse)
Date: 2024

Static analysis across codebases to identify RSA/ECC/DH usage with file:line locations.
Scans Python, JavaScript, Java, Go, C/C++ files for vulnerable crypto patterns.
Outputs structured inventory with migration priority recommendations.
"""

import os
import re
import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class CryptoFinding:
    """Represents a single cryptographic usage finding."""
    file_path: str
    line_number: int
    crypto_type: str
    algorithm: str
    pattern_matched: str
    severity: str
    context: str
    language: str


class CryptoInventoryScanner:
    """
    Scans codebases for RSA, ECC, and DH cryptographic usage patterns.
    Identifies vulnerable legacy crypto implementations requiring migration to NIST PQC.
    """

    # Pattern definitions for various languages and frameworks
    PATTERNS = {
        # Python patterns
        'python': {
            'rsa': [
                r'RSA\.generate\(',
                r'from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+rsa',
                r'from\s+Crypto\.PublicKey\s+import\s+RSA',
                r'RSA\.construct\(',
                r'rsa\.generate_private_key\(',
                r'rsa\.RSAPublicNumbers',
                r'rsa\.RSAPrivateNumbers',
            ],
            'ecc': [
                r'ec\.generate_private_key\(',
                r'from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+ec',
                r'from\s+ecdsa\s+import',
                r'ecdsa\.SigningKey',
                r'ecdsa\.VerifyingKey',
                r'SECP256R1|SECP384R1|SECP521R1|SECT163K1',
                r'ec\.EllipticCurve\(',
            ],
            'dh': [
                r'dh\.generate_parameters\(',
                r'from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+dh',
                r'DHParameterNumbers',
                r'DHPublicNumbers',
                r'DHPrivateNumbers',
            ],
        },
        # JavaScript/TypeScript patterns
        'javascript': {
            'rsa': [
                r'require\(["\']rsa["\']',
                r'require\(["\']node-rsa["\']',
                r'crypto\.generateKeyPairSync\(["\']rsa["\']',
                r'crypto\.generateKeyPair\(["\']rsa["\']',
                r'RSAKey\(',
                r'new\s+RSA\(',
            ],
            'ecc': [
                r'crypto\.generateKeyPairSync\(["\']ec["\']',
                r'crypto\.generateKeyPair\(["\']ec["\']',
                r'require\(["\']elliptic["\']',
                r'ecdsa\.sign\(',
                r'secp256k1|secp256r1|secp384r1|secp521r1',
            ],
            'dh': [
                r'crypto\.generateKeyPairSync\(["\']dh["\']',
                r'crypto\.generateKeyPair\(["\']dh["\']',
                r'crypto\.createDiffieHellman\(',
                r'DiffieHellman',
            ],
        },
        # Java patterns
        'java': {
            'rsa': [
                r'KeyPairGenerator\.getInstance\(["\']RSA["\']',
                r'RSAPublicKey|RSAPrivateKey',
                r'sun\.security\.rsa\.',
                r'org\.bouncycastle\.crypto\.generators\.RSA',
                r'new\s+RSAEngine\(',
            ],
            'ecc': [
                r'KeyPairGenerator\.getInstance\(["\']EC["\']',
                r'ECPublicKey|ECPrivateKey',
                r'org\.bouncycastle\.jce\.provider\.JCEECPublicKey',
                r'ECGenParameterSpec',
                r'secp256r1|secp384r1|secp521r1',
            ],
            'dh': [
                r'KeyPairGenerator\.getInstance\(["\']DH["\']',
                r'DHParameterSpec|DHPublicKey|DHPrivateKey',
                r'javax\.crypto\.spec\.DHParameterSpec',
            ],
        },
        # Go patterns
        'go': {
            'rsa': [
                r'rsa\.GenerateKey\(',
                r'crypto/rsa',
                r'rsa\.PublicKey',
                r'rsa\.PrivateKey',
                r'rsa\.SignPKCS1v15\(',
                r'rsa\.EncryptPKCS1v15\(',
            ],
            'ecc': [
                r'ecdsa\.GenerateKey\(',
                r'crypto/ecdsa',
                r'elliptic\.P256|elliptic\.P384|elliptic\.P521',
                r'ecdsa\.Sign\(',
                r'ecdsa\.Verify\(',
            ],
            'dh': [
                r'dh\.GenerateParameters\(',
                r'crypto/dh',
                r'dh\.PrivateKey|dh\.PublicKey',
            ],
        },
        # C/C++ patterns
        'c': {
            'rsa': [
                r'RSA_new\(',
                r'RSA_generate_key',
                r'RSA_public_encrypt|RSA_private_decrypt',
                r'EVP_PKEY_RSA',
                r'#include\s+<openssl/rsa\.h>',
            ],
            'ecc': [
                r'EC_KEY_new\(',
                r'EC_KEY_generate_key\(',
                r'ECDSA_sign|ECDSA_verify',
                r'NID_secp256k1|NID_secp384r1|NID_secp521r1',
                r'#include\s+<openssl/ec\.h>',
            ],
            'dh': [
                r'DH_new\(',
                r'DH_generate_parameters',
                r'DH_compute_key\(',
                r'#include\s+<openssl/dh\.h>',
            ],
        },
    }

    # File extensions for each language
    LANGUAGE_EXTENSIONS = {
        'python': {'.py', '.pyw'},
        'javascript': {'.js', '.ts', '.jsx', '.tsx'},
        'java': {'.java'},
        'go': {'.go'},
        'c': {'.c', '.cpp', '.cc', '.cxx', '.h', '.hpp'},
    }

    SEVERITY_MAP = {
        'rsa': 'high',
        'ecc': 'high',
        'dh': 'medium',
    }

    def __init__(self, exclude_dirs: Set[str] = None, max_file_size: int = 5_000_000):
        """Initialize scanner with configuration."""
        self.exclude_dirs = exclude_dirs or {
            '.git', '.venv', 'venv', 'node_modules', '.pytest_cache',
            '.tox', 'build', 'dist', '__pycache__', '.egg-info'
        }
        self.max_file_size = max_file_size
        self.findings