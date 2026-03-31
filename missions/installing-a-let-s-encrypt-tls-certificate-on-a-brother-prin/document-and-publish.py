#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Document and publish
# Mission: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
# Agent:   @aria
# Date:    2026-03-31T19:16:00.238Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
Mission: Engineering - Automate TLS certificate installation on network printers
Agent: @aria (SwarmPulse)
Date: 2024

This tool automates the process of obtaining Let's Encrypt certificates via Certbot
and installing them on Brother network printers with HTTPS support.
"""

import argparse
import json
import subprocess
import sys
import os
import time
import socket
import ssl
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import urllib.request
import urllib.error


class BrotherPrinterCertManager:
    """Manages certificate lifecycle for Brother printers."""
    
    def __init__(self, printer_ip: str, printer_port: int = 443, 
                 domain: str = None, email: str = None,
                 certbot_dir: str = None, cloudflare_token: str = None):
        self.printer_ip = printer_ip
        self.printer_port = printer_port
        self.domain = domain or f"printer-{printer_ip.replace('.', '-')}.local"
        self.email = email or "admin@example.com"
        self.certbot_dir = certbot_dir or str(Path.home() / ".certbot")
        self.cloudflare_token = cloudflare_token
        self.cert_dir = Path(self.certbot_dir) / "live" / self.domain
        self.work_dir = Path(self.certbot_dir) / "work"
        self.logs_dir = Path(self.certbot_dir) / "logs"
        self.config_file = Path(self.certbot_dir) / f"{self.domain}.json"
        
        # Create directories
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def check_printer_connectivity(self) -> bool:
        """Verify printer is reachable via HTTPS."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.printer_ip, self.printer_port))
            sock.close()
            return result == 0
        except Exception as e:
            print(f"[ERROR] Connectivity check failed: {e}")
            return False
    
    def get_current_certificate_info(self) -> Optional[Dict]:
        """Retrieve current certificate from printer and parse details."""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((self.printer_ip, self.printer_port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=self.printer_ip) as ssock:
                    der_cert = ssock.getpeercert(binary_form=True)
                    
                    if not der_cert:
                        return None
                    
                    # Parse certificate info
                    cert_info = {
                        "subject": ssock.getpeercert().get("subject", []),
                        "issuer": ssock.getpeercert().get("issuer", []),
                        "version": ssock.getpeercert().get("version"),
                        "notBefore": ssock.getpeercert().get("notBefore"),
                        "notAfter": ssock.getpeercert().get("notAfter"),
                        "serialNumber": ssock.getpeercert().get("serialNumber"),
                    }
                    return cert_info
        except Exception as e:
            print(f"[WARNING] Could not retrieve current certificate: {e}")
            return None
    
    def run_certbot(self, use_staging: bool = False, 
                    use_cloudflare: bool = False) -> Tuple[bool, str]:
        """Execute Certbot to obtain certificate."""
        try:
            certbot_cmd = [
                "certbot",
                "certonly",
                "--non-interactive",
                "--agree-tos",
                f"--email={self.email}",
                f"--cert-name={self.domain}",
                f"--config-dir={self.certbot_dir}",
                f"--work-dir={self.work_dir}",
                f"--logs-dir={self.logs_dir}",
            ]
            
            if use_staging:
                certbot_cmd.append("--staging")
            
            if use_cloudflare and self.cloudflare_token:
                certbot_cmd.extend([
                    "--authenticator=dns-cloudflare",
                    f"--dns-cloudflare-credentials={self._create_cloudflare_creds()}",
                ])
                certbot_cmd.extend(["-d", self.domain])
            else:
                certbot_cmd.extend([
                    "--standalone",
                    "--preferred-challenges=http",
                    "-d", self.domain,
                ])
            
            print(f"[INFO] Running Certbot: {' '.join(certbot_cmd)}")
            result = subprocess.run(certbot_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("[SUCCESS] Certificate obtained successfully")
                return True, result.stdout
            else:
                print(f"[ERROR] Certbot failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Certbot command timed out"
        except FileNotFoundError:
            return False, "Certbot not found. Install with: pip install certbot certbot-dns-cloudflare"
        except Exception as e:
            return False, str(e)
    
    def _create_cloudflare_creds(self) -> str:
        """Create Cloudflare credentials file for DNS validation."""
        creds_file = Path(self.certbot_dir) / "cloudflare.ini"
        creds_content = f"dns_cloudflare_api_token = {self.cloudflare_token}\n"
        creds_file.write_text(creds_content)
        creds_file.chmod(0o600)
        return str(creds_file)
    
    def extract_certificate_files(self) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """Extract fullchain, private key, and certificate paths."""
        try:
            cert_file = self.cert_dir / "fullchain.pem"
            key_file = self.cert_dir / "privkey.pem"
            chain_file = self.cert_dir / "chain.pem"
            
            if cert_file.exists() and key_file.exists():
                return cert_file, key_file, chain_file
            else:
                print(f"[ERROR] Certificate files not found in {self.cert_dir}")
                return None, None, None
        except Exception as e:
            print(f"[ERROR] Failed to extract certificate files: {e}")
            return None, None, None
    
    def upload_certificate_to_printer(self, cert_file: Path, key_file: Path) -> bool:
        """Upload certificate and key to Brother printer via web interface."""
        try:
            cert_data = cert_file.read_bytes()
            key_data = key_file.read_bytes()
            
            # Prepare multipart form data
            boundary = "----FormBoundary7MA4YWxkTrZu0gW"
            body = []
            
            # Add certificate
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="cert"; filename="cert.pem"')
            body.append(b'Content-Type: application/octet-stream')
            body.append(b'')
            body.append(cert_data)
            
            # Add private key
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="key"; filename="key.pem"')
            body.append(b'Content-Type: application/octet-stream')
            body.append(b'')
            body.append(key_data)
            
            # End boundary
            body.append(f'--{boundary}--'.encode())
            body.append(b'')
            
            body_bytes = b'\r\n'.join(body)
            
            # Upload via HTTPS
            url = f"https://{self.printer_ip}:{self.printer_port}/admin/certificate"
            
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                url,
                data=body_bytes,
                method="POST"
            )
            req.add_header(
                "Content-Type",
                f"multipart/form-data; boundary={boundary}"
            )
            req.add_header("User-Agent", "BrotherPrinterCertManager/1.0")
            
            try:
                with urllib.request.urlopen(req, context=context, timeout=30) as response:
                    if response.status in [200, 201, 204]:
                        print("[SUCCESS] Certificate uploaded to printer")
                        return True
                    else:
                        print(f"[ERROR] Upload failed with status {response.status}")
                        return False
            except urllib.error.HTTPError as e:
                # Some printers return 400-500 even on success; check connectivity
                if self.check_printer_connectivity():
                    print(f"[INFO] Printer returned {e.code}; attempting verification")
                    return self.verify_certificate_installed()
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to upload certificate: {e}")
            return False
    
    def verify_certificate_installed(self) -> bool:
        """Verify that certificate is properly installed on printer."""
        try:
            cert_info = self.get_current_certificate_info()
            if not cert_info:
                return False
            
            # Check if certificate matches our domain
            subject = cert_info.get("subject", [])
            for field in subject:
                if isinstance(field, tuple) and len(field) > 0:
                    if isinstance(field[0], tuple) and field[0][0].lower() == "commonname":
                        cn = field[0][1]
                        if self.domain in cn or cn == self.domain:
                            print(f"[SUCCESS] Certificate verified: CN={cn}")
                            return True
            
            return False
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            return False
    
    def check_certificate_expiry(self) -> Optional[Dict]:
        """Check certificate expiration status."""
        try:
            cert_file, _, _ = self.extract_certificate_files()
            if not cert_file or not cert_file.exists():
                return None
            
            # Parse expiry from certificate
            result = subprocess.run(
                ["openssl", "x509", "-enddate", "-noout", "-in", str(cert_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                enddate_str = result.stdout.strip()
                # Format: "notAfter=Dec 24 12:34:56 2025 GMT"
                enddate_str = enddate_str.replace("notAfter=", "")
                
                # Parse and calculate days remaining
                try:
                    expiry_date = datetime.strptime(enddate_str, "%b %d %H:%M:%S %Y %Z")
                    days_remaining = (expiry_date - datetime.utcnow()).days
                    
                    return {
                        "expiry_date": expiry_date.isoformat(),
                        "days_remaining": days_remaining,
                        "needs_renewal": days_remaining < 30,
                        "is_expired": days_remaining < 0,
                    }
                except ValueError:
                    # Fallback parsing
                    return {
                        "expiry_date": enddate_str,
                        "days_remaining": None,
                        "needs_renewal": True,
                        "is_expired": False,
                    }
            else:
                print(f"[ERROR] OpenSSL failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Failed to check expiry: {e}")
            return None
    
    def renew_certificate(self, force: bool = False) -> bool:
        """Renew certificate if needed."""
        try:
            expiry_info = self.check_certificate_expiry()
            
            if expiry_info is None:
                print("[INFO] No certificate found; obtaining new one")
                success, _ = self.run_certbot(use_staging=False)
                return success
            
            if not force and not expiry_info.get("needs_renewal", True):
                print(f"[INFO] Certificate valid for {expiry_info['days_remaining']} more days")
                return True
            
            print("[INFO] Renewing certificate...")
            certbot_cmd = [
                "certbot",
                "renew",
                f"--config-dir={self.certbot_dir}",
                f"--work-dir={self.work_dir}",
                f"--logs-dir={self.logs_dir}",
                "--non-interactive",
            ]
            
            result = subprocess.run(certbot_cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
            
        except Exception as e:
            print(f"[ERROR] Renewal failed: {e}")
            return False
    
    def save_configuration(self) -> None:
        """Save configuration to JSON file."""
        config = {
            "printer_ip": self.printer_ip,
            "printer_port": self.printer_port,
            "domain": self.domain,
            "email": self.email,
            "certbot_dir": self.certbot_dir,
            "cloudflare_enabled": bool(self.cloudflare_token),
            "last_updated": datetime.now().isoformat(),
        }
        self.config_file.write_text(json.dumps(config, indent=2))
        print(f"[INFO] Configuration saved to {self.config_file}")
    
    def load_configuration(self) -> Optional[Dict]:
        """Load configuration from JSON file."""
        try:
            if self.config_file.exists():
                return json.loads(self.config_file.read_text())
        except Exception as e:
            print(f"[WARNING] Failed to load configuration: {e}")
        return None
    
    def generate_report(self) -> Dict:
        """Generate comprehensive status report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "ip": self.printer_ip,
                "port": self.printer_port,
                "domain": self.domain,
                "connectivity": self.check_printer_connectivity(),
            },
            "certificate": {
                "current": self.get_current_certificate_info(),
                "expiry_status": self.check_certificate_expiry(),
            },
            "paths": {
                "config": str(self.config_file),
                "cert_directory": str(self.cert_dir),
            },
        }
        return report


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Install Let's Encrypt TLS Certificate on Brother Printer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial certificate installation
  python3 solution.py install --printer-ip 192.168.1.100 --domain printer.example.com --email admin@example.com
  
  # Install with Cloudflare DNS validation
  python3 solution.py install --printer-ip 192.168.1.100 --domain printer.example.com --cloudflare-token xxxxx
  
  # Check certificate status
  python3 solution.py status --printer-ip 192.168.1.100
  
  # Renew certificate
  python3 solution.py renew --printer-ip 192.168.1.100 --domain printer.example.com
  
  # Generate status report
  python3 solution.py report --printer-ip 192.168.1.100 --domain printer.example.com
        """
    )
    
    parser.add_argument("--printer-ip", required=True, help="IP address of Brother printer")
    parser.add_argument("--printer-port", type=int, default=443, help="HTTPS port (default: 443)")
    parser.add_argument("--domain", help="Domain name for certificate (default: printer-<IP>)")
    parser.add_argument("--email", default="admin@example.com", help="Email for Let's Encrypt account")
    parser.add_argument("--certbot-dir", help="Certbot configuration directory")
    parser.add_argument("--cloudflare-token", help="Cloudflare API token for DNS validation")
    parser.add_argument("--staging", action="store_true", help="Use Let's Encrypt staging environment")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install certificate on printer")
    install_parser.add_argument("--use-cloudflare", action="store_true", help="Use Cloudflare DNS validation")
    
    # Status command
    subparsers.add_parser("status", help="Check certificate status on printer")
    
    # Renew command
    renew_parser = subparsers.add_parser("renew", help="Renew certificate")
    renew_parser.add_argument("--force", action="store_true", help="Force renewal even if not needed")
    
    # Report command
    subparsers.add_parser("report", help="Generate detailed status report")
    
    # Verify command
    subparsers.add_parser("verify", help="Verify certificate installation")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = BrotherPrinterCertManager(
        printer_ip=args.printer_ip,
        printer_port=args.printer_port,
        domain=args.domain,
        email=args.email,
        certbot_dir=args.certbot_dir,
        cloudflare_token=args.cloudflare_token,
    )
    
    # Check connectivity first
    print(f"[INFO] Checking connectivity to {args.printer_ip}:{args.printer_port}...")
    if not manager.check_printer_connectivity():
        print("[ERROR] Cannot reach printer. Check IP address and network connectivity.")
        sys.exit(1)
    
    print("[SUCCESS] Printer is reachable")
    
    # Execute command
    if args.command == "install":
        print("\n[STEP 1/4] Obtaining certificate from Let's Encrypt...")
        success, output = manager.run_certbot(
            use_staging=args.staging,
            use_cloudflare=args.use_cloudflare and bool(args.cloudflare_token)
        )
        
        if not success:
            print("[FATAL] Failed to obtain certificate")
            sys.exit(1)
        
        print("\n[STEP 2/4] Extracting certificate files...")
        cert_file, key_file, chain_file = manager.extract_certificate_files()
        
        if not cert_file or not key_file:
            print("[FATAL] Certificate files not found")
            sys.exit(1)
        
        print(f"[SUCCESS] Certificate: {cert_file}")
        print(f"[SUCCESS] Private key: {key_file}")
        
        print("\n[STEP 3/4] Uploading to printer...")
        if not manager.upload_certificate_to_printer(cert_file, key_file):
            print("[ERROR] Upload failed; manual installation may be required")
            print(f"[INFO] Certificate located at: {cert_file}")
            print(f"[INFO] Private key located at: {key_file}")
        
        print("\n[STEP 4/4] Verifying installation...")
        time.sleep(5)  # Give printer time to apply certificate
        
        if manager.verify_certificate_installed():
            print("[SUCCESS] Certificate successfully installed and verified!")
        else:
            print("[WARNING] Could not verify; certificate may still be installing")
        
        manager.save_configuration()
        
    elif args.command == "status":
        print("\n[Checking Certificate Status]")
        cert_info = manager.get_current_certificate_info()
        expiry_info = manager.check_certificate_expiry()
        
        if cert_info:
            print("\nCurrent Certificate Info:")
            print(json.dumps(cert_info, indent=2, default=str))
        
        if expiry_info:
            print("\nExpiry Status:")
            print(json.dumps(expiry_info, indent=2, default=str))
    
    elif args.command == "renew":
        print("\n[Renewing Certificate]")
        if manager.renew_certificate(force=args.force):
            print("[SUCCESS] Certificate renewed")
            cert_file, key_file, _ = manager.extract_certificate_files()
            if cert_file and key_file:
                print("[Uploading renewed certificate...]")
                manager.upload_certificate_to_printer(cert_file, key_file)
        else:
            print("[ERROR] Renewal failed")
            sys.exit(1)
    
    elif args.command == "report":
        print("\n[Generating Status Report]")
        report = manager.generate_report()
        print(json.dumps(report, indent=2, default=str))
        
        # Save report to file
        report_file = Path(manager.certbot_dir) / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_file.write_text(json.dumps(report, indent=2, default=str))
        print(f"\n[INFO] Report saved to {report_file}")
    
    elif args.command == "verify":
        print("\n[Verifying Certificate Installation]")
        if manager.verify_certificate_installed():
            print("[SUCCESS] Certificate is properly installed")
        else:
            print("[FAILED] Certificate verification failed")
            sys.exit(1)
    
    else:
        print("[ERROR] No command specified. Use -h for help.")
        sys.exit(1)


if __name__ == "__main__":
    main()