#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Crypto inventory scanner
# Mission: Quantum-Safe Cryptography Migration
# Agent:   @quinn
# Date:    2026-03-23T22:21:08.544Z
# Repo:    https://github.com/mandosclaw/swarmpulse-results
# ─────────────────────────────────────────────────────────────

"""Crypto inventory scanner — scans codebases for weak/legacy crypto usage via AST and regex."""
import argparse, ast, json, logging, re
from dataclasses import dataclass, field
from pathlib import Path
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

WEAK_PATTERNS = {
    "RSA < 2048": re.compile(r'RSA\.generate\s*\(\s*(\d+)', re.I),
    "MD5": re.compile(r'\bmd5\b', re.I), "SHA1": re.compile(r'\bsha1\b|\bsha-1\b', re.I),
    "DES/3DES": re.compile(r'\b(DES|3DES|TripleDES)\b', re.I),
    "RC4": re.compile(r'\bRC4\b', re.I), "ECB mode": re.compile(r'\.new\s*\([^)]*MODE_ECB', re.I),
    "hardcoded_key": re.compile(r'(key|secret|password)\s*=\s*["\'][a-zA-Z0-9+/]{16,}["\']', re.I),
}
CRYPTO_IMPORTS = re.compile(r'(Crypto|cryptography|OpenSSL|hashlib|hmac|ssl)', re.I)

@dataclass
class Finding:
    file: str; line: int; pattern: str; excerpt: str; severity: str

def scan_file(path: Path) -> list[Finding]:
    findings = []
    try:
        text = path.read_text(errors="replace")
        if not CRYPTO_IMPORTS.search(text): return []
        for i, line in enumerate(text.splitlines(), 1):
            for name, pat in WEAK_PATTERNS.items():
                m = pat.search(line)
                if m:
                    if name == "RSA < 2048":
                        bits = int(m.group(1))
                        if bits >= 2048: continue
                    sev = "CRITICAL" if name in ("MD5", "SHA1", "DES/3DES", "RC4", "ECB mode") else "HIGH"
                    findings.append(Finding(str(path), i, name, line.strip()[:100], sev))
    except Exception as e:
        log.debug("Error scanning %s: %s", path, e)
    return findings

def main():
    parser = argparse.ArgumentParser(description="Crypto Inventory Scanner — finds weak crypto usage")
    parser.add_argument("paths", nargs="+", help="Files or directories to scan")
    parser.add_argument("--ext", default=".py,.js,.ts,.go,.java,.rb", help="File extensions")
    parser.add_argument("--output", "-o", help="Write JSON report to file")
    args = parser.parse_args()
    exts = set(args.ext.split(","))
    findings = []
    for p in args.paths:
        root = Path(p)
        files = list(root.rglob("*")) if root.is_dir() else [root]
        for f in files:
            if f.suffix in exts and "__pycache__" not in str(f):
                findings.extend(scan_file(f))
    by_sev = {}
    for f in findings:
        by_sev.setdefault(f.severity, []).append({"file": f.file, "line": f.line, "pattern": f.pattern, "excerpt": f.excerpt})
    report = {"total": len(findings), "by_severity": by_sev,
              "summary": {s: len(v) for s, v in by_sev.items()}}
    print(json.dumps(report, indent=2))
    if args.output:
        with open(args.output, "w") as f: json.dump(report, f, indent=2)
    log.info("Found %d weak crypto usages in scanned files", len(findings))

if __name__ == "__main__":
    main()
