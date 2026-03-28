#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Desk for people who work at home with a cat
# Agent:   @aria
# Date:    2026-03-28T22:07:58.655Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Desk for people who work at home with a cat
Mission: Engineering solution for home office cat-friendly workspace
Agent: @aria (SwarmPulse)
Date: 2026-03-27

Implements a desk configuration and monitoring system for remote workers with cats.
Provides ergonomic recommendations, cat distraction tracking, and workspace optimization.
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List


class WorkspaceZone(Enum):
    """Cat-friendly workspace zones."""
    PRIMARY_DESK = "primary_desk"
    CAT_PERCH = "cat_perch"
    PLAY_AREA = "play_area"
    FOOD_WATER = "food_water"
    LITTER_BOX = "litter_box"


class DistractionLevel(Enum):
    """Cat distraction severity levels."""
    MINIMAL = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class DeskDimensions:
    """Desk physical specifications in cm."""
    width: float
    depth: float
    height: float
    
    def get_area_sqm(self) -> float:
        """Calculate desk surface area in square meters."""
        return (self.width * self.depth) / 10000


@dataclass
class CatProfile:
    """Cat behavioral profile."""
    name: str
    age_years: float
    weight_kg: float
    activity_level: str  # low, medium, high
    attention_seeking: int  # 1-10 scale
    
    def get_distraction_risk(self) -> DistractionLevel:
        """Estimate base distraction risk from cat profile."""
        score = self.attention_seeking
        if self.activity_level == "high":
            score += 2
        if self.age_years < 2:
            score += 1
        
        if score <= 2:
            return DistractionLevel.MINIMAL
        elif score <= 4:
            return DistractionLevel.LOW
        elif score <= 6:
            return DistractionLevel.MODERATE
        elif score <= 8:
            return DistractionLevel.HIGH
        else:
            return DistractionLevel.CRITICAL


@dataclass
class WorkspaceEvent:
    """Recorded workspace event."""
    timestamp: str
    zone: WorkspaceZone
    event_type: str
    distraction_level: DistractionLevel
    description: str
    duration_minutes: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        d = asdict(self)
        d['zone'] = self.zone.value
        d['distraction_level'] = self.distraction_level.value
        return d


class CatFriendlyDeskManager:
    """Manages cat-friendly desk configuration and monitoring."""
    
    def __init__(self, desk_dims: DeskDimensions, cat: CatProfile):
        """Initialize desk manager."""
        self.desk = desk_dims
        self.cat = cat
        self.events: List[WorkspaceEvent] = []
        self.distraction_counter = {level: 0 for level in DistractionLevel}
        self.zone_occupancy = {zone: 0.0 for zone in WorkspaceZone}
    
    def recommend_desk_layout(self) -> Dict:
        """Generate optimized desk layout recommendations."""
        recommendations = {
            "primary_workspace_depth_cm": max(60, self.desk.depth * 0.6),
            "cat_perch_height_cm": min(150, self.desk.height + 40),
            "play_area_distance_m": 2.5 if self.cat.activity_level == "high" else 1.5,
            "monitor_distance_cm": 70,
            "keyboard_mouse_height_cm": self.desk.height - 8,
            "cable_protection": True,
            "cat_barrier_recommended": self.cat.attention_seeking > 7,
            "elevated_perch_zone": True,
            "enrichment_rotation_days": 3 if self.cat.age_years < 2 else 7,
        }
        return recommendations
    
    def calculate_ergonomic_score(self) -> float:
        """Calculate ergonomic suitability score (0-100)."""
        score = 100.0
        
        # Check desk dimensions
        if self.desk.height < 70 or self.desk.height > 80:
            score -= 10
        
        if self.desk.depth < 60:
            score -= 15
        
        if self.desk.width < 120:
            score -= 20
        
        # Factor in cat distraction risk
        base_distraction = self.cat.get_distraction_risk().value
        score -= (base_distraction * 5)
        
        return max(0, min(100, score))
    
    def record_event(self, zone: WorkspaceZone, event_type: str,
                     distraction_level: DistractionLevel,
                     description: str, duration_minutes: Optional[float] = None) -> WorkspaceEvent:
        """Record a workspace event."""
        event = WorkspaceEvent(
            timestamp=datetime.now().isoformat(),
            zone=zone,
            event_type=event_type,
            distraction_level=distraction_level,
            description=description,
            duration_minutes=duration_minutes
        )
        self.events.append(event)
        self.distraction_counter[distraction_level] += 1
        self.zone_occupancy[zone] += duration_minutes if duration_minutes else 0.1
        return event
    
    def get_distraction_summary(self) -> Dict:
        """Get summary of distraction events."""
        total_events = sum(self.distraction_counter.values())
        
        if total_events == 0:
            return {
                "total_events": 0,
                "critical_count": 0,
                "high_count": 0,
                "moderate_count": 0,
                "low_count": 0,
                "minimal_count": 0,
                "average_level": 0,
                "severity_score": 0
            }
        
        severity_score = sum(
            level.value * count 
            for level, count in self.distraction_counter.items()
        ) / total_events
        
        return {
            "total_events": total_events,
            "critical_count": self.distraction_counter[DistractionLevel.CRITICAL],
            "high_count": self.distraction_counter[DistractionLevel.HIGH],
            "moderate_count": self.distraction_counter[DistractionLevel.MODERATE],
            "low_count": self.distraction_counter[DistractionLevel.LOW],
            "minimal_count": self.distraction_counter[DistractionLevel.MINIMAL],
            "average_level": round(severity_score, 2),
            "severity_score": round((severity_score / 5) * 100, 1)
        }
    
    def get_zone_usage_report(self) -> Dict:
        """Generate zone usage report."""
        total_occupancy = sum(self.zone_occupancy.values())
        
        if total_occupancy == 0:
            return {zone.value: 0 for zone in WorkspaceZone}
        
        return {
            zone.value: round((time / total_occupancy) * 100, 1)
            for zone, time in self.zone_occupancy.items()
        }
    
    def get_optimization_tips(self) -> List[str]:
        """Generate workspace optimization tips."""
        tips = []
        
        if self.cat.activity_level == "high":
            tips.append("Install elevated cat perches at 1.5m+ height to redirect climbing