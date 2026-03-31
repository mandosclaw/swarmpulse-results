#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Anomaly scoring + SOAR integration
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @quinn
# Date:    2026-03-31T17:52:36.425Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Anomaly scoring + SOAR integration for SaaS Breach Detection
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @quinn
DATE: 2025

Implements unsupervised anomaly detection on SaaS audit logs with scoring,
SOAR alerting, and automatic session revocation for critical threats.
"""

import argparse
import json
import sys
import time
import math
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import statistics


class ThreatLevel(Enum):
    """Threat severity levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AuditLog:
    """Represents a single audit log entry."""
    timestamp: str
    user_id: str
    user_email: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    service: str
    success: bool
    details: Dict[str, Any]


@dataclass
class AnomalyScore:
    """Represents computed anomaly metrics for a user."""
    user_id: str
    user_email: str
    total_score: float
    threat_level: ThreatLevel
    anomalies: List[str]
    timestamp: str
    session_id: str
    service: str


class BehavioralBaseline:
    """Computes and stores behavioral baselines for users."""

    def __init__(self):
        self.user_profiles: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "actions": defaultdict(int),
                "ips": defaultdict(int),
                "user_agents": defaultdict(int),
                "daily_action_count": [],
                "peak_hours": [],
                "services": defaultdict(int),
                "resources": defaultdict(int),
            }
        )
        self.global_stats = {
            "total_logs": 0,
            "avg_daily_actions": 0,
            "common_actions": defaultdict(int),
        }

    def add_log(self, log: AuditLog) -> None:
        """Add a log entry to baseline."""
        profile = self.user_profiles[log.user_id]
        profile["actions"][log.action] += 1
        profile["ips"][log.ip_address] += 1
        profile["user_agents"][log.user_agent] += 1
        profile["services"][log.service] += 1
        profile["resources"][log.resource] += 1

        self.global_stats["total_logs"] += 1
        self.global_stats["common_actions"][log.action] += 1

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get baseline profile for a user."""
        return self.user_profiles.get(user_id, {})

    def get_action_frequency(self, user_id: str, action: str) -> float:
        """Get frequency of an action for user (normalized 0-1)."""
        profile = self.user_profiles.get(user_id, {})
        if not profile or not profile.get("actions"):
            return 0.0
        actions = profile["actions"]
        total = sum(actions.values())
        if total == 0:
            return 0.0
        return actions.get(action, 0) / total

    def get_ip_commonality(self, user_id: str, ip: str) -> float:
        """Get commonality of IP for user (0-1)."""
        profile = self.user_profiles.get(user_id, {})
        if not profile or not profile.get("ips"):
            return 0.0
        ips = profile["ips"]
        total = sum(ips.values())
        if total == 0:
            return 0.0
        return ips.get(ip, 0) / total

    def get_service_frequency(self, user_id: str, service: str) -> float:
        """Get frequency of service access for user (0-1)."""
        profile = self.user_profiles.get(user_id, {})
        if not profile or not profile.get("services"):
            return 0.0
        services = profile["services"]
        total = sum(services.values())
        if total == 0:
            return 0.0
        return services.get(service, 0) / total


class AnomalyDetector:
    """Detects anomalies in SaaS audit logs."""

    def __init__(self, baseline: BehavioralBaseline):
        self.baseline = baseline
        self.credential_stuffing_threshold = 0.7
        self.impossible_travel_threshold = 0.8
        self.mass_download_threshold = 0.75
        self.privilege_creep_threshold = 0.7

    def score_credential_stuffing(self, logs: List[AuditLog]) -> Tuple[float, str]:
        """Detect credential stuffing: failed logins from different IPs."""
        failed_logins = [
            log
            for log in logs
            if log.action == "LOGIN" and not log.success
        ]

        if not failed_logins:
            return 0.0, ""

        unique_ips = set(log.ip_address for log in failed_logins)
        failure_rate = len(failed_logins) / len(logs) if logs else 0

        if len(failed_logins) > 5 and len(unique_ips) > 1 and failure_rate > 0.3:
            score = min(
                1.0,
                (len(failed_logins) / 10.0) * (len(unique_ips) / 5.0) * failure_rate,
            )
            return score, f"Credential_Stuffing({len(failed_logins)}_failures_{len(unique_ips)}_IPs)"

        return 0.0, ""

    def score_impossible_travel(self, logs: List[AuditLog]) -> Tuple[float, str]:
        """Detect impossible travel: rapid IP changes over physical distance."""
        # Simulate IP geolocation mapping
        ip_location = {
            "1.2.3.4": (40.7128, -74.0060),  # NYC
            "5.6.7.8": (51.5074, -0.1278),  # London
            "9.10.11.12": (35.6762, 139.6503),  # Tokyo
            "13.14.15.16": (-33.8688, 151.2093),  # Sydney
            "192.168.1.100": (40.7128, -74.0060),  # Internal
            "10.0.0.50": (40.7128, -74.0060),  # Internal
        }

        if len(logs) < 2:
            return 0.0, ""

        sorted_logs = sorted(logs, key=lambda x: x.timestamp)
        max_score = 0.0
        anomaly_desc = ""

        for i in range(len(sorted_logs) - 1):
            log1 = sorted_logs[i]
            log2 = sorted_logs[i + 1]

            # Skip internal IPs
            if (
                log1.ip_address.startswith("192.168.")
                or log1.ip_address.startswith("10.")
            ):
                continue
            if (
                log2.ip_address.startswith("192.168.")
                or log2.ip_address.startswith("10.")
            ):
                continue

            if log1.ip_address != log2.ip_address:
                loc1 = ip_location.get(
                    log1.ip_address, (40.7128, -74.0060)
                )  # Default to NYC
                loc2 = ip_location.get(
                    log2.ip_address, (40.7128, -74.0060)
                )

                # Great circle distance approximation (km)
                dlat = loc2[0] - loc1[0]
                dlon = loc2[1] - loc1[1]
                distance = math.sqrt(dlat * dlat + dlon * dlon) * 111  # km per degree

                # Parse timestamps
                try:
                    t1 = datetime.fromisoformat(log1.timestamp)
                    t2 = datetime.fromisoformat(log2.timestamp)
                except (ValueError, TypeError):
                    continue

                time_diff_hours = (t2 - t1).total_seconds() / 3600

                if time_diff_hours > 0:
                    required_speed = distance / time_diff_hours  # km/h
                    # Impossible if > 900 km/h (faster than commercial flight)
                    if required_speed > 900:
                        score = min(1.0, required_speed / 2000)
                        if score > max_score:
                            max_score = score
                            anomaly_desc = f"Impossible_Travel({distance:.0f}km_in_{time_diff_hours:.1f}h_{log1.ip_address}_to_{log2.ip_address})"

        return max_score, anomaly_desc

    def score_mass_download(self, logs: List[AuditLog]) -> Tuple[float, str]:
        """Detect mass download: excessive file downloads."""
        download_logs = [
            log
            for log in logs
            if log.action in ["DOWNLOAD", "EXPORT"]
            and log.success
        ]

        if not download_logs:
            return 0.0, ""

        # Baseline: typical users download 5-20 files per day
        baseline_freq = self.baseline.get_action_frequency(
            logs[0].user_id, "DOWNLOAD"
        )

        download_count = len(download_logs)
        total_logs = len(logs)
        download_rate = download_count / total_logs if total_logs > 0 else 0

        if download_count > 50 or download_rate > 0.4:
            score = min(
                1.0, (download_count / 100.0) + abs(download_rate - baseline_freq)
            )
            return score, f"Mass_Download({download_count}_downloads_{download_rate:.1%}_rate)"

        return 0.0, ""

    def score_privilege_creep(self, logs: List[AuditLog]) -> Tuple[float, str]:
        """Detect privilege creep: accessing resources/services not typically used."""
        user_id = logs[0].user_id if logs else ""

        if not logs:
            return 0.0, ""

        # Check for new service access
        services_accessed = set(log.service for log in logs)
        baseline_profile = self.baseline.get_user_profile(user_id)
        baseline_services = set(baseline_profile.get("services", {}).keys())

        new_services = services_accessed - baseline_services
        suspicious_service_access = 0

        for service in services_accessed:
            freq = self.baseline.get_service_frequency(user_id, service)
            # Flag if service accessed but rarely in baseline
            if freq < 0.05 and len(baseline_services) > 0:
                suspicious_service_access += 1

        # Check for new resource access patterns
        resources_accessed = set(log.resource for log in logs)
        baseline_resources = set(baseline_profile.get("resources", {}).keys())
        new_resources = resources_accessed - baseline_resources

        if len(new_resources) > len(resources_accessed) * 0.5 and len(
            resources_accessed
        ) > 10:
            score = min(
                1.0,
                (len(new_resources) / len(resources_accessed))
                + (suspicious_service_access / max(1, len(services_accessed))),
            )
            return score, f"Privilege_Creep({len(new_services)}_new_services_{len(new_resources)}_new_resources)"

        return 0.0, ""

    def score_anomaly(
        self, logs: List[AuditLog]
    ) -> Tuple[float, List[str]]:
        """Compute overall anomaly score."""
        if not logs:
            return 0.0, []

        scores = []
        anomalies = []

        # Credential stuffing
        cred_score, cred_desc = self.score_credential_stuffing(logs)
        scores.append(cred_score * 0.25)
        if cred_score > 0.3:
            anomalies.append(cred_desc)

        # Impossible travel
        travel_score, travel_desc = self.score_impossible_travel(logs)
        scores.append(travel_score * 0.30)
        if travel_score > 0.3:
            anomalies.append(travel_desc)

        # Mass download
        download_score, download_desc = self.score_mass_download(logs)
        scores.append(download_score * 0.25)
        if download_score > 0.3:
            anomalies.append(download_desc)

        # Privilege creep
        priv_score, priv_desc = self.score_privilege_creep(logs)
        scores.append(priv_score * 0.20)
        if priv_score > 0.3:
            anomalies.append(priv_desc)

        total_score = sum(scores)
        return min(1.0, total_score), anomalies

    def get_threat_level(self, score: float) -> ThreatLevel:
        """Map anomaly score to threat level."""
        if score >= 0.8:
            return ThreatLevel.CRITICAL
        elif score >= 0.6:
            return ThreatLevel.HIGH
        elif score >= 0.4:
            return ThreatLevel.MEDIUM
        else:
            return ThreatLevel.LOW


class SOARIntegration:
    """Simulates SOAR integration for alert handling."""

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.revoked_sessions: List[str] = []

    def send_alert(
        self, anomaly_score: AnomalyScore, auto_revoke: bool = False
    ) -> Dict[str, Any]:
        """Send alert to SOAR system."""
        alert = {
            "alert_id": self._generate_alert_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": anomaly_score.user_id,
            "user_email": anomaly_score.user_email,
            "service": anomaly_score.service,
            "anomaly_score": anomaly_score.total_score,
            "threat_level": anomaly_score.threat_level.name,
            "anomalies": anomaly_score.anomalies,
            "auto_revoke_triggered": False,
            "session_id": anomaly_score.session_id,
        }

        if auto_revoke and anomaly_score.threat_level == ThreatLevel.CRITICAL:
            alert["auto_revoke_triggered"] = True
            self._revoke_session(anomaly_score.session_id, anomaly_score.user_id)

        self.alerts.append(alert)
        return alert

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        return f"ALERT-{int(time.time() * 1000)}"

    def _revoke_session(self, session_id: str, user_id: str) -> None:
        """Revoke user session."""
        revocation = f"{user_id}:{session_id}"
        self.revoked_sessions.append(revocation)

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Return all alerts."""
        return self.alerts

    def get_revoked_sessions(self) -> List[str]:
        """Return revoked sessions."""
        return self.revoked_sessions


class AuditLogParser:
    """Parses audit log data."""

    @staticmethod
    def parse_log(log_dict: Dict[str, Any]) -> AuditLog:
        """Parse a log dictionary into AuditLog."""
        return AuditLog(
            timestamp=log_dict.get("timestamp", ""),
            user_id=log_dict.get("user_id", ""),
            user_email=log_dict.get("user_email", ""),
            action=log_dict.get("action", ""),
            resource=log_dict.get("resource", ""),
            ip_address=log_dict.get("ip_address", ""),
            user_agent=log_dict.get("user_agent", ""),
            service=log_dict.get("service", ""),
            success=log_dict.get("success", True),
            details=log_dict.get("details", {}),
        )


class BehaviorAnalyticsEngine:
    """Main engine for behavioral analytics."""

    def __init__(self, auto_revoke_critical: bool = True):
        self.baseline = BehavioralBaseline()
        self.detector = AnomalyDetector(self.baseline)
        self.soar = SOARIntegration()
        self.auto_revoke_critical = auto_revoke_critical
        self.user_logs: Dict[str, List[AuditLog]] = defaultdict(list)

    def ingest_logs(self, logs: List[AuditLog]) -> None:
        """Ingest logs and build baseline."""
        for log in logs:
            self.baseline.add_log(log)
            self.user_logs[log.user_id].append(log)

    def analyze_user(self, user_id: str) -> List[AnomalyScore]:
        """Analyze a user's logs and generate anomaly scores."""
        if user_id not in self.user_logs:
            return []

        logs = self.user_logs[user_id]
        if not logs:
            return []

        # Group logs by service
        logs_by_service = defaultdict(list)
        for log in logs:
            logs_by_service[log.service].append(log)

        anomaly_scores = []

        for service, service_logs in logs_by_service.items():
            score, anomalies = self.detector.score_anomaly(service_logs)
            threat_level = self.detector.get_threat_level(score)

            # Use first log for user info, hash of logs for session ID
            first_log = service_logs[0]
            session_hash = hashlib.md5(
                f"{user_id}{service}{int(time.time())}".encode()
            ).hexdigest()[:12]

            anomaly_score = AnomalyScore(
                user_id=user_id,
                user_email=first_log.user_email,
                total_score=score,
                threat_level=threat_level,
                anomalies=anomalies,
                timestamp=datetime.utcnow().isoformat(),
                session_id=session_hash,
                service=service,
            )

            anomaly_scores.append(anomaly_score)

            # Send to SOAR
            self.soar.send_alert(anomaly_score, auto_revoke=self.auto_revoke_critical)

        return anomaly_scores

    def analyze_all_users(self) -> Dict[str, List[AnomalyScore]]:
        """Analyze all users and return results."""
        results = {}
        for user_id in self.user_logs.keys():
            results[user_id] = self.analyze_user(user_id)
        return results

    def export_report(self) -> Dict[str, Any]:
        """Export comprehensive analysis report."""
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_users_analyzed": len(self.user_logs),
            "total_logs_ingested": self.baseline.global_stats["total_logs"],
            "critical_alerts": len(
                [
                    a
                    for a in self.soar.get_alerts()
                    if a["threat_level"] == "CRITICAL"
                ]
            ),
            "high_alerts": len(
                [a for a in self.soar.get_alerts() if a["threat_level"] == "HIGH"]
            ),
            "revoked_sessions": len(self.soar.get_revoked_sessions()),
            "alerts": self.soar.get_alerts(),
            "revoked_sessions_list": self.soar.get_revoked_sessions(),
        }


def generate_sample_logs() -> List[Dict[str, Any]]:
    """Generate realistic sample audit logs for demo."""
    base_time = datetime.utcnow()
    logs = []

    # Normal user behavior
    for i in range(30):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=i * 2)).isoformat(),
                "user_id": "user001",
                "user_email": "john.doe@company.com",
                "action": "LOGIN",
                "resource": "workspace",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Chrome",
                "service": "google-workspace",
                "success": True,
                "details": {},
            }
        )
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=i * 2 + 1)).isoformat(),
                "user_id": "user001",
                "user_email": "john.doe@company.com",
                "action": "VIEW_DOCUMENT",
                "resource": f"doc_{i}",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Chrome",
                "service": "google-workspace",
                "success": True,
                "details": {},
            }
        )

    # Suspicious user: credential stuffing + impossible travel
    for i in range(8):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=80 - i * 5)).isoformat(),
                "user_id": "user002",
                "user_email": "jane.smith@company.com",
                "action": "LOGIN",
                "resource": "workspace",
                "ip_address": ["1.2.3.4", "5.6.7.8", "9.10.11.12", "13.14.15.16"][
                    i % 4
                ],
                "user_agent": "Mozilla/5.0 Firefox",
                "service": "google-workspace",
                "success": i % 3 != 0,  # Some failures
                "details": {},
            }
        )

    # Failed logins from different IPs
    for i in range(6):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=40 + i)).isoformat(),
                "user_id": "user002",
                "user_email": "jane.smith@company.com",
                "action": "LOGIN",
                "resource": "workspace",
                "ip_address": f"203.0.113.{100 + i}",
                "user_agent": "Python-Requests/2.28",
                "service": "google-workspace",
                "success": False,
                "details": {"error": "invalid_credentials"},
            }
        )

    # Mass download activity
    for i in range(75):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=100 + i * 1)).isoformat(),
                "user_id": "user003",
                "user_email": "bob.wilson@company.com",
                "action": "DOWNLOAD",
                "resource": f"file_{i}.xlsx",
                "ip_address": "10.0.0.50",
                "user_agent": "Mozilla/5.0 Safari",
                "service": "microsoft-365",
                "success": True,
                "details": {"file_size_mb": 5 + i % 10},
            }
        )

    # Normal M365 activity
    for i in range(20):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=i * 3)).isoformat(),
                "user_id": "user004",
                "user_email": "alice.johnson@company.com",
                "action": "VIEW_EMAIL",
                "resource": f"email_{i}",
                "ip_address": "192.168.1.101",
                "user_agent": "Mozilla/5.0 Chrome",
                "service": "microsoft-365",
                "success": True,
                "details": {},
            }
        )

    # Privilege creep: accessing Salesforce when user normally uses Workspace
    for i in range(5):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=50 + i * 2)).isoformat(),
                "user_id": "user001",
                "user_email": "john.doe@company.com",
                "action": "ACCESS_DASHBOARD",
                "resource": "sales_dashboard",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Chrome",
                "service": "salesforce",
                "success": True,
                "details": {"dashboard_id": "dash_001"},
            }
        )

    # GitHub suspicious activity
    for i in range(10):
        logs.append(
            {
                "timestamp": (base_time - timedelta(minutes=30 + i * 2)).isoformat(),
                "user_id": "user005",
                "user_email": "dev.hacker@company.com",
                "action": "CLONE_REPO",
                "resource": f"repo_{i}",
                "ip_address": "203.0.113.50",
                "user_agent": "git/2.40",
                "service": "github",
                "success": True,
                "details": {"repo_size_mb": 100 + i * 50},
            }
        )

    return logs


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SaaS Breach Detection via Behavioral Analytics"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to JSON log file (one log per line)",
        default=None,
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Path to write JSON report",
        default="breach_detection_report.json",
    )
    parser.add_argument(
        "--auto-revoke",
        action="store_true",
        help="Auto-revoke sessions on critical threats",
        default=True,
    )
    parser.add_argument(
        "--no-auto-revoke",
        action="store_true",
        help="Disable auto-revoke",
        default=False,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print alerts to stdout",
        default=False,
    )

    args = parser.parse_args()

    # Determine auto-revoke setting
    auto_revoke = args.auto_revoke and not args.no_auto_revoke

    # Load logs
    if args.log_file:
        try:
            logs_data = []
            with open(args.log_file, "r") as f:
                for line in f:
                    if line.strip():
                        logs_data.append(json.loads(line))
        except FileNotFoundError:
            print(f"Error: Log file '{args.log_file}' not found", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in log file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Use sample data
        logs_data = generate_sample_logs()

    # Parse logs
    logs = [AuditLogParser.parse_log(log_dict) for log_dict in logs_data]

    # Initialize engine
    engine = BehaviorAnalyticsEngine(auto_revoke_critical=auto_revoke)

    # Ingest and analyze
    engine.ingest_logs(logs)
    results = engine.analyze_all_users()

    # Generate report
    report = engine.export_report()

    # Print results if verbose
    if args.verbose:
        for user_id, scores in results.items():
            for score in scores:
                print(f"\n[{score.threat_level.name}] User: {score.user_email}")
                print(f"  Score: {score.total_score:.2f}")
                print(f"  Service: {score.service}")
                if score.anomalies:
                    print(f"  Anomalies:")
                    for anomaly in score.anomalies:
                        print(f"    - {anomaly}")

    # Write report
    with open(args.output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Analysis complete. Report written to: {args.output_file}")
    print(f"  Critical Alerts: {report['critical_alerts']}")
    print(f"  High Alerts: {report['high_alerts']}")
    print(f"  Sessions Revoked: {report['revoked_sessions']}")


if __name__ == "__main__":
    main()