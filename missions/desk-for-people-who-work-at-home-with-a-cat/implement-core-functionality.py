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
            tips.append("Install elevated cat perches at 1.5m+ height to redirect climbing behavior.")
            tips.append("Use interactive toys to engage high-energy cat during work hours.")
        
        if self.cat.attention_seeking > 7:
            tips.append("Create dedicated interaction times to reduce random desk interruptions.")
            tips.append("Use puzzle feeders to extend feeding time and reduce boredom.")
        
        if self.desk.width < 150:
            tips.append("Consider desk expansion or second monitor arm to maximize workspace.")
        
        ergonomic_score = self.calculate_ergonomic_score()
        if ergonomic_score < 70:
            tips.append("Upgrade desk dimensions for better ergonomics and cat containment.")
        
        if self.cat.age_years < 2:
            tips.append("Rotate toys and enrichment items every 2-3 days for kitten engagement.")
        
        distraction_summary = self.get_distraction_summary()
        if distraction_summary["critical_count"] > 0:
            tips.append("Implement focused work blocks with scheduled cat play sessions.")
        
        if not tips:
            tips.append("Your workspace setup is well-optimized for your cat!")
        
        return tips
    
    def export_events_json(self, filepath: Path) -> None:
        """Export recorded events to JSON file."""
        events_data = [event.to_dict() for event in self.events]
        with open(filepath, 'w') as f:
            json.dump(events_data, f, indent=2)
    
    def generate_report(self) -> Dict:
        """Generate comprehensive workspace report."""
        return {
            "cat_profile": asdict(self.cat),
            "desk_dimensions": asdict(self.desk),
            "desk_area_sqm": self.desk.get_area_sqm(),
            "cat_distraction_risk": self.cat.get_distraction_risk().name,
            "ergonomic_score": round(self.calculate_ergonomic_score(), 1),
            "layout_recommendations": self.recommend_desk_layout(),
            "distraction_summary": self.get_distraction_summary(),
            "zone_usage": self.get_zone_usage_report(),
            "optimization_tips": self.get_optimization_tips(),
            "total_events_recorded": len(self.events),
            "report_generated": datetime.now().isoformat()
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cat-friendly desk workspace manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python implement-core-functionality.py --demo
  python implement-core-functionality.py --cat-name Whiskers --report
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demonstration with sample data"
    )
    
    parser.add_argument(
        "--cat-name",
        type=str,
        default="Mittens",
        help="Name of the cat (default: Mittens)"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate and print comprehensive report"
    )
    
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export events to JSON file"
    )
    
    args = parser.parse_args()
    
    # Create desk dimensions (standard home office desk)
    desk = DeskDimensions(width=140, depth=70, height=75)
    
    # Create cat profile
    cat = CatProfile(
        name=args.cat_name,
        age_years=3.5,
        weight_kg=4.2,
        activity_level="medium",
        attention_seeking=6
    )
    
    # Initialize manager
    manager = CatFriendlyDeskManager(desk, cat)
    
    if args.demo:
        # Simulate some workspace events
        manager.record_event(
            WorkspaceZone.PRIMARY_DESK,
            "work_session",
            DistractionLevel.MINIMAL,
            "Morning focus session",
            duration_minutes=120
        )
        
        manager.record_event(
            WorkspaceZone.CAT_PERCH,
            "cat_activity",
            DistractionLevel.LOW,
            "Cat resting on perch",
            duration_minutes=45
        )
        
        manager.record_event(
            WorkspaceZone.PLAY_AREA,
            "cat_play",
            DistractionLevel.MODERATE,
            "Active play with toy",
            duration_minutes=15
        )
        
        manager.record_event(
            WorkspaceZone.PRIMARY_DESK,
            "cat_interruption",
            DistractionLevel.HIGH,
            "Cat on keyboard - work interrupted",
            duration_minutes=5
        )
        
        manager.record_event(
            WorkspaceZone.PRIMARY_DESK,
            "work_session",
            DistractionLevel.MINIMAL,
            "Afternoon focus session",
            duration_minutes=90
        )
        
        print("=" * 70)
        print("CAT-FRIENDLY DESK MANAGER - DEMONSTRATION")
        print("=" * 70)
        print()
    
    if args.report or args.demo:
        report = manager.generate_report()
        print(json.dumps(report, indent=2))
        print()
    
    if args.export_json:
        manager.export_events_json(Path(args.export_json))
        print(f"Events exported to {args.export_json}")
    
    if not (args.demo or args.report or args.export_json):
        # Default: show optimization tips
        print(f"Cat-Friendly Desk Setup for {cat.name}")
        print("-" * 50)
        print(f"Ergonomic Score: {manager.calculate_ergonomic_score()}/100")
        print(f"Distraction Risk: {cat.get_distraction_risk().name}")
        print()
        print("Optimization Tips:")
        for i, tip in enumerate(manager.get_optimization_tips(), 1):
            print(f"  {i}. {tip}")


if __name__ == "__main__":
    main()