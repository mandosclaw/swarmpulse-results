#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Audit log ingestion (multi-source)
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @sue
# Date:    2026-03-29T13:08:09.681Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
MISSION: SaaS Breach Detection via Behavioral Analytics
CATEGORY: Engineering
TASK: Audit log ingestion (multi-source)
DESCRIPTION: Unified ingest for Google, M365, Salesforce, GitHub audit events. Normalize to CEF.
AGENT: @sue
DATE: 2025-01-15
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib
import random
import string
from urllib.parse import urljoin


class AuditSourceType(Enum):
    """Supported audit log sources."""
    GOOGLE_WORKSPACE = "google_workspace"
    M365 = "m365"
    SALESFORCE = "salesforce"
    GITHUB = "github"


@dataclass
class CEFEvent:
    """Common Event Format (CEF) normalized event."""
    cef_version: str = "0"
    device_vendor: str = ""
    device_product: str = ""
    device_version: str = ""
    device_event_class_id: str = ""
    name: str = ""
    severity: str = "3"
    extensions: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extensions is None:
            self.extensions = {}
    
    def to_cef_string(self) -> str:
        """Convert CEF event to CEF log format string."""
        header = f"CEF:{self.cef_version}|{self.device_vendor}|{self.device_product}|{self.device_version}|{self.device_event_class_id}|{self.name}|{self.severity}|"
        
        extension_parts = []
        for key, value in self.extensions.items():
            if value is not None:
                sanitized_value = str(value).replace("|", "\\|").replace("=", "\\=").replace("\n", "\\n")
                extension_parts.append(f"{key}={sanitized_value}")
        
        return header + " ".join(extension_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "cef_version": self.cef_version,
            "device_vendor": self.device_vendor,
            "device_product": self.device_product,
            "device_version": self.device_version,
            "device_event_class_id": self.device_event_class_id,
            "name": self.name,
            "severity": self.severity,
            "extensions": self.extensions
        }
        return result


class GoogleWorkspaceParser:
    """Parser for Google Workspace audit logs."""
    
    @staticmethod
    def normalize(event: Dict[str, Any]) -> CEFEvent:
        """Normalize Google Workspace event to CEF."""
        timestamp = event.get("id", {}).get("time", datetime.utcnow().isoformat())
        actor = event.get("actor", {}).get("email", "unknown")
        event_type = event.get("events", [{}])[0].get("type", "UNKNOWN")
        
        cef = CEFEvent(
            device_vendor="Google",
            device_product="Workspace",
            device_version="1.0",
            device_event_class_id=event_type,
            name=f"Google Workspace: {event_type}",
            severity="3"
        )
        
        cef.extensions = {
            "rt": timestamp,
            "suser": actor,
            "sourceIP": event.get("ipAddress", "unknown"),
            "eventType": event_type,
            "eventDetails": json.dumps(event.get("events", [{}])[0].get("parameters", {})),
            "orgUnit": event.get("orgUnitPath", "/"),
            "customAttributes": json.dumps(event.get("customAttributes", {}))
        }
        
        return cef


class M365Parser:
    """Parser for Microsoft 365 audit logs."""
    
    @staticmethod
    def normalize(event: Dict[str, Any]) -> CEFEvent:
        """Normalize M365 event to CEF."""
        timestamp = event.get("CreationTime", datetime.utcnow().isoformat())
        actor = event.get("UserId", "unknown")
        operation = event.get("Operation", "UNKNOWN")
        
        cef = CEFEvent(
            device_vendor="Microsoft",
            device_product="365",
            device_version="1.0",
            device_event_class_id=operation,
            name=f"M365: {operation}",
            severity="3"
        )
        
        cef.extensions = {
            "rt": timestamp,
            "suser": actor,
            "sourceIP": event.get("ClientIP", "unknown"),
            "eventType": operation,
            "workload": event.get("Workload", "unknown"),
            "recordType": event.get("RecordType", "unknown"),
            "objectId": event.get("ObjectId", ""),
            "resultStatus": event.get("ResultStatus", "Success"),
            "userAgent": event.get("UserAgent", ""),
            "auditData": json.dumps(event.get("AuditData", {}))
        }
        
        return cef


class SalesforceParser:
    """Parser for Salesforce audit logs."""
    
    @staticmethod
    def normalize(event: Dict[str, Any]) -> CEFEvent:
        """Normalize Salesforce event to CEF."""
        timestamp = event.get("TIMESTAMP_DERIVED", datetime.utcnow().isoformat())
        user = event.get("USER_ID", "unknown")
        action = event.get("ACTION", "UNKNOWN")
        
        cef = CEFEvent(
            device_vendor="Salesforce",
            device_product="Audit",
            device_version="1.0",
            device_event_class_id=action,
            name=f"Salesforce: {action}",
            severity="3"
        )
        
        cef.extensions = {
            "rt": timestamp,
            "suser": user,
            "sourceIP": event.get("SOURCE_IP", "unknown"),
            "eventType": action,
            "entityType": event.get("ENTITY_TYPE", ""),
            "entityId": event.get("ENTITY_ID", ""),
            "delegateUser": event.get("DELEGATE_USER", ""),
            "displayName": event.get("DISPLAY_NAME", ""),
            "section": event.get("SECTION", ""),
            "details": json.dumps(event.get("details", {}))
        }
        
        return cef


class GitHubParser:
    """Parser for GitHub audit logs."""
    
    @staticmethod
    def normalize(event: Dict[str, Any]) -> CEFEvent:
        """Normalize GitHub event to CEF."""
        timestamp = event.get("@timestamp", datetime.utcnow().isoformat())
        actor = event.get("actor", "unknown")
        action = event.get("action", "UNKNOWN")
        
        cef = CEFEvent(
            device_vendor="GitHub",
            device_product="Enterprise",
            device_version="1.0",
            device_event_class_id=action,
            name=f"GitHub: {action}",
            severity="3"
        )
        
        cef.extensions = {
            "rt": timestamp,
            "suser": actor,
            "sourceIP": event.get("actor_ip", "unknown"),
            "eventType": action,
            "repository": event.get("repository", ""),
            "organization": event.get("org", ""),
            "userAgent": event.get("user_agent", ""),
            "operationType": event.get("operation_type", ""),
            "result": event.get("result", "unknown"),
            "auditLog": json.dumps({k: v for k, v in event.items() if k not in ["@timestamp", "actor", "action", "actor_ip", "user_agent"]})
        }
        
        return cef


class AuditLogIngestionEngine:
    """Unified audit log ingestion and normalization engine."""
    
    def __init__(self, verbose: bool = False, output_format: str = "json"):
        self.verbose = verbose
        self.output_format = output_format
        self.parsers: Dict[AuditSourceType, Any] = {
            AuditSourceType.GOOGLE_WORKSPACE: GoogleWorkspaceParser(),
            AuditSourceType.M365: M365Parser(),
            AuditSourceType.SALESFORCE: SalesforceParser(),
            AuditSourceType.GITHUB: GitHubParser(),
        }
        self.normalized_events: List[CEFEvent] = []
        self.ingestion_stats = {
            "total_events": 0,
            "successful": 0,
            "failed": 0,
            "by_source": {}
        }
    
    def ingest_event(self, source: AuditSourceType, raw_event: Dict[str, Any]) -> Tuple[Optional[CEFEvent], Optional[str]]:
        """Ingest and normalize a single event."""
        self.ingestion_stats["total_events"] += 1
        
        if source not in self.ingestion_stats["by_source"]:
            self.ingestion_stats["by_source"][source.value] = {"total": 0, "success": 0, "failed": 0}
        
        self.ingestion_stats["by_source"][source.value]["total"] += 1
        
        try:
            parser = self.parsers.get(source)
            if not parser:
                raise ValueError(f"No parser available for source: {source.value}")
            
            normalized_event = parser.normalize(raw_event)
            self.normalized_events.append(normalized_event)
            self.ingestion_stats["successful"] += 1
            self.ingestion_stats["by_source"][source.value]["success"] += 1
            
            if self.verbose:
                print(f"[✓] Ingested {source.value} event: {normalized_event.name}", file=sys.stderr)
            
            return normalized_event, None
        
        except Exception as e:
            error_msg = f"Failed to ingest {source.value} event: {str(e)}"
            self.ingestion_stats["failed"] += 1
            self.ingestion_stats["by_source"][source.value]["failed"] += 1
            
            if self.verbose:
                print(f"[✗] {error_msg}", file=sys.stderr)
            
            return None, error_msg
    
    def ingest_batch(self, source: AuditSourceType, raw_events: List[Dict[str, Any]]) -> List[CEFEvent]:
        """Ingest and normalize a batch of events from a source."""
        normalized = []
        for event in raw_events:
            cef_event, error = self.ingest_event(source, event)
            if cef_event:
                normalized.append(cef_event)
        
        if self.verbose:
            print(f"[i] Batch ingestion from {source.value}: {len(normalized)}/{len(raw_events)} successful", file=sys.stderr)
        
        return normalized
    
    def get_normalized_events(self) -> List[CEFEvent]:
        """Get all normalized events."""
        return self.normalized_events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        return self.ingestion_stats
    
    def export_cef(self) -> str:
        """Export all normalized events in CEF format."""
        lines = [event.to_cef_string() for event in self.normalized_events]
        return "\n".join(lines)
    
    def export_json(self) -> str:
        """Export all normalized events in JSON format."""
        events_dicts = [event.to_dict() for event in self.normalized_events]
        return json.dumps(events_dicts, indent=2)
    
    def export(self, format_type: str = None) -> str:
        """Export normalized events in specified format."""
        fmt = format_type or self.output_format
        if fmt.lower() == "cef":
            return self.export_cef()
        else:
            return self.export_json()


def generate_sample_google_event() -> Dict[str, Any]:
    """Generate sample Google Workspace audit event."""
    return {
        "kind": "admin#reports#activity",
        "etag": "test_etag",
        "id": {
            "time": datetime.utcnow().isoformat(),
            "uniqueQualifier": "12345",
            "applicationName": "admin",
            "customerId": "C0000xxxxxx"
        },
        "actor": {
            "callerType": "USER",
            "email": f"admin{random.randint(1,5)}@example.com",
            "profileId": "12345"
        },
        "ipAddress": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
        "events": [{
            "type": random.choice(["LOGIN", "CREATE_USER", "CHANGE_PASSWORD", "DELETE_USER", "DOWNLOAD", "MOVE"]),
            "name": "login",
            "parameters": {
                "login_type": random.choice(["basic", "oauth", "saml"]),
                "is_suspicious": random.choice([True, False])
            }
        }],
        "orgUnitPath": f"/org{random.randint(1,3)}",
        "customAttributes": {"department": random.choice(["Engineering", "Sales", "HR", "Finance"])}
    }


def generate_sample_m365_event() -> Dict[str, Any]:
    """Generate sample Microsoft 365 audit event."""
    return {
        "CreationTime": datetime.utcnow().isoformat(),
        "UserId": f"user{random.randint(1,10)}@company.onmicrosoft.com",
        "Operation": random.choice(["UserLoggedIn", "FileAccessed", "FileModified", "FileDeleted", "Send", "Add-MailboxPermission"]),
        "AuditData": {
            "AzureActiveDirectoryEventUri": "https://manage.office.com/api/v1.0/activities",
            "ResultStatus": "Success"
        },
        "ClientIP": f"203.0.113.{random.randint(1,255)}",
        "Workload": random.choice(["Exchange", "SharePoint", "Teams", "AzureAD"]),
        "RecordType": random.choice(["ExchangeAdmin", "ExchangeItem", "SharePoint", "AzureActiveDirectory"]),
        "ObjectId": f"object{random.randint(1000,9999)}",
        "ResultStatus": "Success",
        "UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "AuditData": json.dumps({"details": f"Operation details {random.randint(1,100)}"})
    }


def generate_sample_salesforce_event() -> Dict[str, Any]:
    """Generate sample Salesforce audit event."""
    timestamp = (datetime.utcnow() - timedelta(minutes=random.randint(0,60))).isoformat()
    return {
        "TIMESTAMP_DERIVED": timestamp,
        "USER_ID": f"user_{random.randint(100,999)}",
        "USER_IDLE_TIMEOUT_IN_MINUTES": str(random.randint(15,480)),
        "ACTION": random.choice(["Login", "ApiCallStart", "Report", "BulkApiV2Job", "QueryMore", "Update", "Delete"]),
        "ENTITY_TYPE": random.choice(["Account", "Contact", "Lead", "Opportunity", "Task"]),
        "ENTITY_ID": f"001{random.randint(100000000,999999999)}",
        "SOURCE_IP": f"198.51.100.{random.randint(1,255)}",
        "DELEGATE_