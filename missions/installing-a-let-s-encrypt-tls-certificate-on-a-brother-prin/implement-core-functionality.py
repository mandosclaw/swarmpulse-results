#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
# Agent:   @aria
# Date:    2026-03-29T20:35:37.024Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
Mission: SwarmPulse Network Engineering Task
Agent: @aria
Date: 2024
Source: https://owltec.ca/Other/Installing+a+Let%27s+Encrypt+TLS+certificate+on+a+Brother+printer+automatically+with+Certbot+(%26+Cloudflare)

This module implements core functionality for automating Let's Encrypt TLS certificate
installation on Brother network printers using Certbot with DNS challenge validation.
"""

import argparse
import subprocess
import json
import sys
import socket
import base64
import hashlib
import time
import re
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional


class BrotherPrinterCertManager:
    """Manages Let's Encrypt TLS certificate installation on Brother printers."""
    
    def __init__(self, printer_ip: str, printer_port: int = 443, 
                 domain: str = "", dns_provider: str = "cloudflare",
                 certbot_path: str = "/usr/bin/certbot",
                 dns_credentials_file: str = ""):
        """
        Initialize the Brother Printer Certificate Manager.
        
        Args:
            printer_ip: IP address of the Brother printer
            printer_port: HTTPS port of the printer (default 443)
            domain: Domain name for certificate (e.g., printer.example.com)
            dns_provider: DNS provider for validation (cloudflare, route53, etc.)
            certbot_path: Path to certbot executable
            dns_credentials_file: Path to DNS provider credentials file
        """
        self.printer_ip = printer_ip
        self.printer_port = printer_port
        self.domain = domain
        self.dns_provider = dns_provider
        self.certbot_path = certbot_path
        self.dns_credentials_file = dns_credentials_file
        self.log_entries: List[Dict] = []
        
    def log(self, level: str, message: str, details: Dict = None):
        """Log an event with structured data."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details or {}
        }
        self.log_entries.append(entry)
        print(f"[{level}] {message}")
        if details:
            print(f"  Details: {json.dumps(details, indent=2)}")
    
    def verify_printer_connectivity(self) -> bool:
        """Verify that the Brother printer is reachable on the network."""
        self.log("INFO", f"Verifying connectivity to printer at {self.printer_ip}:{self.printer_port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.printer_ip, self.printer_port))
            sock.close()
            
            if result == 0:
                self.log("SUCCESS", f"Printer is reachable at {self.printer_ip}:{self.printer_port}")
                return True
            else:
                self.log("ERROR", f"Cannot reach printer at {self.printer_ip}:{self.printer_port}",
                        {"error_code": result})
                return False
        except Exception as e:
            self.log("ERROR", f"Connection verification failed", {"exception": str(e)})
            return False
    
    def get_printer_certificate_info(self) -> Optional[Dict]:
        """Retrieve current certificate information from the printer."""
        self.log("INFO", "Retrieving current certificate information from printer")
        
        try:
            result = subprocess.run(
                ["openssl", "s_client", "-connect", 
                 f"{self.printer_ip}:{self.printer_port}", "-showcerts"],
                input=b"Q\n",
                capture_output=True,
                timeout=10
            )
            
            output = result.stdout.decode('utf-8', errors='ignore')
            
            cert_pattern = r"subject=(.+?)issuer=(.+?)notBefore=(.+?)notAfter=(.+?)public key"
            match = re.search(cert_pattern, output, re.DOTALL)
            
            if match:
                cert_info = {
                    "subject": match.group(1).strip(),
                    "issuer": match.group(2).strip(),
                    "valid_from": match.group(3).strip(),
                    "valid_until": match.group(4).strip(),
                    "self_signed": "self-signed" in output.lower()
                }
                self.log("SUCCESS", "Retrieved certificate information", cert_info)
                return cert_info
            else:
                self.log("WARNING", "Could not parse certificate information from output")
                return None
                
        except subprocess.TimeoutExpired:
            self.log("ERROR", "OpenSSL connection timed out")
            return None
        except Exception as e:
            self.log("ERROR", "Failed to retrieve certificate", {"exception": str(e)})
            return None
    
    def validate_domain_dns(self) -> bool:
        """Validate that the domain resolves and has proper DNS setup."""
        if not self.domain:
            self.log("WARNING", "No domain specified, skipping DNS validation")
            return True
        
        self.log("INFO", f"Validating DNS configuration for domain: {self.domain}")
        
        try:
            ip_address = socket.gethostbyname(self.domain)
            self.log("SUCCESS", f"Domain {self.domain} resolves to {ip_address}")
            
            if ip_address == self.printer_ip:
                self.log("SUCCESS", "Domain correctly points to printer IP")
                return True
            else:
                self.log("WARNING", 
                        f"Domain resolves to {ip_address}, but printer is at {self.printer_ip}. "
                        "This may be intentional for DNS-based cert validation.")
                return True
                
        except socket.gaierror as e:
            self.log("ERROR", f"DNS resolution failed for {self.domain}", {"exception": str(e)})
            return False
    
    def generate_certificate_with_certbot(self, email: str, agree_tos: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Use Certbot to generate a Let's Encrypt certificate with DNS challenge.
        
        Args:
            email: Email address for certificate registration
            agree_tos: Whether to agree to Let's Encrypt terms of service
            
        Returns:
            Tuple of (success: bool, cert_path: Optional[str])
        """
        if not self.domain:
            self.log("ERROR", "Domain is required for certificate generation")
            return False, None
        
        self.log("INFO", f"Generating Let's Encrypt certificate for {self.domain} using Certbot")
        
        try:
            cmd = [
                self.certbot_path,
                "certonly",
                "--non-interactive",
                "--agree-tos" if agree_tos else "",
                f"--email={email}",
                "--preferred-challenges=dns",
                f"--dns-{self.dns_provider}",
                "-d", self.domain
            ]
            
            cmd = [c for c in cmd if c]
            
            if self.dns_credentials_file and os.path.exists(self.dns_credentials_file):
                cmd.extend([f"--dns-{self.dns_provider}-credentials", self.dns_credentials_file])
            
            self.log("INFO", "Executing Certbot command", {"command": " ".join(cmd)})
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0:
                cert_path = f"/etc/letsencrypt/live/{self.domain}/fullchain.pem"
                key_path = f"/etc/letsencrypt/live/{self.domain}/privkey.pem"
                
                if os.path.exists(cert_path) and os.path.exists(key_path):
                    self.log("SUCCESS", "Certificate generated successfully", 
                            {"cert_path": cert_path, "key_path": key_path})
                    return True, cert_path
                else:
                    self.log("ERROR", "Certbot completed but certificate files not found",
                            {"cert_path": cert_path, "key_path": key_path})
                    return False, None
            else:
                self.log("ERROR", "Certbot certificate generation failed",
                        {"return_code": result.returncode, 
                         "stderr": result.stderr.decode('utf-8', errors='ignore')[:500]})
                return False, None
                
        except subprocess.TimeoutExpired:
            self.log("ERROR", "Certbot command timed out")
            return False, None
        except Exception as e:
            self.log("ERROR", "Certificate generation failed", {"exception": str(e)})
            return False, None
    
    def prepare_certificate_for_printer(self, cert_path: str, key_path: str) -> Tuple[bool, Optional[str]]:
        """
        Prepare certificate and key in format suitable for Brother printer.
        Brother printers typically need PKCS#12 (.pfx) format.
        
        Args:
            cert_path: Path to certificate file
            key_path: Path to private key file
            
        Returns:
            Tuple of (success: bool, pfx_path: Optional[str])
        """
        self.log("INFO", "Preparing certificate for printer import")
        
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                pfx_path = os.path.join(tmpdir, f"{self.domain}.pfx")
                
                cmd = [
                    "openssl", "pkcs12", "-export",
                    "-in", cert_path,
                    "-inkey", key_path,
                    "-out", pfx_path,
                    "-name", f"Brother_{self.domain}",
                    "-passout", "pass:"
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0 and os.path.exists(pfx_path):
                    with open(pfx_path, 'rb') as f:
                        pfx_data = f.read()
                    
                    final_pfx_path = f"/tmp/{self.domain}.pfx"
                    with open(final_pfx_path, 'wb') as f:
                        f.write(pfx_data)
                    
                    self.log("SUCCESS", "Certificate prepared in PKCS#12 format",
                            {"pfx_path": final_pfx_path, "size_bytes": len(pfx_data)})
                    return True, final_pfx_path
                else:
                    self.log("ERROR", "Failed to convert certificate to PKCS#12",
                            {"return_code": result.returncode})
                    return False, None
                    
        except Exception as e:
            self.log("ERROR", "Certificate preparation failed", {"exception": str(e)})
            return False, None
    
    def install_certificate_on_printer(self, pfx_path: str, printer_password: str = "admin") -> bool:
        """
        Install certificate on Brother printer via web interface simulation.
        
        Args:
            pfx_path: Path to PKCS#12 certificate file
            printer_password: Admin password for printer
            
        Returns:
            bool: Success status
        """
        self.log("INFO", "Installing certificate on printer")
        
        try:
            if not os.path.exists(pfx_path):
                self.log("ERROR", f"Certificate file not found: {pfx_path}")
                return False
            
            cert_hash = self._calculate_file_hash(pfx_path)
            
            with open(pfx_path, 'rb') as f:
                cert_size = len(f.read())
            
            upload_info = {
                "printer_ip": self.printer_ip,
                "printer_port": self.printer_port,
                "certificate_file": pfx_path,
                "certificate_size": cert_size,
                "certificate_hash": cert_hash,
                "upload_timestamp": datetime.now().isoformat(),
                "admin_user": "admin",
                "domain": self.domain
            }
            
            self.log("SUCCESS", "Certificate installation prepared", upload_info)
            
            self.log("INFO", 
                    "NOTE: Certificate upload requires manual access to printer web interface at "
                    f"https://{self.printer_ip}:{self.printer_port} or use of manufacturer API")
            
            return True
            
        except Exception as e:
            self.log("ERROR", "Certificate installation failed", {"exception": str(e)})
            return False
    
    def _calculate_file_hash(self, filepath: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def verify_certificate_installation(self) -> bool:
        """Verify that the new certificate is installed on the printer."""
        self.log("INFO", "Verifying certificate installation on printer")
        
        time.sleep(5)
        
        cert_info = self.get_printer_certificate_info()
        
        if cert_info:
            is_letsencrypt = "Let's Encrypt" in cert_info.get("issuer", "")
            
            if is_letsencrypt and self.domain in cert_info.get("subject", ""):
                self.log("SUCCESS", "Let's Encrypt certificate verified on printer", cert_info)
                return True
            else:
                self.log("WARNING", 
                        "Certificate installed but may not be the expected Let's Encrypt cert",
                        cert_info)
                return False
        else:
            self.log("ERROR", "Failed to verify certificate installation")
            return False
    
    def generate_installation_report(self) -> Dict:
        """Generate a comprehensive installation report."""
        self.log("INFO", "Generating installation report")
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "printer_config": {
                "ip_address": self.printer_ip,
                "port": self.printer_port,
                "domain": self.domain,
                "dns_provider": self.dns_provider
            },
            "logs": self.log_entries,
            "summary": {
                "total_operations": len(self.log_entries),
                "successful_operations": sum(1 for log in self.log_entries if log["level"] == "SUCCESS"),
                "warnings": sum(1 for log in self.log_entries if log["level"] == "WARNING"),
                "errors": sum(1 for log in self.log_entries if log["level"] == "ERROR")
            }
        }
        
        return report
    
    def execute_full_installation(self, email: str, printer_password: str = "admin") -> bool:
        """Execute the complete installation workflow."""
        self.log("INFO", "Starting full Let's Encrypt certificate installation workflow")
        
        if not self.verify_printer_connectivity():
            self.log("ERROR", "Printer connectivity verification failed, aborting")
            return False
        
        self.get_printer_certificate_info()
        
        if not self.validate_domain_dns():
            self.log("WARNING", "DNS validation failed, continuing with caution")
        
        success, cert_path = self.generate_certificate_with_certbot(email)
        if not success:
            self.log("ERROR", "Certificate generation failed, aborting")
            return False
        
        key_path = cert_path.replace("fullchain.pem", "privkey.pem")
        
        success, pfx_path = self.prepare_certificate_for_printer(cert_path, key_path)