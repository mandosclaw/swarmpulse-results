#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Desk for people who work at home with a cat
# Agent:   @aria
# Date:    2026-03-31T19:16:45.682Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Desk for people who work at home with a cat
Mission: Engineering
Agent: @aria (SwarmPulse)
Date: 2026-03-27

This module implements a pet-aware desk management system that monitors
workspace conditions and provides recommendations for maintaining productivity
while working from home with a cat.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any
import time
import random


@dataclass
class DeskCondition:
    """Represents the current state of a pet-aware workspace."""
    timestamp: str
    temperature_celsius: float
    humidity_percent: float
    noise_level_db: float
    cat_proximity_cm: float
    keyboard_activity_count: int
    monitor_distance_cm: float
    chair_ergonomic_score: int


@dataclass
class SafetyAlert:
    """Represents a safety or productivity concern."""
    severity: str
    category: str
    message: str
    recommendation: str
    timestamp: str


class PetAwareDeskManager:
    """
    Manages a workspace optimized for people working from home with cats.
    Monitors environmental conditions and provides real-time recommendations.
    """

    def __init__(
        self,
        temp_min: float = 18.0,
        temp_max: float = 24.0,
        humidity_min: float = 30.0,
        humidity_max: float = 60.0,
        noise_threshold: float = 70.0,
        cat_proximity_min: float = 30.0,
        monitor_distance_optimal: float = 60.0,
    ):
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.humidity_min = humidity_min
        self.humidity_max = humidity_max
        self.noise_threshold = noise_threshold
        self.cat_proximity_min = cat_proximity_min
        self.monitor_distance_optimal = monitor_distance_optimal
        self.alerts: List[SafetyAlert] = []
        self.conditions_history: List[DeskCondition] = []

    def generate_sample_condition(self) -> DeskCondition:
        """Generate realistic sensor data for testing."""
        return DeskCondition(
            timestamp=datetime.now().isoformat(),
            temperature_celsius=round(random.uniform(16, 26), 1),
            humidity_percent=round(random.uniform(25, 75), 1),
            noise_level_db=round(random.uniform(35, 80), 1),
            cat_proximity_cm=round(random.uniform(10, 200), 1),
            keyboard_activity_count=random.randint(0, 50),
            monitor_distance_cm=round(random.uniform(40, 100), 1),
            chair_ergonomic_score=random.randint(1, 10),
        )

    def validate_condition(self, condition: DeskCondition) -> List[SafetyAlert]:
        """Analyze desk conditions and generate alerts."""
        alerts = []

        # Temperature check
        if condition.temperature_celsius < self.temp_min:
            alerts.append(
                SafetyAlert(
                    severity="warning",
                    category="temperature",
                    message=f"Temperature too low: {condition.temperature_celsius}°C",
                    recommendation="Increase room temperature or add a heater for comfort",
                    timestamp=condition.timestamp,
                )
            )
        elif condition.temperature_celsius > self.temp_max:
            alerts.append(
                SafetyAlert(
                    severity="warning",
                    category="temperature",
                    message=f"Temperature too high: {condition.temperature_celsius}°C",
                    recommendation="Open windows or use air conditioning. Ensure cat has access to water.",
                    timestamp=condition.timestamp,
                )
            )

        # Humidity check
        if condition.humidity_percent < self.humidity_min:
            alerts.append(
                SafetyAlert(
                    severity="info",
                    category="humidity",
                    message=f"Humidity too low: {condition.humidity_percent}%",
                    recommendation="Use a humidifier to prevent dry skin and respiratory issues for you and your cat",
                    timestamp=condition.timestamp,
                )
            )
        elif condition.humidity_percent > self.humidity_max:
            alerts.append(
                SafetyAlert(
                    severity="warning",
                    category="humidity",
                    message=f"Humidity too high: {condition.humidity_percent}%",
                    recommendation="Increase ventilation to prevent mold and maintain air quality",
                    timestamp=condition.timestamp,
                )
            )

        # Noise level check
        if condition.noise_level_db > self.noise_threshold:
            alerts.append(
                SafetyAlert(
                    severity="warning",
                    category="noise",
                    message=f"Noise level excessive: {condition.noise_level_db}dB",
                    recommendation="Use noise-canceling headphones and provide a quiet retreat for your cat",
                    timestamp=condition.timestamp,
                )
            )

        # Cat proximity check
        if condition.cat_proximity_cm < self.cat_proximity_min:
            alerts.append(
                SafetyAlert(
                    severity="info",
                    category="pet_interaction",
                    message=f"Cat very close: {condition.cat_proximity_cm}cm away",
                    recommendation="Your cat is seeking attention. Consider a short break or provide a nearby perch.",
                    timestamp=condition.timestamp,
                )
            )

        # Monitor distance check
        if abs(condition.monitor_distance_cm - self.monitor_distance_optimal) > 20:
            alerts.append(
                SafetyAlert(
                    severity="info",
                    category="ergonomics",
                    message=f"Monitor distance suboptimal: {condition.monitor_distance_cm}cm",
                    recommendation="Adjust monitor distance to approximately 60cm for optimal eye health",
                    timestamp=condition.timestamp,
                )
            )

        # Chair ergonomic score check
        if condition.chair_ergonomic_score < 5:
            alerts.append(
                SafetyAlert(
                    severity="warning",
                    category="ergonomics",
                    message=f"Poor chair ergonomics: score {condition.chair_ergonomic_score}/10",
                    recommendation="Invest in an ergonomic chair designed for extended work with pets nearby",
                    timestamp=condition.timestamp,
                )
            )

        # Keyboard activity check (inactivity warning)
        if condition.keyboard_activity_count == 0:
            alerts.append(
                SafetyAlert(
                    severity="info",
                    category="productivity",
                    message="No keyboard activity detected",
                    recommendation="Take a break, stretch, and engage with your cat to maintain work-life balance",
                    timestamp=condition.timestamp,
                )
            )

        return alerts

    def process_condition(self, condition: DeskCondition) -> Dict[str, Any]:
        """Process a desk condition and return analysis results."""
        self.conditions_history.append(condition)
        new_alerts = self.validate_condition(condition)
        self.alerts.extend(new_alerts)

        return {
            "condition": asdict(condition),
            "alerts": [asdict(alert) for alert in new_alerts],
            "alert_count": len(new_alerts),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from condition history."""
        if not self.conditions_history:
            return {"error": "No data available"}

        temps = [c.temperature_celsius for c in self.conditions_history]
        humidities = [c.humidity_percent for c in self.conditions_history]
        noise_levels = [c.noise_level_db for c in self.conditions_history]
        distances = [c.cat_proximity_cm for c in self.conditions_history]

        return {
            "samples_recorded": len(self.conditions_history),
            "temperature": {
                "min": round(min(temps), 1),
                "max": round(max(temps), 1),
                "avg": round(sum(temps) / len(temps), 1),
            },
            "humidity": {
                "min": round(min(humidities), 1),
                "max": round(max(humidities), 1),
                "avg": round(sum(humidities) / len(humidities), 1),
            },
            "noise_level": {
                "min": round(min(noise_levels), 1),
                "max": round(max(noise_levels), 1),
                "avg": round(sum(noise_levels) / len(noise_levels), 1),
            },
            "cat_proximity": {
                "min": round(min(distances), 1),
                "max": round(max(distances), 1),
                "avg": round(sum(distances) / len(distances), 1),
            },
            "total_alerts": len(self.alerts),
            "alert_breakdown": self._count_alerts_by_category(),
        }

    def _count_alerts_by_category(self) -> Dict[str, int]:
        """Count alerts by category."""
        counts: Dict[str, int] = {}
        for alert in self.alerts:
            counts[alert.category] = counts.get(alert.category, 0) + 1
        return counts

    def get_recommendations(self) -> List[str]:
        """Generate overall recommendations based on collected data."""
        recommendations = []

        if not self.conditions_history:
            return ["No data available for recommendations"]

        stats = self.get_statistics()

        if stats["temperature"]["avg"] < self.temp_min:
            recommendations.append("Consider improving insulation or using supplemental heating")

        if stats["humidity"]["avg"] > self.humidity_max:
            recommendations.append("Improve ventilation to reduce humidity levels")

        if stats["noise_level"]["avg"] > self.noise_threshold:
            recommendations.append("Install acoustic panels or use active noise cancellation")

        if stats["cat_proximity"]["avg"] < 50:
            recommendations.append("Consider a cat tree or elevated perch near your desk area")

        if not recommendations:
            recommendations.append("Your workspace is well-optimized for working with your cat!")

        return recommendations

    def monitor_continuous(self, duration_seconds: int, interval_seconds: int) -> List[Dict[str, Any]]:
        """Monitor desk conditions continuously for a specified duration."""
        results = []
        end_time = time.time() + duration_seconds
        sample_count = 0

        while time.time() < end_time:
            condition = self.generate_sample_condition()
            result = self.process_condition(condition)
            result["sample_number"] = sample_count + 1
            results.append(result)
            sample_count += 1
            time.sleep(interval_seconds)

        return results


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Pet-aware desk management system for remote workers with cats"
    )

    parser.add_argument(
        "--mode",
        choices=["single", "continuous", "stats", "recommendations"],
        default="single",
        help="Operating mode",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=10,
        help="Duration in seconds for continuous monitoring",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Sampling interval in seconds for continuous monitoring",
    )

    parser.add_argument(
        "--temp-min",
        type=float,
        default=18.0,
        help="Minimum comfortable temperature in Celsius",
    )

    parser.add_argument(
        "--temp-max",
        type=float,
        default=24.0,
        help="Maximum comfortable temperature in Celsius",
    )

    parser.add_argument(
        "--humidity-min",
        type=float,
        default=30.0,
        help="Minimum comfortable humidity percentage",
    )

    parser.add_argument(
        "--humidity-max",
        type=float,
        default=60.0,
        help="Maximum comfortable humidity percentage",
    )

    parser.add_argument(
        "--noise-threshold",
        type=float,
        default=70.0,
        help="Maximum acceptable noise level in dB",
    )

    parser.add_argument(
        "--cat-proximity-min",
        type=float,
        default=30.0,
        help="Minimum safe distance to cat in cm",
    )

    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    manager = PetAwareDeskManager(
        temp_min=args.temp_min,
        temp_max=args.temp_max,
        humidity_min=args.humidity_min,
        humidity_max=args.humidity_max,
        noise_threshold=args.noise_threshold,
        cat_proximity_min=args.cat_proximity_min,
    )

    if args.mode == "single":
        condition = manager.generate_sample_condition()
        result = manager.process_condition(condition)

        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print("\n=== DESK CONDITION ANALYSIS ===")
            print(f"Timestamp: {condition.timestamp}")
            print(f"Temperature: {condition.temperature_celsius}°C")
            print(f"Humidity: {condition.humidity_percent}%")
            print(f"Noise Level: {condition.noise_level_db}dB")
            print(f"Cat Proximity: {condition.cat_proximity_cm}cm")
            print(f"Monitor Distance: {condition.monitor_distance_cm}cm")
            print(f"Chair Ergonomics: {condition.chair_ergonomic_score}/10")
            print(f"\nAlerts Generated: {result['alert_count']}")
            if result["alerts"]:
                for alert in result["alerts"]:
                    print(f"  [{alert['severity'].upper()}] {alert['category']}: {alert['message']}")
                    print(f"    → {alert['recommendation']}")

    elif args.mode == "continuous":
        print(f"Starting continuous monitoring for {args.duration}s (interval: {args.interval}s)...")
        results = manager.monitor_continuous(args.duration, args.interval)

        if args.output_json:
            print(json.dumps(results, indent=2))
        else:
            print(f"\nCollected {len(results)} samples")
            total_alerts = sum(r["alert_count"] for r in results)
            print(f"Total alerts: {total_alerts}")

    elif args.mode == "stats":
        # Generate some sample data
        for _ in range(5):
            condition = manager.generate_sample_condition()
            manager.process_condition(condition)

        stats = manager.get_statistics()

        if args.output_json:
            print(json.dumps(stats, indent=2))
        else:
            print("\n=== WORKSPACE STATISTICS ===")
            print(f"Samples Recorded: {stats['samples_recorded']}")
            print(f"\nTemperature (°C): min={stats['temperature']['min']}, "
                  f"avg={stats['temperature']['avg']}, max={stats['temperature']['max']}")
            print(f"Humidity (%): min={stats['humidity']['min']}, "
                  f"avg={stats['humidity']['avg']}, max={stats['humidity']['max']}")
            print(f"Noise Level (dB): min={stats['noise_level']['min']}, "
                  f"avg={stats['noise_level']['avg']}, max={stats['noise_level']['max']}")
            print(f"Cat Proximity (cm): min={stats['cat_proximity']['min']}, "
                  f"avg={stats['cat_proximity']['avg']}, max={stats['cat_proximity']['max']}")
            print(f"Total Alerts: {stats['total_alerts']}")
            print(f"Alert Breakdown: {stats['alert_breakdown']}")

    elif args.mode == "recommendations":
        # Generate sample data
        for _ in range(5):
            condition = manager.generate_sample_condition()
            manager.process_condition(condition)

        recommendations = manager.get_recommendations()

        if args.output_json:
            print(json.dumps({"recommendations": recommendations}, indent=2))
        else:
            print("\n=== WORKSPACE RECOMMENDATIONS ===")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")


if __name__ == "__main__":
    main()