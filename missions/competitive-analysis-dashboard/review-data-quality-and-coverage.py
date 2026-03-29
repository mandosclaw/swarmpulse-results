#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Review data quality and coverage
# Mission: Competitive Analysis Dashboard
# Agent:   @sue
# Date:    2026-03-28T22:06:08.417Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Review data quality and coverage
Mission: Competitive Analysis Dashboard
Agent: @sue
Date: 2024

Audit ingested competitor data for accuracy and completeness.
Validates data schema, detects missing values, checks data freshness,
identifies duplicates, and generates quality metrics with audit reports.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
import hashlib
import statistics
from collections import defaultdict, Counter
import re


class DataQualityAuditor:
    """Audits ingested competitor data for quality and coverage."""

    def __init__(
        self,
        max_age_hours: int = 24,
        missing_threshold: float = 0.1,
        duplicate_threshold: float = 0.05,
    ):
        self.max_age_hours = max_age_hours
        self.missing_threshold = missing_threshold
        self.duplicate_threshold = duplicate_threshold
        self.audit_results = {
            "timestamp": None,
            "summary": {},
            "field_analysis": {},
            "quality_scores": {},
            "issues": [],
            "coverage_report": {},
            "duplicate_analysis": {},
            "freshness_analysis": {},
            "recommendations": [],
        }

    def audit_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run complete audit on ingested data."""
        self.audit_results["timestamp"] = datetime.utcnow().isoformat()

        if not data:
            self.audit_results["issues"].append(
                {"severity": "CRITICAL", "message": "No data provided for audit"}
            )
            return self.audit_results

        self.audit_results["summary"]["total_records"] = len(data)
        self.audit_results["summary"]["audit_date"] = datetime.utcnow().isoformat()

        self._analyze_schema(data)
        self._check_coverage(data)
        self._detect_duplicates(data)
        self._check_freshness(data)
        self._validate_data_types(data)
        self._check_required_fields(data)
        self._generate_recommendations()

        return self.audit_results

    def _analyze_schema(self, data: List[Dict[str, Any]]) -> None:
        """Analyze data schema consistency."""
        if not data:
            return

        field_sets = [set(record.keys()) for record in data]
        most_common_fields = field_sets[0]

        schema_consistency = sum(1 for fs in field_sets if fs == most_common_fields) / len(
            field_sets
        )

        self.audit_results["summary"]["schema_consistency"] = round(schema_consistency, 4)
        self.audit_results["summary"]["fields_found"] = list(most_common_fields)

        if schema_consistency < 0.95:
            self.audit_results["issues"].append(
                {
                    "severity": "HIGH",
                    "field": "schema",
                    "message": f"Schema inconsistency detected. Only {schema_consistency*100:.1f}% records match primary schema",
                }
            )

    def _check_coverage(self, data: List[Dict[str, Any]]) -> None:
        """Analyze field coverage and missing values."""
        if not data:
            return

        all_fields = set()
        for record in data:
            all_fields.update(record.keys())

        coverage = {}
        field_stats = defaultdict(lambda: {"present": 0, "missing": 0, "null": 0})

        for field in all_fields:
            for record in data:
                if field in record:
                    field_stats[field]["present"] += 1
                    if record[field] is None or record[field] == "":
                        field_stats[field]["null"] += 1
                else:
                    field_stats[field]["missing"] += 1

        for field, stats in field_stats.items():
            coverage_pct = stats["present"] / len(data)
            coverage[field] = {
                "coverage_percent": round(coverage_pct * 100, 2),
                "present_count": stats["present"],
                "missing_count": stats["missing"],
                "null_count": stats["null"],
                "data_quality": round((stats["present"] - stats["null"]) / len(data) * 100, 2),
            }

            if coverage_pct < (1 - self.missing_threshold):
                self.audit_results["issues"].append(
                    {
                        "severity": "MEDIUM",
                        "field": field,
                        "message": f"Field '{field}' coverage is {coverage_pct*100:.1f}%, below threshold",
                    }
                )

        self.audit_results["coverage_report"] = coverage

    def _detect_duplicates(self, data: List[Dict[str, Any]]) -> None:
        """Detect duplicate records and near-duplicates."""
        if not data:
            return

        hashes = []
        duplicates = []

        for i, record in enumerate(data):
            record_hash = self._hash_record(record)
            hashes.append(record_hash)

            if record_hash in hashes[: i]:
                duplicates.append({"index": i, "record": record})

        duplicate_pct = len(duplicates) / len(data) if data else 0

        self.audit_results["duplicate_analysis"] = {
            "total_duplicates": len(duplicates),
            "duplicate_percentage": round(duplicate_pct * 100, 2),
            "duplicate_records": duplicates[:10],
        }

        if duplicate_pct > self.duplicate_threshold:
            self.audit_results["issues"].append(
                {
                    "severity": "MEDIUM",
                    "field": "duplicates",
                    "message": f"Duplicate records detected: {duplicate_pct*100:.2f}% of dataset",
                }
            )

    def _hash_record(self, record: Dict[str, Any]) -> str:
        """Generate hash of record for duplicate detection."""
        record_str = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(record_str.encode()).hexdigest()

    def _check_freshness(self, data: List[Dict[str, Any]]) -> None:
        """Check data freshness based on timestamp fields."""
        if not data:
            return

        timestamp_fields = ["timestamp", "date", "created_at", "updated_at", "ingested_at"]
        freshness_data = []

        for record in data:
            for ts_field in timestamp_fields:
                if ts_field in record and record[ts_field]:
                    try:
                        ts_value = record[ts_field]
                        if isinstance(ts_value, str):
                            parsed_ts = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
                        else:
                            parsed_ts = ts_value

                        age = datetime.utcnow() - (
                            parsed_ts
                            if parsed_ts.tzinfo is None
                            else parsed_ts.replace(tzinfo=None)
                        )
                        freshness_data.append(age.total_seconds() / 3600)
                    except (ValueError, TypeError, AttributeError):
                        continue

        if freshness_data:
            max_age = max(freshness_data)
            avg_age = statistics.mean(freshness_data)

            self.audit_results["freshness_analysis"] = {
                "max_age_hours": round(max_age, 2),
                "avg_age_hours": round(avg_age, 2),
                "records_analyzed": len(freshness_data),
            }

            if max_age > self.max_age_hours:
                self.audit_results["issues"].append(
                    {
                        "severity": "HIGH",
                        "field": "freshness",
                        "message": f"Data freshness issue: oldest record is {max_age:.1f} hours old (threshold: {self.max_age_hours}h)",
                    }
                )
        else:
            self.audit_results["freshness_analysis"] = {
                "max_age_hours": None,
                "avg_age_hours": None,
                "records_analyzed": 0,
            }
            self.audit_results["issues"].append(
                {
                    "severity": "MEDIUM",
                    "field": "freshness",
                    "message": "No timestamp fields found for freshness analysis",
                }
            )

    def _validate_data_types(self, data: List[Dict[str, Any]]) -> None:
        """Validate data types in records."""
        if not data:
            return

        type_violations = defaultdict(int)

        for record in data:
            for field, value in record.items():
                if value is None or value == "":
                    continue

                if isinstance(value, str):
                    if field in ["price", "revenue", "employees", "rating"]:
                        try:
                            float(value)
                        except (ValueError, TypeError):
                            type_violations[f"{field}_non_numeric"] += 1
                    elif field in ["date", "created_at", "updated_at", "timestamp"]:
                        try:
                            datetime.fromisoformat(value.replace("Z", "+00:00"))
                        except (ValueError, TypeError, AttributeError):
                            type_violations[f"{field}_invalid_date"] += 1

        for violation, count in type_violations.items():
            if count > 0:
                self.audit_results["issues"].append(
                    {
                        "severity": "LOW",
                        "field": violation,
                        "message": f"Data type validation: {count} records with invalid format for {violation}",
                    }
                )

    def _check_required_fields(self, data: List[Dict[str, Any]]) -> None:
        """Check for required fields in dataset."""
        required_fields = ["id", "name", "timestamp"]
        missing_required = defaultdict(int)

        for record in data:
            for field in required_fields:
                if field not in record or record[field] is None or record[field] == "":
                    missing_required[field] += 1

        for field, count in missing_required.items():
            if count > 0:
                self.audit_results["issues"].append(
                    {
                        "severity": "CRITICAL",
                        "field": field,
                        "message": f"Required field '{field}' missing in {count} records",
                    }
                )

    def _generate_recommendations(self) -> None:
        """Generate recommendations based on audit findings."""
        recommendations = []

        if self.audit_results["duplicate_analysis"].get("total_duplicates", 0) > 0:
            recommendations.append(
                "Remove or consolidate duplicate records to improve data integrity"
            )

        coverage = self.audit_results.get("coverage_report", {})
        for field, stats in coverage.items():
            if stats["coverage_percent"] < 80:
                recommendations.append(
                    f"Improve coverage of field '{field}' (currently {stats['coverage_percent']}%)"
                )

        if self.audit_results["summary"].get("schema_consistency", 1) < 0.95:
            recommendations.append("Standardize data schema across all records")

        freshness = self.audit_results.get("freshness_analysis", {})
        if freshness.get("max_age_hours") and freshness["max_age_hours"] > self.max_age_hours:
            recommendations.append(
                f"Update stale data: {freshness['max_age_hours']} hours old (max threshold: {self.max_age_hours}h)"
            )

        issues_by_severity = defaultdict(int)
        for issue in self.audit_results["issues"]:
            issues_by_severity[issue["severity"]] += 1

        if issues_by_severity["CRITICAL"] > 0:
            recommendations.insert(
                0, f"Address {issues_by_severity['CRITICAL']} critical issues before data use"
            )

        self.audit_results["recommendations"] = recommendations

    def generate_report(self) -> str:
        """Generate human-readable audit report."""
        report = []
        report.append("=" * 70)
        report.append("DATA QUALITY AUDIT REPORT")
        report.append("=" * 70)
        report.append(f"Audit Date: {self.audit_results['timestamp']}")
        report.append("")

        summary = self.audit_results.get("summary", {})
        report.append("SUMMARY")
        report.append("-" * 70)
        report.append(f"Total Records: {summary.get('total_records', 0)}")
        report.append(f"Schema Consistency: {summary.get('schema_consistency', 0)*100:.1f}%")
        report.append(f"Fields Found: {len(summary.get('fields_found', []))}")
        report.append("")

        issues = self.audit_results.get("issues", [])
        if issues:
            report.append("ISSUES FOUND")
            report.append("-" * 70)
            critical = [i for i in issues if i["severity"] == "CRITICAL"]
            high = [i for i in issues if i["severity"] == "HIGH"]
            medium = [i for i in issues if i["severity"] == "MEDIUM"]
            low = [i for i in issues if i["severity"] == "LOW"]

            if critical:
                report.append(f"CRITICAL ({len(critical)}):")
                for issue in critical:
                    report.append(f"  - {issue['message']}")
            if high:
                report.append(f"HIGH ({len(high)}):")
                for issue in high:
                    report.append(f"  - {issue['message']}")
            if medium:
                report.append(f"MEDIUM ({len(medium)}):")
                for issue in medium[:5]:
                    report.append(f"  - {issue['message']}")
            if low:
                report.append(f"LOW ({len(low)}):")
                for issue in low[:3]:
                    report.append(f"  - {issue['message']}")
            report.append("")

        duplicates = self.audit_results.get("duplicate_analysis", {})
        if duplicates:
            report.append("DUPLICATE ANALYSIS")
            report.append("-" * 70)
            report.append(f"Total Duplicates: {duplicates.get('total_duplicates', 0)}")
            report.append(f"Duplicate Percentage: {duplicates.get('duplicate_percentage', 0)}%")
            report.append("")

        freshness = self.audit_results.get("freshness_analysis", {})
        if freshness and freshness.get("max_age_hours") is not None:
            report.append("FRESHNESS ANALYSIS")
            report.append("-" * 70)
            report.append(f"Max Age: {freshness.get('max_age_hours', 'N/A')} hours")
            report.append(f"Avg Age: {freshness.get('avg_age_hours', 'N/A')} hours")
            report.append(f"Records Analyzed: {freshness.get('records_analyzed', 0)}")
            report.append("")

        recommendations = self.audit_results.get("recommendations", [])
        if recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 70)
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")

        report.append("=" * 70)
        return "\n".join(report)


def load_data_file(filepath: str) -> List[Dict[str,