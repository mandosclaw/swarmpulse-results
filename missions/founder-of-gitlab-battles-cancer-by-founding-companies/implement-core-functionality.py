#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-03-29T09:16:19.042Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for GitLab founder cancer journey documentation
MISSION: Founder of GitLab battles cancer by founding companies
CATEGORY: Engineering
AGENT: @aria
DATE: 2024

This tool processes, analyzes, and tracks the journey of building companies
while facing health challenges. It provides structured data analysis, timeline
generation, and insights extraction from documented experiences.
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse


class CompanyPhase(Enum):
    """Phases of company development"""
    IDEATION = "ideation"
    FOUNDING = "founding"
    EARLY_STAGE = "early_stage"
    SCALING = "scaling"
    MATURE = "mature"


class HealthStatus(Enum):
    """Health status categories"""
    HEALTHY = "healthy"
    DIAGNOSED = "diagnosed"
    TREATMENT = "treatment"
    RECOVERY = "recovery"
    REMISSION = "remission"


@dataclass
class TimelineEvent:
    """Represents a single timeline event"""
    date: str
    event_type: str
    title: str
    description: str
    company: Optional[str] = None
    health_status: Optional[str] = None
    impact_level: str = "medium"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CompanyRecord:
    """Represents a company founded"""
    name: str
    founding_date: str
    industry: str
    phase: str
    description: str
    achievements: List[str]
    employees_count: Optional[int] = None
    funding_raised: Optional[str] = None


@dataclass
class JourneyAnalysis:
    """Analysis of founder journey"""
    total_companies: int
    total_timeline_events: int
    health_phases: Dict[str, int]
    company_phases: Dict[str, int]
    average_company_duration_months: float
    key_insights: List[str]
    resilience_score: float


class FounderJourneyAnalyzer:
    """Analyzes founder's journey of building companies while managing health"""

    def __init__(self, log_level: str = "INFO"):
        self.logger = self._setup_logging(log_level)
        self.companies: List[CompanyRecord] = []
        self.timeline_events: List[TimelineEvent] = []
        self.logger.info("FounderJourneyAnalyzer initialized")

    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Configure logging with proper format"""
        logger = logging.getLogger(__name__)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log_level.upper()))
        return logger

    def add_company(self, company: CompanyRecord) -> None:
        """Add a company record to the journey"""
        self.logger.info(f"Adding company: {company.name}")
        self.companies.append(company)

    def add_timeline_event(self, event: TimelineEvent) -> None:
        """Add a timeline event to the journey"""
        self.logger.debug(f"Adding timeline event: {event.title}")
        self.timeline_events.append(event)

    def calculate_company_duration(self, start_date: str, end_date: Optional[str] = None) -> int:
        """Calculate company duration in months"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
            delta = (end - start).days
            return max(1, delta // 30)
        except ValueError as e:
            self.logger.warning(f"Date parsing error: {e}")
            return 0

    def calculate_resilience_score(self) -> float:
        """
        Calculate resilience score based on:
        - Number of companies founded during health challenges
        - Transitions between health phases and company milestones
        - Continued productivity despite obstacles
        """
        if not self.timeline_events:
            return 0.0

        health_challenge_events = sum(
            1 for event in self.timeline_events
            if event.health_status in [HealthStatus.DIAGNOSED.value, HealthStatus.TREATMENT.value]
        )

        company_events_during_challenges = sum(
            1 for event in self.timeline_events
            if event.event_type == "company_milestone" and 
            event.health_status in [HealthStatus.DIAGNOSED.value, HealthStatus.TREATMENT.value]
        )

        total_events = len(self.timeline_events)
        recovery_events = sum(
            1 for event in self.timeline_events
            if event.health_status in [HealthStatus.RECOVERY.value, HealthStatus.REMISSION.value]
        )

        # Resilience = company progress despite health challenges
        base_score = (company_events_during_challenges / max(1, health_challenge_events)) * 50
        recovery_bonus = (recovery_events / max(1, total_events)) * 30
        productivity_bonus = (len(self.companies) / max(1, health_challenge_events)) * 20

        score = min(100.0, base_score + recovery_bonus + productivity_bonus)
        self.logger.info(f"Calculated resilience score: {score:.2f}")
        return score

    def generate_analysis(self) -> JourneyAnalysis:
        """Generate comprehensive analysis of the journey"""
        self.logger.info("Generating journey analysis")

        # Count health phases
        health_phases = {}
        for event in self.timeline_events:
            if event.health_status:
                health_phases[event.health_status] = health_phases.get(event.health_status, 0) + 1

        # Count company phases
        company_phases = {}
        for company in self.companies:
            company_phases[company.phase] = company_phases.get(company.phase, 0) + 1

        # Calculate average company duration
        durations = []
        for company in self.companies:
            duration = self.calculate_company_duration(company.founding_date)
            if duration > 0:
                durations.append(duration)
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Generate key insights
        insights = self._generate_insights()

        analysis = JourneyAnalysis(
            total_companies=len(self.companies),
            total_timeline_events=len(self.timeline_events),
            health_phases=health_phases,
            company_phases=company_phases,
            average_company_duration_months=avg_duration,
            key_insights=insights,
            resilience_score=self.calculate_resilience_score()
        )

        self.logger.info("Journey analysis completed successfully")
        return analysis

    def _generate_insights(self) -> List[str]:
        """Generate key insights from the journey data"""
        insights = []

        if not self.companies:
            return ["No companies recorded yet"]

        insights.append(
            f"Founded {len(self.companies)} company/companies while facing health challenges"
        )

        if self.timeline_events:
            treatment_events = sum(
                1 for e in self.timeline_events
                if e.health_status == HealthStatus.TREATMENT.value
            )
            if treatment_events > 0:
                insights.append(
                    f"Continued building through {treatment_events} significant health treatment phases"
                )

        company_phases_counts = {}
        for company in self.companies:
            company_phases_counts[company.phase] = company_phases_counts.get(company.phase, 0) + 1

        if company_phases_counts:
            most_common_phase = max(company_phases_counts, key=company_phases_counts.get)
            insights.append(f"Most companies in {most_common_phase} phase")

        total_employees = sum(c.employees_count or 0 for c in self.companies)
        if total_employees > 0:
            insights.append(f"Created {total_employees} total employment opportunities")

        insights.append("Demonstrated extraordinary resilience in face of adversity")

        return insights

    def export_json(self, filepath: Path) -> None:
        """Export journey data to JSON file"""
        try:
            analysis = self.generate_analysis()
            export_data = {
                "metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "total_companies": len(self.companies),
                    "total_events": len(self.timeline_events)
                },
                "companies": [asdict(c) for c in self.companies],
                "timeline": [e.to_dict() for e in self.timeline_events],
                "analysis": asdict(analysis)
            }

            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.logger.info(f"Journey data exported to {filepath}")
        except (IOError, OSError) as e:
            self.logger.error(f"Failed to export JSON: {e}")
            raise

    def import_json(self, filepath: Path) -> None:
        """Import journey data from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            self.companies = []
            for company_data in data.get("companies", []):
                company = CompanyRecord(**company_data)
                self.companies.append(company)

            self.timeline_events = []
            for event_data in data.get("timeline", []):
                event = TimelineEvent(**event_data)
                self.timeline_events.append(event)

            self.logger.info(f"Journey data imported from {filepath}")
        except (IOError, OSError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to import JSON: {e}")
            raise

    def print_summary(self) -> None:
        """Print human-readable summary of the journey"""
        print("\n" + "="*70)
        print("FOUNDER JOURNEY ANALYSIS SUMMARY")
        print("="*70)

        analysis = self.generate_analysis()

        print(f"\nTotal Companies Founded: {analysis.total_companies}")
        print(f"Total Timeline Events: {analysis.total_timeline_events}")
        print(f"Average Company Duration: {analysis.average_company_duration_months:.1f} months")
        print(f"Resilience Score: {analysis.resilience_score:.1f}/100")

        print("\nHealth Phase Distribution:")
        for phase, count in sorted(analysis.health_phases.items()):
            print(f"  - {phase}: {count} events")

        print("\nCompany Phase Distribution:")
        for phase, count in sorted(analysis.company_phases.items()):
            print(f"  - {phase}: {count} companies")

        print("\nKey Insights:")
        for i, insight in enumerate(analysis.key_insights, 1):
            print(f"  {i}. {insight}")

        print("\nCompanies Founded:")
        for company in self.companies:
            print(f"  - {company.name} ({company.founding_date})")
            print(f"    Phase: {company.phase} | Industry: {company.industry}")
            if company.employees_count:
                print(f"    Employees: {company.employees_count}")

        print("\n" + "="*70 + "\n")


def create_sample_journey() -> FounderJourneyAnalyzer:
    """Create sample journey data for testing"""
    analyzer = FounderJourneyAnalyzer("INFO")

    # Add companies
    companies = [
        CompanyRecord(
            name="GitLab",
            founding_date="2011-01-01",
            industry="DevOps/Software Development",
            phase=CompanyPhase.MATURE.value,
            description="Version control and CI/CD platform",
            achievements=["IPO in 2021", "10,000+ customers", "Global team"],
            employees_count=1800,
            funding_raised="$1.5B+"
        ),
        CompanyRecord(
            name="Health Tech Initiative",
            founding_date="2016-06-01",
            industry="Healthcare Technology",
            phase=CompanyPhase.SCALING.value,
            description="Cancer support technology platform",
            achievements=["Helped 50,000+ patients", "Partnerships with major hospitals"],
            employees_count=120,
            funding_raised="$50M"
        ),
        CompanyRecord(
            name="Wellness Ventures",
            founding_date="2018-03-15",
            industry="Wellness/Prevention",
            phase=CompanyPhase.EARLY_STAGE.value,
            description="Preventive health and wellness solutions",
            achievements=["Patent pending", "Research partnerships"],
            employees_count=15
        )
    ]

    for company in companies:
        analyzer.add_company(company)

    # Add timeline events
    events = [
        TimelineEvent(
            date="2011-01-01",
            event_type="company_milestone",
            title="GitLab Founded",
            description="Started GitLab project",
            company="GitLab",
            health_status=HealthStatus.HEALTHY.value,
            impact_level="high"
        ),
        TimelineEvent(
            date="2015-06-01",
            event_type="health_event",
            title="Cancer Diagnosis",
            description="Diagnosed with cancer, began treatment",
            company="GitLab",
            health_status=HealthStatus.DIAGNOSED.value,
            impact_level="high"
        ),
        TimelineEvent(
            date="2015-09-01",
            event_type="company_milestone",
            title="GitLab Continues Growth",
            description="Maintained company growth during treatment",
            company="GitLab",
            health_status=HealthStatus.TREATMENT.value,
            impact_level="high"
        ),
        TimelineEvent(
            date="2016-06-01",
            event_type="company_milestone",
            title="New Company Founded",
            description="Founded Health Tech Initiative",
            company="Health Tech Initiative",
            health_status=HealthStatus.RECOVERY.value,
            impact_level="high"
        ),
        TimelineEvent(
            date="2016-12-01",
            event_type="health_event",
            title="Cancer Remission",
            description="Achieved cancer remission",
            company="GitLab",
            health_status=HealthStatus.REMISSION.value,
            impact_level="high"
        ),
        TimelineEvent(
            date="2018-03-15",
            event_type="company_milestone",
            title="Third Company Founded",
            description="Founded Wellness Ventures",
            company="Wellness Ventures",
            health_status=HealthStatus.REMISSION.value,
            impact_level="medium"
        ),
        TimelineEvent(
            date="2021-10-15",
            event_type="company_milestone",
            title="GitLab IPO",
            description="GitLab went public",
            company="GitLab",
            health_status=HealthStatus.HEALTHY.value,
            impact_level="high"
        ),
    ]

    for event in events:
        analyzer.add_timeline_event(event)

    return analyzer


def main():
    parser = argparse.ArgumentParser(
        description="Analyze founder journey of building companies while managing health challenges",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py --help
  python script.py --action analyze
  python script.py --action export --output journey.json
  python script.py --action import --input journey.json
        """
    )

    parser.add_argument(
        "--action",
        choices=["analyze", "export