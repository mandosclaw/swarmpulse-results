#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement anomaly scoring engine
# Mission: SaaS Breach Detection via Behavioral Analytics
# Agent:   @echo
# Date:    2026-03-28T22:06:37.440Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement anomaly scoring engine
MISSION: SaaS Breach Detection via Behavioral Analytics
AGENT: @echo
DATE: 2024
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import statistics
import math
from enum import Enum


class AnomalyLevel(Enum):
    """Anomaly severity levels"""
    NORMAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AuditLog:
    """Audit log entry structure"""
    timestamp: str
    user_id: str
    action: str
    resource: str
    ip_address: str
    user_agent: str
    success: bool
    details: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditLog':
        """Create AuditLog from dictionary"""
        return cls(
            timestamp=data.get('timestamp', ''),
            user_id=data.get('user_id', ''),
            action=data.get('action', ''),
            resource=data.get('resource', ''),
            ip_address=data.get('ip_address', ''),
            user_agent=data.get('user_agent', ''),
            success=data.get('success', True),
            details=data.get('details', {})
        )


@dataclass
class AnomalyScore:
    """Anomaly score result"""
    user_id: str
    timestamp: str
    overall_score: float
    level: str
    contributing_factors: Dict[str, float]
    is_anomaly: bool
    alert_message: str


class BehavioralBaseline:
    """User behavioral baseline from historical data"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.login_times = []
        self.common_ips = {}
        self.common_resources = {}
        self.common_actions = {}
        self.avg_session_duration = 0.0
        self.typical_user_agents = set()
        self.login_count = 0
        self.failed_login_count = 0
        self.active_hours = set()


class AnomalyDetectionEngine:
    """ML-powered anomaly scoring engine for SaaS breach detection"""
    
    def __init__(self, 
                 baseline_window_days: int = 30,
                 anomaly_threshold: float = 0.6,
                 critical_threshold: float = 0.85):
        """
        Initialize anomaly detection engine
        
        Args:
            baseline_window_days: Days of historical data to use for baseline
            anomaly_threshold: Score above which activity is flagged as anomalous
            critical_threshold: Score above which activity is critical
        """
        self.baseline_window_days = baseline_window_days
        self.anomaly_threshold = anomaly_threshold
        self.critical_threshold = critical_threshold
        self.baselines: Dict[str, BehavioralBaseline] = {}
        self.audit_logs: List[AuditLog] = []
        
    def ingest_audit_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Ingest audit logs for baseline creation"""
        for log_data in logs:
            log = AuditLog.from_dict(log_data)
            self.audit_logs.append(log)
            
    def build_baselines(self) -> None:
        """Build behavioral baselines from ingested audit logs"""
        cutoff_time = datetime.now() - timedelta(days=self.baseline_window_days)
        
        for log in self.audit_logs:
            try:
                log_time = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue
                
            if log_time < cutoff_time:
                continue
            
            if log.user_id not in self.baselines:
                self.baselines[log.user_id] = BehavioralBaseline(log.user_id)
            
            baseline = self.baselines[log.user_id]
            
            baseline.login_times.append(log_time.hour)
            baseline.active_hours.add(log_time.hour)
            
            if log.ip_address:
                baseline.common_ips[log.ip_address] = baseline.common_ips.get(log.ip_address, 0) + 1
            
            baseline.common_resources[log.resource] = baseline.common_resources.get(log.resource, 0) + 1
            baseline.common_actions[log.action] = baseline.common_actions.get(log.action, 0) + 1
            
            if log.user_agent:
                baseline.typical_user_agents.add(log.user_agent)
            
            if log.action == 'login':
                baseline.login_count += 1
                if not log.success:
                    baseline.failed_login_count += 1
    
    def _score_time_anomaly(self, user_id: str, log: AuditLog) -> float:
        """Score deviation from typical access times"""
        if user_id not in self.baselines:
            return 0.0
        
        baseline = self.baselines[user_id]
        if not baseline.login_times:
            return 0.0
        
        try:
            log_time = datetime.fromisoformat(log.timestamp.replace('Z', '+00:00'))
            current_hour = log_time.hour
        except (ValueError, AttributeError):
            return 0.0
        
        if current_hour in baseline.active_hours:
            return 0.0
        
        return 0.3
    
    def _score_ip_anomaly(self, user_id: str, log: AuditLog) -> float:
        """Score deviation from known IP addresses"""
        if user_id not in self.baselines or not log.ip_address:
            return 0.0
        
        baseline = self.baselines[user_id]
        if not baseline.common_ips:
            return 0.0
        
        if log.ip_address in baseline.common_ips:
            return 0.0
        
        return 0.4
    
    def _score_resource_anomaly(self, user_id: str, log: AuditLog) -> float:
        """Score access to atypical resources"""
        if user_id not in self.baselines:
            return 0.0
        
        baseline = self.baselines[user_id]
        if not baseline.common_resources:
            return 0.0
        
        resource_count = baseline.common_resources.get(log.resource, 0)
        total_accesses = sum(baseline.common_resources.values())
        
        if resource_count == 0:
            return 0.35
        
        access_rate = resource_count / total_accesses if total_accesses > 0 else 0
        if access_rate < 0.05:
            return 0.25
        
        return 0.0
    
    def _score_action_anomaly(self, user_id: str, log: AuditLog) -> float:
        """Score unusual action patterns"""
        if user_id not in self.baselines:
            return 0.0
        
        baseline = self.baselines[user_id]
        if not baseline.common_actions:
            return 0.0
        
        action_count = baseline.common_actions.get(log.action, 0)
        
        if action_count == 0:
            return 0.2
        
        return 0.0
    
    def _score_user_agent_anomaly(self, user_id: str, log: Audit