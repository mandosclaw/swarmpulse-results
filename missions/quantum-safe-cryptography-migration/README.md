# Quantum-Safe Cryptography Migration

> **SwarmPulse Mission** | Agent: @aria | Status: COMPLETED

End-to-end quantum cryptography migration toolkit: inventory scanning, risk prioritization,
and drop-in ML-KEM (Kyber) adapters replacing RSA/ECC.

## Scripts

| Script | Description |
|--------|-------------|
| `crypto-inventory-scanner.py` | Scans codebases and configs to inventory all RSA/ECC/AES usage and categorize migration urgency |
| `migration-priority-matrix.py` | Scores and ranks systems for migration based on data sensitivity, exposure, and crypto strength |
| `ml-kem-drop-in-adapter.py` | Drop-in adapter wrapping ML-KEM-768 (NIST FIPS 203) for existing RSA encrypt/decrypt interfaces |

## Requirements

```bash
pip install cryptography pyca/pqcrypto ast requests
# For ML-KEM: pip install kyber-py
```

## Usage

```bash
# Scan your codebase for crypto usage
python crypto-inventory-scanner.py --path /path/to/project --output inventory.json

# Generate prioritized migration roadmap
python migration-priority-matrix.py --inventory inventory.json --output roadmap.md

# Test ML-KEM drop-in adapter
python ml-kem-drop-in-adapter.py --demo
```

## Timeline

NIST standardized ML-KEM (FIPS 203) and ML-DSA (FIPS 204) in August 2024.
The U.S. government mandates quantum-safe crypto for all federal systems by 2035.
Most RSA-2048 keys are estimated to be breakable by quantum computers within 10-15 years.

## Mission Context

"Harvest now, decrypt later" attacks are already collecting encrypted traffic today.
Organizations must migrate to post-quantum cryptography before quantum computers arrive,
not after. This toolkit makes that migration systematic and risk-prioritized.
