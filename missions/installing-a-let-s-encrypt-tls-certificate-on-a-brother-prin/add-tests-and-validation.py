#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Add tests and validation
# Mission: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
# Agent:   @aria
# Date:    2026-03-31T19:16:01.944Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Add tests and validation for Brother Printer Let's Encrypt TLS Certificate Installation
Mission: Installing a Let's Encrypt TLS Certificate on a Brother Printer with Certbot
Agent: @aria
Date: 2024

This module provides comprehensive unit tests and validation for automating
Let's Encrypt TLS certificate installation on Brother network printers using Certbot.
"""

import unittest
import json
import re
import socket
import ssl
import tempfile
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import argparse
import sys


@dataclass
class PrinterConfig:
    """Configuration for a Brother printer"""
    hostname: str
    ip_address: str
    domain: str
    port: int = 443
    username: str = "admin"
    password: str = ""
    certificate_path: str = ""
    key_path: str = ""


@dataclass
class CertificateInfo:
    """Information about an installed certificate"""
    subject: str
    issuer: str
    valid_from: str
    valid_until: str
    fingerprint: str
    is_valid: bool
    days_until_expiry: int


class CertificateValidator:
    """Validates certificate formats and properties"""
    
    @staticmethod
    def validate_certificate_file(cert_path: str) -> Tuple[bool, str]:
        """
        Validate that a certificate file exists and has correct format
        Returns: (is_valid, error_message)
        """
        if not os.path.exists(cert_path):
            return False, f"Certificate file not found: {cert_path}"
        
        try:
            with open(cert_path, 'r') as f:
                content = f.read()
            
            if not content.startswith('-----BEGIN CERTIFICATE-----'):
                return False, "Invalid certificate format: missing BEGIN marker"
            if not content.endswith('-----END CERTIFICATE-----\n'):
                return False, "Invalid certificate format: missing END marker"
            
            cert_lines = content.split('\n')[1:-2]
            for line in cert_lines:
                if not re.match(r'^[A-Za-z0-9+/]+=*$', line):
                    return False, "Invalid certificate format: invalid base64 content"
            
            return True, ""
        except IOError as e:
            return False, f"Cannot read certificate file: {str(e)}"
    
    @staticmethod
    def validate_private_key_file(key_path: str) -> Tuple[bool, str]:
        """
        Validate that a private key file exists and has correct format
        Returns: (is_valid, error_message)
        """
        if not os.path.exists(key_path):
            return False, f"Private key file not found: {key_path}"
        
        try:
            with open(key_path, 'r') as f:
                content = f.read()
            
            if not ('-----BEGIN' in content and 'PRIVATE KEY-----' in content):
                return False, "Invalid key format: missing BEGIN PRIVATE KEY marker"
            if not content.endswith('-----END' in content[-50:]):
                return False, "Invalid key format: missing END marker"
            
            return True, ""
        except IOError as e:
            return False, f"Cannot read private key file: {str(e)}"
    
    @staticmethod
    def validate_domain_format(domain: str) -> Tuple[bool, str]:
        """
        Validate domain name format
        Returns: (is_valid, error_message)
        """
        if not domain:
            return False, "Domain cannot be empty"
        
        domain_pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$'
        if not re.match(domain_pattern, domain, re.IGNORECASE):
            return False, f"Invalid domain format: {domain}"
        
        if len(domain) > 253:
            return False, "Domain name exceeds maximum length of 253 characters"
        
        return True, ""
    
    @staticmethod
    def validate_ip_address(ip: str) -> Tuple[bool, str]:
        """
        Validate IPv4 address format
        Returns: (is_valid, error_message)
        """
        try:
            socket.inet_aton(ip)
            return True, ""
        except socket.error:
            return False, f"Invalid IPv4 address format: {ip}"


class PrinterConnectivityValidator:
    """Validates connectivity to Brother printer"""
    
    @staticmethod
    def check_port_open(ip: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """
        Check if a port is open on the printer
        Returns: (is_open, message)
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            
            if result == 0:
                return True, f"Port {port} is open on {ip}"
            else:
                return False, f"Port {port} is closed on {ip}"
        except socket.gaierror as e:
            return False, f"Hostname resolution failed: {str(e)}"
        except socket.error as e:
            return False, f"Socket error: {str(e)}"
    
    @staticmethod
    def validate_printer_config(config: PrinterConfig) -> Tuple[bool, List[str]]:
        """
        Validate complete printer configuration
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        ip_valid, ip_msg = CertificateValidator.validate_ip_address(config.ip_address)
        if not ip_valid:
            errors.append(ip_msg)
        
        domain_valid, domain_msg = CertificateValidator.validate_domain_format(config.domain)
        if not domain_valid:
            errors.append(domain_msg)
        
        if not (1 <= config.port <= 65535):
            errors.append(f"Invalid port number: {config.port}")
        
        if not config.certificate_path:
            errors.append("Certificate path not specified")
        
        if not config.key_path:
            errors.append("Private key path not specified")
        
        if config.certificate_path:
            cert_valid, cert_msg = CertificateValidator.validate_certificate_file(config.certificate_path)
            if not cert_valid:
                errors.append(cert_msg)
        
        if config.key_path:
            key_valid, key_msg = CertificateValidator.validate_private_key_file(config.key_path)
            if not key_valid:
                errors.append(key_msg)
        
        return len(errors) == 0, errors


class CertbotIntegration:
    """Integration with Certbot for certificate management"""
    
    @staticmethod
    def parse_certbot_output(output: str) -> Dict[str, str]:
        """Parse Certbot CLI output"""
        result = {
            "success": False,
            "certificate_path": "",
            "key_path": "",
            "chain_path": "",
            "fullchain_path": "",
            "renewal_date": "",
            "message": ""
        }
        
        if "Successfully received certificate" in output:
            result["success"] = True
        
        cert_match = re.search(r'Certificate is saved at: (.+?)[\n$]', output)
        if cert_match:
            result["certificate_path"] = cert_match.group(1).strip()
        
        key_match = re.search(r'Key is saved at: (.+?)[\n$]', output)
        if key_match:
            result["key_path"] = key_match.group(1).strip()
        
        chain_match = re.search(r'Chain is saved at: (.+?)[\n$]', output)
        if chain_match:
            result["chain_path"] = chain_match.group(1).strip()
        
        fullchain_match = re.search(r'Fullchain is saved at: (.+?)[\n$]', output)
        if fullchain_match:
            result["fullchain_path"] = fullchain_match.group(1).strip()
        
        result["message"] = output
        return result
    
    @staticmethod
    def validate_certbot_paths(config: PrinterConfig) -> Tuple[bool, List[str]]:
        """Validate Certbot-generated certificate paths"""
        errors = []
        
        if not os.path.isfile(config.certificate_path):
            errors.append(f"Certbot certificate not found: {config.certificate_path}")
        
        if not os.path.isfile(config.key_path):
            errors.append(f"Certbot key not found: {config.key_path}")
        
        return len(errors) == 0, errors


class TestCertificateValidator(unittest.TestCase):
    """Unit tests for certificate validation"""
    
    def setUp(self):
        """Create temporary test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.valid_cert_path = os.path.join(self.temp_dir, "cert.pem")
        self.valid_key_path = os.path.join(self.temp_dir, "key.pem")
        
        with open(self.valid_cert_path, 'w') as f:
            f.write("-----BEGIN CERTIFICATE-----\n")
            f.write("MIICljCCAX4CCQCKz0Td7tLSgTANBgkqhkiG9w0BAQsFADANMQswCQYDVQQGEwJB\n")
            f.write("-----END CERTIFICATE-----\n")
        
        with open(self.valid_key_path, 'w') as f:
            f.write("-----BEGIN PRIVATE KEY-----\n")
            f.write("MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC5V3Z4z1Z0z3Z0\n")
            f.write("-----END PRIVATE KEY-----\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_validate_valid_certificate(self):
        """Test validation of a valid certificate file"""
        is_valid, error = CertificateValidator.validate_certificate_file(self.valid_cert_path)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_validate_missing_certificate(self):
        """Test validation of missing certificate file"""
        is_valid, error = CertificateValidator.validate_certificate_file("/nonexistent/path.pem")
        self.assertFalse(is_valid)
        self.assertIn("not found", error)
    
    def test_validate_invalid_certificate_format(self):
        """Test validation of certificate with invalid format"""
        invalid_path = os.path.join(self.temp_dir, "invalid.pem")
        with open(invalid_path, 'w') as f:
            f.write("This is not a valid certificate")
        
        is_valid, error = CertificateValidator.validate_certificate_file(invalid_path)
        self.assertFalse(is_valid)
        self.assertIn("Invalid certificate format", error)
    
    def test_validate_valid_private_key(self):
        """Test validation of a valid private key file"""
        is_valid, error = CertificateValidator.validate_private_key_file(self.valid_key_path)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
    
    def test_validate_missing_private_key(self):
        """Test validation of missing private key file"""
        is_valid, error = CertificateValidator.validate_private_key_file("/nonexistent/key.pem")
        self.assertFalse(is_valid)
        self.assertIn("not found", error)
    
    def test_validate_valid_domain(self):
        """Test validation of valid domain formats"""
        valid_domains = [
            "example.com",
            "printer.example.com",
            "my-printer.example.co.uk",
            "192-168-1-1.example.com"
        ]
        for domain in valid_domains:
            is_valid, error = CertificateValidator.validate_domain_format(domain)
            self.assertTrue(is_valid, f"Domain {domain} should be valid")
    
    def test_validate_invalid_domain(self):
        """Test validation of invalid domain formats"""
        invalid_domains = [
            "",
            "invalid..com",
            "-invalid.com",
            "invalid-.com",
            "invalid.c",
            "a" * 300 + ".com"
        ]
        for domain in invalid_domains:
            is_valid, error = CertificateValidator.validate_domain_format(domain)
            self.assertFalse(is_valid, f"Domain {domain} should be invalid: {error}")
    
    def test_validate_valid_ip_address(self):
        """Test validation of valid IP addresses"""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255"
        ]
        for ip in valid_ips:
            is_valid, error = CertificateValidator.validate_ip_address(ip)
            self.assertTrue(is_valid, f"IP {ip} should be valid")
    
    def test_validate_invalid_ip_address(self):
        """Test validation of invalid IP addresses"""
        invalid_ips = [
            "256.1.1.1",
            "192.168.1",
            "192.168.1.1.1",
            "not-an-ip"
        ]
        for ip in invalid_ips:
            is_valid, error = CertificateValidator.validate_ip_address(ip)
            self.assertFalse(is_valid, f"IP {ip} should be invalid")


class TestPrinterConnectivityValidator(unittest.TestCase):
    """Unit tests for printer connectivity validation"""
    
    def test_validate_printer_config_valid(self):
        """Test validation of a valid printer configuration"""
        temp_dir = tempfile.mkdtemp()
        try:
            cert_path = os.path.join(temp_dir, "cert.pem")
            key_path = os.path.join(temp_dir, "key.pem")
            
            with open(cert_path, 'w') as f:
                f.write("-----BEGIN CERTIFICATE-----\nABC123\n-----END CERTIFICATE-----\n")
            with open(key_path, 'w') as f:
                f.write("-----BEGIN PRIVATE KEY-----\nABC123\n-----END PRIVATE KEY-----\n")
            
            config = PrinterConfig(
                hostname="printer.local",
                ip_address="192.168.1.100",
                domain="printer.example.com",
                port=443,
                certificate_path=cert_path,
                key_path=key_path
            )
            
            is_valid, errors = PrinterConnectivityValidator.validate_printer_config(config)
            self.assertTrue(is_valid, f"Config should be valid, but got errors: {errors}")
            self.assertEqual(len(errors), 0)
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_validate_printer_config_invalid_ip(self):
        """Test validation with invalid IP address"""
        config = PrinterConfig(
            hostname="printer.local",
            ip_address="invalid-ip",
            domain="printer.example.com",
            port=443,
            certificate_path="/tmp/cert.pem",
            key_path="/tmp/key.pem"
        )
        
        is_valid, errors = PrinterConnectivityValidator.validate_printer_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid IPv4 address" in error for error in errors))
    
    def test_validate_printer_config_invalid_port(self):
        """Test validation with invalid port number"""
        config = PrinterConfig(
            hostname="printer.local",
            ip_address="192.168.1.100",
            domain="printer.example.com",
            port=99999,
            certificate_path="/tmp/cert.pem",
            key_path="/tmp/key.pem"
        )
        
        is_valid, errors = PrinterConnectivityValidator.validate_printer_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid port number" in error for error in errors))
    
    def test_validate_printer_config_invalid_domain(self):
        """Test validation with invalid domain"""
        config = PrinterConfig(
            hostname="printer.local",
            ip_address="192.168.1.100",
            domain="invalid..domain",
            port=443,
            certificate_path="/tmp/cert.pem",
            key_path="/tmp/key.pem"
        )
        
        is_valid, errors = PrinterConnectivityValidator.validate_printer_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid domain format" in error for error in errors))


class TestCertbotIntegration(unittest.TestCase):
    """Unit tests for Certbot integration"""
    
    def test_parse_certbot_success_output(self):
        """Test parsing successful Certbot output"""
        output = """Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/example.com/cert.pem
Key is saved at: /etc/letsencrypt/live/example.com/privkey.pem
Chain is saved at: /etc/letsencrypt/live/example.com/chain.pem
Fullchain is saved at: /etc/letsencrypt/live/example.com/fullchain.pem"""
        
        result = CertbotIntegration.parse_certbot_output(output)
        
        self.assertTrue(result["success"])
        self.assertEqual(result["certificate_path"], "/etc/letsencrypt/live/example.com/cert.pem")
        self.assertEqual(result["key_path"], "/etc/letsencrypt/live/example.com/privkey.pem")
        self.assertEqual(result["chain_path"], "/etc/letsencrypt/live/example.com/chain.pem")
    
    def test_parse_certbot_failure_output(self):
        """Test parsing failed Certbot output"""
        output = "Error: Failed to authenticate"
        
        result = CertbotIntegration.parse_certbot_output(output)
        
        self.assertFalse(result["success"])
        self.assertEqual(result["certificate_path"], "")
    
    def test_validate_certbot_paths_valid(self):
        """Test validation of valid Certbot paths"""
        temp_dir = tempfile.mkdtemp()
        try:
            cert_path = os.path.join(temp_dir, "cert.pem")
            key_path = os.path.join(temp_dir, "key.pem")
            
            open(cert_path, 'w').close()
            open(key_path, 'w').close()
            
            config = PrinterConfig(
                hostname="printer.local",
                ip_address="192.168.1.100",
                domain="printer.example.com",
                certificate_path=cert_path,
                key_path=key_path
            )
            
            is_valid, errors = CertbotIntegration.validate_certbot_paths(config)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_validate_certbot_paths_missing(self):
        """Test validation with missing Certbot paths"""
        config = PrinterConfig(
            hostname="printer.local",
            ip_address="192.168.1.100",
            domain="printer.example.com",
            certificate_path="/nonexistent/cert.pem",
            key_path="/nonexistent/key.pem"
        )
        
        is_valid, errors = CertbotIntegration.validate_certbot_paths(config)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)


class ValidationReport:
    """Generate validation reports"""
    
    @staticmethod
    def generate_json_report(config: PrinterConfig, validation_results: Dict) -> str:
        """Generate JSON validation report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "printer": {
                "hostname": config.hostname,
                "ip_address": config.ip_address,
                "domain": config.domain,
                "port": config.port
            },
            "validation_results": validation_results,
            "overall_status": "PASS" if all(v.get("valid", False) for v in validation_results.values()) else "FAIL"
        }
        return json.dumps(report, indent=2)
    
    @staticmethod
    def generate_text_report(config: PrinterConfig, validation_results: Dict) -> str:
        """Generate human-readable validation report"""
        report_lines = [
            "=" * 70,
            "BROTHER PRINTER TLS CERTIFICATE VALIDATION REPORT",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "PRINTER CONFIGURATION:",
            f"  Hostname: {config.hostname}",
            f"  IP Address: {config.ip_address}",
            f"  Domain: {config.domain}",
            f"  Port: {config.port}",
            "",
            "VALIDATION RESULTS:",
        ]
        
        for check_name, result in validation_results.items():
            status = "✓ PASS" if result.get("valid") else "✗ FAIL"
            report_lines.append(f"  {status}: {check_name}")
            if result.get("message"):
                report_lines.append(f"         {result['message']}")
        
        overall = "PASS" if all(v.get("valid", False) for v in validation_results.values()) else "FAIL"
        report_lines.extend([
            "",
            f"OVERALL STATUS: {overall}",
            "=" * 70
        ])
        
        return "\n".join(report_lines)


def main():
    """Main entry point with CLI"""
    parser = argparse.ArgumentParser(
        description="Validate Brother Printer TLS Certificate Installation",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--hostname",
        type=str,
        default="brother-printer.local",
        help="Printer hostname (default: brother-printer.local)"
    )
    parser.add_argument(
        "--ip-address",
        type=str,
        default="192.168.1.100",
        help="Printer IP address (default: 192.168.1.100)"
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="printer.example.com",
        help="Certificate domain name (default: printer.example.com)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=443,
        help="HTTPS port (default: 443)"
    )
    parser.add_argument(
        "--certificate",
        type=str,
        default="/etc/letsencrypt/live/printer.example.com/fullchain.pem",
        help="Path to certificate file"
    )
    parser.add_argument(
        "--key",
        type=str,
        default="/etc/letsencrypt/live/printer.example.com/privkey.pem",
        help="Path to private key file"
    )
    parser.add_argument(
        "--report-format",
        type=str,
        choices=["json", "text"],
        default="text",
        help="Output report format (default: text)"
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run unit tests instead of validation"
    )
    
    args = parser.parse_args()
    
    if args.run_tests:
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        suite.addTests(loader.loadTestsFromTestCase(TestCertificateValidator))
        suite.addTests(loader.loadTestsFromTestCase(TestPrinterConnectivityValidator))
        suite.addTests(loader.loadTestsFromTestCase(TestCertbotIntegration))
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return 0 if result.wasSuccessful() else 1
    
    config = PrinterConfig(
        hostname=args.hostname,
        ip_address=args.ip_address,
        domain=args.domain,
        port=args.port,
        certificate_path=args.certificate,
        key_path=args.key
    )
    
    validation_results = {}
    
    is_valid, errors = PrinterConnectivityValidator.validate_printer_config(config)
    validation_results["printer_config"] = {
        "valid": is_valid,
        "message": ", ".join(errors) if errors else "Configuration valid"
    }
    
    cert_valid, cert_msg = CertificateValidator.validate_certificate_file(config.certificate_path)
    validation_results["certificate_file"] = {
        "valid": cert_valid,
        "message": cert_msg
    }
    
    key_valid, key_msg = CertificateValidator.validate_private_key_file(config.key_path)
    validation_results["private_key_file"] = {
        "valid": key_valid,
        "message": key_msg
    }
    
    domain_valid, domain_msg = CertificateValidator.validate_domain_format(config.domain)
    validation_results["domain_format"] = {
        "valid": domain_valid,
        "message": domain_msg
    }
    
    ip_valid, ip_msg = CertificateValidator.validate_ip_address(config.ip_address)
    validation_results["ip_address_format"] = {
        "valid": ip_valid,
        "message": ip_msg
    }
    
    if args.report_format == "json":
        report = ValidationReport.generate_json_report(config, validation_results)
    else:
        report = ValidationReport.generate_text_report(config, validation_results)
    
    print(report)
    
    all_valid = all(v.get("valid", False) for v in validation_results.values())
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())