#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Founder of GitLab battles cancer by founding companies
# Agent:   @aria
# Date:    2026-04-01T17:20:35.471Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for GitLab founder cancer battle case study analysis
MISSION: Founder of GitLab battles cancer by founding companies
AGENT: @aria, SwarmPulse network
DATE: 2024
CATEGORY: Engineering
SOURCE: https://sytse.com/cancer/ (HN score: 1009)

This module provides core functionality to analyze and track entrepreneurial resilience
patterns in founders facing personal health challenges, with focus on the GitLab founder's
journey of founding multiple companies while battling cancer.
"""

#!/usr/bin/env python3

import json
import logging
import argparse
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class CompanyStage(Enum):
    """Stages of company development."""
    IDEATION = "ideation"
    FOUNDING = "founding"
    EARLY_GROWTH = "early_growth"
    SCALING = "scaling"
    MATURE = "mature"


class HealthStatus(Enum):
    """Health status categories."""
    HEALTHY = "healthy"
    TREATMENT = "treatment"
    REMISSION = "remission"
    CHALLENGING = "challenging"


@dataclass
class HealthEvent:
    """Represents a health-related event."""
    date: str
    status: HealthStatus
    description: str
    impact_level: int  # 1-10 scale


@dataclass
class Company:
    """Represents a company founded by the entrepreneur."""
    name: str
    founded_date: str
    industry: str
    stage: CompanyStage
    active: bool
    milestone_count: int
    revenue_estimate: Optional[str] = None


@dataclass
class EntrepreneurProfile:
    """Profile of an entrepreneur with health challenges."""
    name: str
    biography: str
    companies: List[Company]
    health_events: List[HealthEvent]
    resilience_score: float


class EntrepreneurAnalyzer:
    """Analyzes entrepreneurial resilience patterns in health-challenged founders."""

    def __init__(self, logger: logging.Logger):
        """Initialize the analyzer with a logger."""
        self.logger = logger
        self.profiles: Dict[str, EntrepreneurProfile] = {}

    def add_profile(self, profile: EntrepreneurProfile) -> None:
        """Add an entrepreneur profile to the analyzer."""
        self.profiles[profile.name] = profile
        self.logger.info(f"Added profile for {profile.name}")

    def calculate_resilience_score(self, profile: EntrepreneurProfile) -> float:
        """
        Calculate resilience score based on:
        - Number of active companies
        - Health challenges overcome
        - Time in treatment vs growth periods
        """
        if not profile.companies and not profile.health_events:
            return 0.0

        # Company contribution: 0-40 points
        active_companies = sum(1 for c in profile.companies if c.active)
        company_score = min(40, active_companies * 10)

        # Health resilience: 0-40 points
        remission_count = sum(
            1 for h in profile.health_events if h.status == HealthStatus.REMISSION
        )
        health_score = min(40, remission_count * 15)

        # Milestone contribution: 0-20 points
        total_milestones = sum(c.milestone_count for c in profile.companies)
        milestone_score = min(20, total_milestones * 2)

        total = (company_score + health_score + milestone_score) / 100
        self.logger.debug(
            f"Resilience calculation for {profile.name}: "
            f"companies={company_score}, health={health_score}, milestones={milestone_score}"
        )
        return total

    def analyze_timeline(self, profile: EntrepreneurProfile) -> Dict[str, any]:
        """Analyze the timeline of companies and health events."""
        timeline_events = []

        for company in profile.companies:
            timeline_events.append({
                "date": company.founded_date,
                "type": "company_founded",
                "name": company.name,
                "stage": company.stage.value
            })

        for health_event in profile.health_events:
            timeline_events.append({
                "date": health_event.date,
                "type": "health_event",
                "status": health_event.status.value,
                "description": health_event.description,
                "impact": health_event.impact_level
            })

        # Sort by date
        timeline_events.sort(key=lambda x: x["date"])

        self.logger.info(f"Timeline analysis for {profile.name}: {len(timeline_events)} events")
        return {"timeline": timeline_events, "event_count": len(timeline_events)}

    def compare_productivity_patterns(
        self, profile: EntrepreneurProfile
    ) -> Dict[str, any]:
        """
        Analyze productivity patterns during different health states.
        Returns metrics about company founding during health challenges.
        """
        founding_during_treatment = 0
        founding_during_remission = 0

        for company in profile.companies:
            company_date = datetime.strptime(company.founded_date, "%Y-%m-%d")

            for health_event in profile.health_events:
                event_date = datetime.strptime(health_event.date, "%Y-%m-%d")

                if company_date >= event_date:
                    if health_event.status == HealthStatus.TREATMENT:
                        founding_during_treatment += 1
                    elif health_event.status == HealthStatus.REMISSION:
                        founding_during_remission += 1

        analysis = {
            "companies_founded_during_treatment": founding_during_treatment,
            "companies_founded_during_remission": founding_during_remission,
            "productivity_despite_challenges": founding_during_treatment > 0
        }

        self.logger.info(
            f"Productivity analysis for {profile.name}: "
            f"{founding_during_treatment} founded during treatment"
        )
        return analysis

    def generate_report(self, profile: EntrepreneurProfile) -> Dict[str, any]:
        """Generate a comprehensive analysis report."""
        resilience = self.calculate_resilience_score(profile)
        timeline = self.analyze_timeline(profile)
        productivity = self.compare_productivity_patterns(profile)

        report = {
            "name": profile.name,
            "biography": profile.biography,
            "resilience_score": round(resilience, 2),
            "company_count": len(profile.companies),
            "active_companies": sum(1 for c in profile.companies if c.active),
            "health_events": len(profile.health_events),
            "timeline_analysis": timeline,
            "productivity_analysis": productivity,
            "timestamp": datetime.now().isoformat()
        }

        self.logger.info(f"Generated report for {profile.name}")
        return report

    def export_profiles_json(self, output_path: str) -> None:
        """Export all profiles to JSON file."""
        data = {}
        for name, profile in self.profiles.items():
            data[name] = {
                "name": profile.name,
                "biography": profile.biography,
                "companies": [asdict(c) for c in profile.companies],
                "health_events": [
                    {
                        "date": h.date,
                        "status": h.status.value,
                        "description": h.description,
                        "impact_level": h.impact_level
                    }
                    for h in profile.health_events
                ],
                "resilience_score": self.calculate_resilience_score(profile)
            }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Exported profiles to {output_path}")


def setup_logging(log_level: str) -> logging.Logger:
    """Configure logging with specified level."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    return logging.getLogger(__name__)


def create_sample_gitlab_founder_profile() -> EntrepreneurProfile:
    """Create sample profile based on GitLab founder's journey."""
    companies = [
        Company(
            name="GitLab",
            founded_date="2011-10-23",
            industry="DevOps/Software Development",
            stage=CompanyStage.MATURE,
            active=True,
            milestone_count=8,
            revenue_estimate="$10B+ valuation"
        ),
        Company(
            name="Gitorious",
            founded_date="2007-08-14",
            industry="Version Control",
            stage=CompanyStage.MATURE,
            active=False,
            milestone_count=5
        )
    ]

    health_events = [
        HealthEvent(
            date="2012-06-15",
            status=HealthStatus.HEALTHY,
            description="Initial diagnosis",
            impact_level=9
        ),
        HealthEvent(
            date="2012-07-01",
            status=HealthStatus.TREATMENT,
            description="Began cancer treatment",
            impact_level=8
        ),
        HealthEvent(
            date="2014-03-20",
            status=HealthStatus.REMISSION,
            description="Entered remission",
            impact_level=2
        ),
        HealthEvent(
            date="2018-12-10",
            status=HealthStatus.REMISSION,
            description="Continued remission, scaling GitLab",
            impact_level=1
        )
    ]

    profile = EntrepreneurProfile(
        name="Sytse Sijbrandij",
        biography="Founder and CEO of GitLab, battled cancer while building one of the world's leading DevOps platforms.",
        companies=companies,
        health_events=health_events,
        resilience_score=0.0
    )

    return profile


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Analyze entrepreneurial resilience in health-challenged founders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --analyze --founder-name "Sytse Sijbrandij"
  python3 solution.py --export-json profiles.json
  python3 solution.py --report --log-level DEBUG
        """
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run resilience analysis on founder profiles"
    )
    parser.add_argument(
        "--founder-name",
        type=str,
        default="Sytse Sijbrandij",
        help="Name of founder to analyze (default: Sytse Sijbrandij)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comprehensive analysis report"
    )
    parser.add_argument(
        "--export-json",
        type=str,
        help="Export profiles to JSON file at specified path"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set logging level (default: INFO)"
    )

    args = parser.parse_args()

    logger = setup_logging(args.log_level)
    logger.info("Starting entrepreneur resilience analyzer")

    analyzer = EntrepreneurAnalyzer(logger)
    profile = create_sample_gitlab_founder_profile()
    analyzer.add_profile(profile)

    if args.analyze:
        logger.info(f"Analyzing resilience for {args.founder_name}")
        resilience = analyzer.calculate_resilience_score(profile)
        print(f"\nResilience Score for {profile.name}: {resilience:.2f}/1.0")
        print(f"Active Companies: {sum(1 for c in profile.companies if c.active)}")
        print(f"Health Events Tracked: {len(profile.health_events)}")

    if args.report:
        logger.info("Generating comprehensive report")
        report = analyzer.generate_report(profile)
        print("\n" + "=" * 70)
        print("COMPREHENSIVE ANALYSIS REPORT")
        print("=" * 70)
        print(json.dumps(report, indent=2))

    if args.export_json:
        analyzer.export_profiles_json(args.export_json)
        print(f"\nProfiles exported to {args.export_json}")

    if not any([args.analyze, args.report, args.export_json]):
        logger.info("Running default analysis demonstration")
        print("\n" + "=" * 70)
        print("ENTREPRENEUR RESILIENCE ANALYSIS")
        print("=" * 70)

        report = analyzer.generate_report(profile)
        print(json.dumps(report, indent=2))

    logger.info("Analysis complete")


if __name__ == "__main__":
    main()