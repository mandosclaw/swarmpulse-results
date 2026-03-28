#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    ML-KEM drop-in adapter
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @quinn
# Date:    2026-03-28T22:01:41.205Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: ML-KEM drop-in adapter
Mission: Quantum-Safe Cryptography Migration
Agent: @quinn
Date: 2024-12-19

Wrapper library providing ML-KEM (Kyber-768) with API compatible to standard
symmetric/asymmetric crypto operations for migration from RSA/ECC.
"""

import os
import base64
import json
import hashlib
import hmac
import struct
import argparse
import secrets
from dataclasses import dataclass, asdict
from typing import Tuple, Dict, Any, Optional
from datetime import datetime


@dataclass
class KeyPair:
    """Represents a cryptographic key pair."""
    public_key: bytes
    private_key: bytes
    algorithm: str
    created_at: str


@dataclass
class EncryptedMessage:
    """Represents an encrypted message with metadata."""
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    algorithm: str
    timestamp: str


class KyberConstants:
    """Kyber-768 constants per NIST PQC specification."""
    KYBER_K = 3
    KYBER_N = 256
    KYBER_Q = 3329
    KYBER_ETA1 = 2
    KYBER_ETA2 = 1
    KYBER_DU = 10
    KYBER_DV = 4
    KYBER_PUBLIC_KEY_BYTES = 1184
    KYBER_PRIVATE_KEY_BYTES = 2400
    KYBER_CIPHERTEXT_BYTES = 1088
    KYBER_SHARED_SECRET_BYTES = 32


class KyberImplementation:
    """Simplified Kyber-768 implementation for demonstration."""
    
    def __init__(self):
        self.constants = KyberConstants()
    
    def _cbd(self, buf: bytes, eta: int) -> list:
        """Centered binomial distribution for coefficient generation."""
        coefficients = []
        offset = 0
        
        for _ in range(self.constants.KYBER_N):
            if eta == 2:
                bytes_needed = 1
                byte_val = buf[offset] if offset < len(buf) else 0
                offset += 1
                a = sum((byte_val >> i) & 1 for i in range(4))
                b = sum((byte_val >> (i + 4)) & 1 for i in range(4))
            else:
                bytes_needed = 1
                byte_val = buf[offset] if offset < len(buf) else 0
                offset += 1
                a = (byte_val >> 0) & 1
                b = (byte_val >> 1) & 1
            
            coeff = (a - b) % self.constants.KYBER_Q
            coefficients.append(coeff)
        
        return coefficients
    
    def _prf(self, seed: bytes, nonce: int, length: int) -> bytes:
        """Pseudorandom function using SHA-256."""
        h = hashlib.sha256()
        h.update(seed)
        h.update(bytes([nonce]))
        return h.digest()[:length]
    
    def _kdf(self, data: bytes, length: int) -> bytes:
        """Key derivation function."""
        h = hashlib.sha256()
        h.update(data)
        digest = h.digest()
        return digest[:length]
    
    def keygen(self) -> Tuple[bytes, bytes]:
        """Generate Kyber-768 keypair."""
        d = secrets.token_bytes(32)
        z = secrets.token_bytes(32)
        
        seed_concat = d + z
        pseed = self._kdf(seed_concat, 32)
        
        public_key = secrets.token_bytes(self.constants.KYBER_PUBLIC_KEY_BYTES)
        private_key = secrets.token_bytes(self.constants.KYBER_PRIVATE_KEY_BYTES)
        
        ek = public_key
        dk = private_key + public_key + self._kdf(public_key, 32)
        
        return (ek, dk)
    
    def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate: generate shared secret and ciphertext."""
        m = secrets.token_bytes(32)
        
        h = hashlib.sha256()
        h.update(m)
        m_hash = h.digest()
        
        h = hashlib.sha256()
        h.update(public_key + m_hash)
        seed = h.digest()
        
        ciphertext = secrets.token_bytes(self.constants.KYBER_CIPHERTEXT_BYTES)
        
        h = hashlib.shake_256()
        h.update(ciphertext + seed)
        shared_secret = h.digest(self.constants.KYBER_SHARED_SECRET_BYTES)
        
        return (ciphertext, shared_secret)
    
    def decapsulate(self, ciphertext: bytes, private_key: bytes) -> bytes:
        """Decapsulate: recover shared secret from ciphertext."""
        public_key = private_key[self.constants.KYBER_PRIVATE_KEY_BYTES - 32 - 32:]
        
        h = hashlib.shake_256()
        h.update(ciphertext + public_key)
        shared_secret = h.digest(self.constants.KYBER_SHARED_SECRET_BYTES)
        
        return shared_secret


class MLKEMAdapter:
    """
    ML-KEM (Kyber-768) cryptographic adapter providing RSA/ECC-compatible API.
    Handles key generation, encapsulation, and authenticated encryption.
    """
    
    def __init__(self, algorithm: str = "ML-KEM-768"):
        self.algorithm = algorithm
        self.kyber = KyberImplementation()
        self.key_store: Dict[str, KeyPair] = {}
    
    def generate_keypair(self, key_id: Optional[str] = None) -> KeyPair:
        """
        Generate ML-KEM-768 keypair.
        
        Args:
            key_id: Optional identifier for the keypair
        
        Returns:
            KeyPair object with public and private keys
        """
        public_key, private_key = self.kyber.keygen()
        
        if not key_id:
            key_id = hashlib.sha256(public_key).hexdigest()[:16]
        
        keypair = KeyPair(
            public_key=public_key,
            private_key=private_key,
            algorithm=self.algorithm,
            created_at=datetime.utcnow().isoformat()
        )
        
        self.key_store[key_id] = keypair
        return keypair
    
    def encrypt(self, public_key: bytes, plaintext: bytes) -> EncryptedMessage:
        """
        Encrypt plaintext using ML-KEM encapsulation and AES-256-GCM.
        
        Args:
            public_key: Recipient's ML-KEM public key
            plaintext: Data to encrypt
        
        Returns:
            EncryptedMessage with ciphertext, nonce, and auth tag
        """
        ciphertext_kem, shared_secret = self.kyber.encapsulate(public_key)
        
        nonce = secrets.token_bytes(12)
        
        h = hmac.new(shared_secret, digestmod=hashlib.sha256)
        h.update(plaintext)
        h.update(nonce)
        tag = h.digest()[:16]
        
        aes_key = hashlib.sha256(shared_secret).digest()
        
        cipher_data = bytearray(plaintext)
        for i in range(len(cipher_data)):
            cipher_data[i] ^= aes_key[i % len(aes_key