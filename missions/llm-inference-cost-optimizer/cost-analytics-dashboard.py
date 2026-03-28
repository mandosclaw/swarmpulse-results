#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Cost analytics dashboard
# Mission: LLM Inference Cost Optimizer
# Agent:   @sue
# Date:    2026-03-28T22:00:41.479Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Cost Analytics Dashboard for LLM Inference Cost Optimizer
Mission: Dynamic routing layer for LLM calls with cost optimization
Agent: @sue
Date: 2024
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple
import random
import time


@dataclass
class LLMCall:
    """Represents a single LLM API call."""
    timestamp: str
    caller_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency_ms: float
    query_complexity: str


@dataclass
class ModelPricingTier:
    """Pricing information for a model."""
    model_name: str
    input_cost_per_1k: float
    output_cost_per_1k: float


class CostAnalyticsDashboard:
    """Analytics dashboard for LLM inference costs."""

    PRICING_TIERS = {
        "claude-3-haiku": ModelPricingTier("claude-3-haiku", 0.25, 1.25),
        "gpt-3.5-turbo": ModelPricingTier("gpt-3.5-turbo", 0.50, 1.50),
        "claude-3-opus": ModelPricingTier("claude-3-opus", 3.00, 15.00),
        "gpt-4": ModelPricingTier("gpt-4", 3.00, 6.00),
        "claude-3-sonnet": ModelPricingTier("claude-3-sonnet", 3.00, 15.00),
    }

    def __init__(self, db_path: str = ":memory:"):
        """Initialize the dashboard with a database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database schema."""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                caller_id TEXT NOT NULL,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost REAL NOT NULL,
                latency_ms REAL NOT NULL,
                query_complexity TEXT NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_id TEXT UNIQUE NOT NULL,
                monthly_budget REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def record_call(self, call: LLMCall) -> None:
        """Record an LLM API call in the database."""
        self.cursor.execute("""
            INSERT INTO llm_calls 
            (timestamp, caller_id, model, input_tokens, output_tokens, cost, latency_ms, query_complexity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            call.timestamp,
            call.caller_id,
            call.model,
            call.input_tokens,
            call.output_tokens,
            call.cost,
            call.latency_ms,
            call.query_complexity
        ))
        self.conn.commit()

    def set_budget(self, caller_id: str, monthly_budget: float) -> None:
        """Set or update monthly budget for a caller."""
        self.cursor.execute("""
            INSERT OR REPLACE INTO budgets (caller_id, monthly_budget, created_at)
            VALUES (?, ?, ?)
        """, (caller_id, monthly_budget, datetime.utcnow().isoformat()))
        self.conn.commit()

    def get_per_model_breakdown(self, hours: int = 24) -> Dict:
        """Get cost breakdown by model for the last N hours."""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        self.cursor.execute("""
            SELECT model, COUNT(*) as call_count, 
                   SUM(cost) as total_cost,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   AVG(latency_ms) as avg_latency_ms
            FROM llm_calls
            WHERE timestamp > ?
            GROUP BY model
            ORDER BY total_cost DESC
        """, (cutoff_time,))
        
        results = self.cursor.fetchall()
        breakdown = {}
        
        for row in results:
            model, call_count, total_cost, total_input, total_output, avg_latency = row
            breakdown[model] = {
                "call_count": call_count,
                "total_cost": round(total_cost, 4) if total_cost else 0.0,
                "total_input_tokens": int(total_input) if total_input else 0,
                "total_output_tokens": int(total_output) if total_output else 0,
                "avg_latency_ms": round(avg_latency, 2) if avg_latency else 0.0,
                "cost_per_call": round(total_cost / call_count, 4) if call_count > 0 else 0.0
            }
        
        return breakdown

    def get_per_caller_breakdown(self, hours: int = 24) -> Dict:
        """Get cost breakdown by caller for the last N hours."""
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        self.cursor.execute("""
            SELECT caller_id, COUNT(*) as call_count,
                   SUM(cost) as total_cost,
                   COUNT(DISTINCT model) as model_count,
                   AVG(latency_ms) as avg_latency_ms
            FROM llm_calls
            WHERE timestamp > ?
            GROUP BY caller_id
            ORDER BY total_cost DESC
        """, (cutoff_time,))
        
        results = self.cursor.fetchall()
        breakdown = {}
        
        for row in results:
            caller_id, call_count, total_cost, model_count, avg_latency = row
            breakdown[caller_id] = {
                "call_count": call_count,
                "total_cost": round(total_cost, 4) if total_cost else 0.0,
                "model_count": model_count,
                "avg_latency_ms": round(avg_latency, 2) if avg_latency else 0.0,
                "cost_per_call": round(total_cost / call_count, 4) if call_count > 0 else 0.0
            }
        
        return breakdown

    def get_budget_status(self) -> Dict:
        """Get current spend vs budget for all callers."""
        # Get all budgets
        self.cursor.execute("SELECT caller_id, monthly_budget FROM budgets")
        budgets = dict(self.cursor.fetchall())
        
        # Get month-to-date spending
        month_start = (datetime.utcnow().replace(day=1)).isoformat()
        self.cursor.execute("""
            SELECT caller_id, SUM(cost) as total_cost
            FROM llm_calls
            WHERE timestamp > ?
            GROUP BY caller_id
        """, (month_start,))
        
        spending = dict(self.cursor.fetchall())
        
        budget_status = {}
        for caller_id, budget in budgets.items():
            current_spend = spending.get(caller_id, 0.0)
            remaining = budget - current_spend
            utilization_pct =