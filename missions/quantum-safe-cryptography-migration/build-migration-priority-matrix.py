#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build migration priority matrix
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @aria
# Date:    2026-03-29T13:22:13.844Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Build migration priority matrix
MISSION: Quantum-Safe Cryptography Migration
AGENT: @aria
DATE: 2025-01-24

End-to-end quantum cryptography migration toolkit: inventory scanning, risk prioritization,
and drop-in ML-KEM adapters for existing RSA/ECC infrastructure.

This module builds a migration priority matrix that assesses cryptographic systems
based on quantum threat exposure, business criticality, and migration feasibility.
"""

import json
import argparse
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Tuple
from datetime import datetime
from pathlib import Path


class CryptoAlgorithm(Enum):
    """Cryptographic algorithms categorized by quantum resistance."""
    RSA_2048 = "RSA-2048"
    RSA_3072 = "RSA-3072"
    RSA_4096 = "RSA-4096"
    ECC_P256 = "ECC-P256"
    ECC_P384 = "ECC-P384"
    ECC_P521 = "ECC-P521"
    ML_KEM_512 = "ML-KEM-512"
    ML_KEM_768 = "ML-KEM-768"
    ML_KEM_1024 = "ML-KEM-1024"
    CLASSIC_DES = "DES"
    CLASSIC_3DES = "3DES"
    AES_128 = "AES-128"
    AES_256 = "AES-256"
    SHA1 = "SHA-1"
    SHA256 = "SHA-256"
    SHA512 = "SHA-512"


class CriticalityLevel(Enum):
    """Business criticality levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


class QuantumThreatLevel(Enum):
    """Quantum threat assessment levels."""
    IMMEDIATE = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    MINIMAL = 1


@dataclass
class CryptoSystem:
    """Represents a cryptographic system in the inventory."""
    system_id: str
    name: str
    algorithm: CryptoAlgorithm
    deployment_date: str
    instance_count: int
    criticality: CriticalityLevel
    data_retention_years: int
    harvest_now_decrypt_later_risk: bool
    location: str
    owner_team: str


@dataclass
class QuantumThreatAssessment:
    """Quantum threat assessment for an algorithm."""
    algorithm: CryptoAlgorithm
    threat_level: QuantumThreatLevel
    nist_status: str
    migration_urgency: int
    estimated_quantum_break_years: int
    recommended_replacement: CryptoAlgorithm


@dataclass
class MigrationScore:
    """Migration priority score for a system."""
    system_id: str
    system_name: str
    quantum_threat_score: float
    business_impact_score: float
    migration_feasibility_score: float
    overall_priority_score: float
    priority_rank: int
    recommended_action: str
    target_algorithm: CryptoAlgorithm
    estimated_effort_months: float


class QuantumThreatDatabase:
    """Database of quantum threat assessments for various algorithms."""

    def __init__(self):
        self.assessments: Dict[CryptoAlgorithm, QuantumThreatAssessment] = {
            CryptoAlgorithm.RSA_2048: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.RSA_2048,
                threat_level=QuantumThreatLevel.IMMEDIATE,
                nist_status="NOT_RECOMMENDED",
                migration_urgency=5,
                estimated_quantum_break_years=10,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
            CryptoAlgorithm.RSA_3072: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.RSA_3072,
                threat_level=QuantumThreatLevel.HIGH,
                nist_status="ACCEPTABLE_LEGACY",
                migration_urgency=4,
                estimated_quantum_break_years=15,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
            CryptoAlgorithm.RSA_4096: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.RSA_4096,
                threat_level=QuantumThreatLevel.MEDIUM,
                nist_status="ACCEPTABLE_LEGACY",
                migration_urgency=3,
                estimated_quantum_break_years=20,
                recommended_replacement=CryptoAlgorithm.ML_KEM_1024,
            ),
            CryptoAlgorithm.ECC_P256: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ECC_P256,
                threat_level=QuantumThreatLevel.IMMEDIATE,
                nist_status="NOT_RECOMMENDED",
                migration_urgency=5,
                estimated_quantum_break_years=10,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
            CryptoAlgorithm.ECC_P384: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ECC_P384,
                threat_level=QuantumThreatLevel.HIGH,
                nist_status="ACCEPTABLE_LEGACY",
                migration_urgency=4,
                estimated_quantum_break_years=15,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
            CryptoAlgorithm.ECC_P521: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ECC_P521,
                threat_level=QuantumThreatLevel.MEDIUM,
                nist_status="ACCEPTABLE_LEGACY",
                migration_urgency=3,
                estimated_quantum_break_years=20,
                recommended_replacement=CryptoAlgorithm.ML_KEM_1024,
            ),
            CryptoAlgorithm.ML_KEM_512: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ML_KEM_512,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.ML_KEM_512,
            ),
            CryptoAlgorithm.ML_KEM_768: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ML_KEM_768,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
            CryptoAlgorithm.ML_KEM_1024: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.ML_KEM_1024,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.ML_KEM_1024,
            ),
            CryptoAlgorithm.CLASSIC_DES: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.CLASSIC_DES,
                threat_level=QuantumThreatLevel.IMMEDIATE,
                nist_status="NOT_RECOMMENDED",
                migration_urgency=5,
                estimated_quantum_break_years=5,
                recommended_replacement=CryptoAlgorithm.AES_256,
            ),
            CryptoAlgorithm.CLASSIC_3DES: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.CLASSIC_3DES,
                threat_level=QuantumThreatLevel.HIGH,
                nist_status="NOT_RECOMMENDED",
                migration_urgency=5,
                estimated_quantum_break_years=8,
                recommended_replacement=CryptoAlgorithm.AES_256,
            ),
            CryptoAlgorithm.AES_128: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.AES_128,
                threat_level=QuantumThreatLevel.LOW,
                nist_status="RECOMMENDED_APPROVED",
                migration_urgency=2,
                estimated_quantum_break_years=1000,
                recommended_replacement=CryptoAlgorithm.AES_256,
            ),
            CryptoAlgorithm.AES_256: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.AES_256,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.AES_256,
            ),
            CryptoAlgorithm.SHA1: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.SHA1,
                threat_level=QuantumThreatLevel.HIGH,
                nist_status="DEPRECATED",
                migration_urgency=4,
                estimated_quantum_break_years=12,
                recommended_replacement=CryptoAlgorithm.SHA256,
            ),
            CryptoAlgorithm.SHA256: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.SHA256,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.SHA256,
            ),
            CryptoAlgorithm.SHA512: QuantumThreatAssessment(
                algorithm=CryptoAlgorithm.SHA512,
                threat_level=QuantumThreatLevel.MINIMAL,
                nist_status="RECOMMENDED",
                migration_urgency=1,
                estimated_quantum_break_years=10000,
                recommended_replacement=CryptoAlgorithm.SHA512,
            ),
        }

    def get_threat_assessment(self, algorithm: CryptoAlgorithm) -> QuantumThreatAssessment:
        """Get threat assessment for an algorithm."""
        return self.assessments.get(
            algorithm,
            QuantumThreatAssessment(
                algorithm=algorithm,
                threat_level=QuantumThreatLevel.MEDIUM,
                nist_status="UNKNOWN",
                migration_urgency=3,
                estimated_quantum_break_years=15,
                recommended_replacement=CryptoAlgorithm.ML_KEM_768,
            ),
        )


class MigrationPriorityMatrix:
    """Builds and manages migration priority matrix for quantum-safe cryptography."""

    def __init__(self, threat_db: QuantumThreatDatabase = None):
        self.threat_db = threat_db or QuantumThreatDatabase()
        self.systems: List[CryptoSystem] = []
        self.scores: List[MigrationScore] = []

    def add_system(self, system: CryptoSystem) -> None:
        """Add a cryptographic system to inventory."""
        self.systems.append(system)

    def add_systems_batch(self, systems: List[CryptoSystem]) -> None:
        """Add multiple systems to inventory."""
        self.systems.extend(systems)

    def calculate_quantum_threat_score(self, system: CryptoSystem) -> float:
        """
        Calculate quantum threat score (0-100) based on:
        - Algorithm quantum resistance
        - Harvest-now-decrypt-later risk
        - Data retention period
        """
        assessment = self.threat_db.get_threat_assessment(system.algorithm)

        base_threat = assessment.threat_level.value * 20

        hndl_multiplier = 1.5 if system.harvest_now_decrypt_later_risk else 1.0

        retention_bonus = min(system.data_retention_years * 3, 30)

        total_score = (base_threat + retention_bonus) * hndl_multiplier
        return min(total_score, 100.0)

    def calculate_business_impact_score(self, system: CryptoSystem) -> float:
        """
        Calculate business impact score (0-100) based on:
        - System criticality
        - Instance count
        - Deployment scope
        """
        criticality_score = system.criticality.value * 20

        instance_impact = min(system.instance_count * 2, 20)

        total_score = criticality_score + instance_impact
        return min(total_score, 100.0)

    def calculate_migration_feasibility_score(self, system: CryptoSystem) -> float:
        """
        Calculate migration feasibility score (0-100) where higher is easier.
        Based on:
        - Algorithm type (symmetric easier than asymmetric)
        - Instance count (fewer is easier)
        - Time since deployment (older systems may have legacy code)
        """
        algorithm_str = system.algorithm.value.lower()

        if "aes" in algorithm_str or "sha" in algorithm_str:
            algo_feasibility = 80
        elif "ml-kem" in algorithm_str:
            algo_feasibility = 70
        elif "ecc" in algorithm_str:
            algo_feasibility = 50
        elif "rsa" in algorithm_str:
            algo_feasibility = 45
        else:
            algo_feasibility = 30

        instance_penalty = min(system.instance_count * 5, 40)
        feasibility_score = algo_feasibility - instance_penalty

        return max(min(feasibility_score, 100.0), 10.0)

    def estimate_migration_effort(self, system: CryptoSystem, feasibility_score: float) -> float:
        """Estimate migration effort in months."""
        base_effort = 100 - feasibility_score

        instance_factor = 0.1 * system.instance_count
        complexity_factor = 0.5 if system.criticality == CriticalityLevel.CRITICAL else 0.2

        total_effort = (base_effort / 20.0) + instance_factor + complexity_factor
        return max(total_effort, 0.5)

    def calculate_overall_priority_score(
        self,
        quantum_threat: float,
        business_impact: float,
        feasibility: float,
    ) -> float:
        """
        Calculate weighted overall priority score.
        Higher score = higher priority for migration.
        """
        weights = {
            "quantum_threat": 0.50,
            "business_impact": 0.30,
            "feasibility": 0.20,
        }

        overall = (
            quantum_threat * weights["quantum_threat"]
            + business_impact * weights["business_impact"]
            + (100 - feasibility) * weights["feasibility"]
        )

        return overall

    def determine_recommended_action(self, overall_score: float) -> str:
        """Determine recommended action based on priority score."""
        if overall_score >= 75:
            return "IMMEDIATE_MIGRATION"
        elif overall_score >= 60:
            return "URGENT_MIGRATION_PLAN"
        elif overall_score >= 45:
            return "PLANNED_MIGRATION"
        elif overall_score >= 30:
            return "MONITOR_AND_PLAN"
        else:
            return