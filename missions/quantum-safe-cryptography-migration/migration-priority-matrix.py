#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Migration priority matrix
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @quinn
# Date:    2026-03-23T22:21:16.431Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Migration priority matrix — scores crypto usages by exploitability, data sensitivity, and replacement complexity."""
import argparse, json, logging
from dataclasses import dataclass, field
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

EXPLOIT_SCORE = {"MD5": 10, "SHA1": 9, "DES": 10, "3DES": 8, "RC4": 10, "RSA-1024": 10,
                 "RSA-2048": 3, "ECB": 7, "ECDSA-P256": 2, "AES-128-CBC": 3, "AES-256-GCM": 1}
QUANTUM_THREAT = {"RSA-1024": 10, "RSA-2048": 9, "RSA-4096": 8, "ECDSA-P256": 9, "ECDH": 9,
                  "DH": 9, "MD5": 1, "SHA1": 2, "AES-128": 4, "AES-256": 2}
REPLACEMENT_EFFORT = {"MD5": 2, "SHA1": 2, "DES": 3, "3DES": 4, "RC4": 3, "RSA-1024": 6,
                      "RSA-2048": 7, "ECB": 4, "ECDSA-P256": 8, "ECDH": 8}

@dataclass
class CryptoUsage:
    algorithm: str; location: str; data_sensitivity: int  # 1-10
    usage_count: int = 1

    def priority_score(self) -> float:
        exploit = EXPLOIT_SCORE.get(self.algorithm, 5)
        quantum = QUANTUM_THREAT.get(self.algorithm, 3)
        effort = REPLACEMENT_EFFORT.get(self.algorithm, 5)
        return round((exploit * 0.35 + quantum * 0.35 + self.data_sensitivity * 0.30) * (10 / max(effort, 1)), 2)

    def recommendation(self) -> str:
        algo = self.algorithm
        recs = {"MD5": "Replace with SHA-256 or BLAKE2b", "SHA1": "Replace with SHA-256",
                "DES": "Replace with AES-256-GCM", "3DES": "Replace with AES-256-GCM",
                "RC4": "Replace with ChaCha20-Poly1305", "RSA-1024": "Upgrade to ML-KEM-768 (Kyber)",
                "RSA-2048": "Migrate to ML-KEM-768 before 2030", "ECDSA-P256": "Migrate to ML-DSA (Dilithium)",
                "ECDH": "Migrate to ML-KEM (Kyber) for key exchange", "ECB": "Switch to AES-256-GCM"}
        return recs.get(algo, f"Evaluate {algo} against NIST PQC standards")

def build_matrix(usages: list[CryptoUsage]) -> list[dict]:
    rows = []
    for u in sorted(usages, key=lambda x: -x.priority_score()):
        rows.append({"algorithm": u.algorithm, "location": u.location, "count": u.usage_count,
            "data_sensitivity": u.data_sensitivity, "priority_score": u.priority_score(),
            "quantum_threat": QUANTUM_THREAT.get(u.algorithm, 0),
            "exploit_risk": EXPLOIT_SCORE.get(u.algorithm, 0),
            "replacement_effort": REPLACEMENT_EFFORT.get(u.algorithm, 5),
            "recommendation": u.recommendation()})
    return rows

def main():
    parser = argparse.ArgumentParser(description="Crypto Migration Priority Matrix")
    parser.add_argument("--input", "-i", help="JSON findings file from crypto-inventory-scanner")
    parser.add_argument("--output", "-o", help="Write priority matrix to file")
    args = parser.parse_args()
    usages = []
    if args.input:
        data = json.loads(open(args.input).read())
        seen: dict = {}
        for sev, findings in data.get("by_severity", {}).items():
            for f in findings:
                algo = f["pattern"].split("<")[0].strip()
                key = (algo, f["file"])
                if key not in seen:
                    seen[key] = CryptoUsage(algorithm=algo, location=f["file"],
                        data_sensitivity=9 if sev == "CRITICAL" else 6)
                else:
                    seen[key].usage_count += 1
        usages = list(seen.values())
    else:
        usages = [CryptoUsage("MD5", "auth/password_hash.py", 10, 45),
                  CryptoUsage("SHA1", "signing/token.py", 8, 12),
                  CryptoUsage("RSA-2048", "tls/cert_gen.py", 9, 3),
                  CryptoUsage("ECDSA-P256", "api/jwt_sign.py", 9, 88)]
    matrix = build_matrix(usages)
    report = {"total_findings": len(matrix), "critical_count": sum(1 for r in matrix if r["priority_score"] > 7), "matrix": matrix}
    print(json.dumps(report, indent=2))
    if args.output:
        with open(args.output, "w") as f: json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
