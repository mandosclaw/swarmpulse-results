#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement core functionality
# Mission: Sand from Different Beaches in the World
# Agent:   @aria
# Date:    2026-03-29T20:38:00.599Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Implement core functionality for Sand from Different Beaches in the World
MISSION: Engineering
AGENT: @aria
DATE: 2024
CONTEXT: Sourced from https://magnifiedsand.com/ (Hacker News score: 68)

This module implements sand analysis and classification from different beaches worldwide.
It processes sand samples, extracts characteristics, and provides detailed analysis reports.
"""

import argparse
import json
import sys
import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class SandColor(Enum):
    """Classification of sand colors observed under magnification."""
    WHITE = "white"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    BLACK = "black"
    GRAY = "gray"
    BROWN = "brown"
    MIXED = "mixed"


class SandOrigin(Enum):
    """Classification of sand origins by geological composition."""
    QUARTZ = "quartz"
    VOLCANIC = "volcanic"
    CORAL = "coral"
    SHELL = "shell"
    MINERAL = "mineral"
    MIXED = "mixed"


class BeachRegion(Enum):
    """Geographic regions for beach classification."""
    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARCTIC = "arctic"
    DESERT = "desert"
    VOLCANIC = "volcanic"


@dataclass
class SandGrain:
    """Represents a single sand grain sample."""
    diameter_mm: float
    color: SandColor
    shape: str
    translucency: str
    composition: str

    def to_dict(self) -> Dict:
        return {
            "diameter_mm": self.diameter_mm,
            "color": self.color.value,
            "shape": self.shape,
            "translucency": self.translucency,
            "composition": self.composition
        }


@dataclass
class BeachSandSample:
    """Represents a complete sand sample from a beach."""
    beach_name: str
    location: str
    coordinates: Tuple[float, float]
    region: BeachRegion
    collection_date: str
    grains: List[SandGrain]
    average_grain_size_mm: float
    dominant_color: SandColor
    origin: SandOrigin
    salinity_ppm: float
    moisture_percent: float
    notes: str

    def to_dict(self) -> Dict:
        return {
            "beach_name": self.beach_name,
            "location": self.location,
            "coordinates": {
                "latitude": self.coordinates[0],
                "longitude": self.coordinates[1]
            },
            "region": self.region.value,
            "collection_date": self.collection_date,
            "grain_count": len(self.grains),
            "average_grain_size_mm": self.average_grain_size_mm,
            "dominant_color": self.dominant_color.value,
            "origin": self.origin.value,
            "salinity_ppm": self.salinity_ppm,
            "moisture_percent": self.moisture_percent,
            "notes": self.notes,
            "grains": [grain.to_dict() for grain in self.grains]
        }


class SandAnalyzer:
    """Core analyzer for sand samples from different beaches."""

    def __init__(self):
        self.samples: List[BeachSandSample] = []
        self.analysis_results: Dict = {}

    def add_sample(self, sample: BeachSandSample) -> bool:
        """Add a sand sample to the analyzer."""
        if not isinstance(sample, BeachSandSample):
            return False
        self.samples.append(sample)
        return True

    def classify_grain_size(self, diameter_mm: float) -> str:
        """Classify sand grain by size (Wentworth scale)."""
        if diameter_mm >= 2.0:
            return "gravel"
        elif diameter_mm >= 1.0:
            return "very_coarse_sand"
        elif diameter_mm >= 0.5:
            return "coarse_sand"
        elif diameter_mm >= 0.25:
            return "medium_sand"
        elif diameter_mm >= 0.125:
            return "fine_sand"
        elif diameter_mm >= 0.0625:
            return "very_fine_sand"
        else:
            return "silt"

    def analyze_sample(self, sample: BeachSandSample) -> Dict:
        """Perform comprehensive analysis on a sand sample."""
        analysis = {
            "beach_name": sample.beach_name,
            "location": sample.location,
            "analysis_timestamp": datetime.now().isoformat(),
            "sample_statistics": {
                "total_grains": len(sample.grains),
                "average_grain_size_mm": sample.average_grain_size_mm,
                "grain_size_classification": self.classify_grain_size(sample.average_grain_size_mm),
                "grain_sizes": [self.classify_grain_size(g.diameter_mm) for g in sample.grains]
            },
            "color_analysis": {
                "dominant_color": sample.dominant_color.value,
                "color_distribution": self._calculate_color_distribution(sample),
                "color_uniformity": self._calculate_color_uniformity(sample)
            },
            "composition_analysis": {
                "primary_origin": sample.origin.value,
                "composition_description": sample.notes,
                "estimated_mineral_content": self._estimate_mineral_content(sample)
            },
            "environmental_properties": {
                "salinity_ppm": sample.salinity_ppm,
                "moisture_percent": sample.moisture_percent,
                "environmental_notes": self._generate_environmental_notes(sample)
            },
            "geographic_context": {
                "region": sample.region.value,
                "coordinates": {
                    "latitude": sample.coordinates[0],
                    "longitude": sample.coordinates[1]
                },
                "regional_characteristics": self._get_regional_characteristics(sample.region)
            }
        }
        return analysis

    def _calculate_color_distribution(self, sample: BeachSandSample) -> Dict[str, float]:
        """Calculate the distribution of colors in the sample."""
        color_counts = {}
        for grain in sample.grains:
            color_key = grain.color.value
            color_counts[color_key] = color_counts.get(color_key, 0) + 1

        total = len(sample.grains)
        return {color: count / total * 100 for color, count in color_counts.items()} if total > 0 else {}

    def _calculate_color_uniformity(self, sample: BeachSandSample) -> float:
        """Calculate uniformity score (0-100) based on color variance."""
        if len(sample.grains) < 2:
            return 100.0

        distribution = self._calculate_color_distribution(sample)
        if not distribution:
            return 0.0

        dominant_percentage = max(distribution.values())
        uniformity = min(100.0, dominant_percentage)
        return round(uniformity, 2)

    def _estimate_mineral_content(self, sample: BeachSandSample) -> Dict[str, str]:
        """Estimate mineral composition based on origin."""
        mineral_map = {
            SandOrigin.QUARTZ: {"primary": "silicon dioxide (SiO2)", "secondary": "feldspar"},
            SandOrigin.VOLCANIC: {"primary": "basalt, magnetite", "secondary": "olivine"},
            SandOrigin.CORAL: {"primary": "calcium carbonate (CaCO3)", "secondary": "aragonite"},
            SandOrigin.SHELL: {"primary": "calcium carbonate", "secondary": "aragonite, calcite"},
            SandOrigin.MINERAL: {"primary": "various minerals", "secondary": "depends on source"},
            SandOrigin.MIXED: {"primary": "mixed composition", "secondary": "multiple minerals"}
        }
        return mineral_map.get(sample.origin, {"primary": "unknown", "secondary": "unknown"})

    def _generate_environmental_notes(self, sample: BeachSandSample) -> str:
        """Generate environmental assessment notes."""
        notes = []
        if sample.salinity_ppm > 3000:
            notes.append("High salinity content - coastal/marine influence")
        elif sample.salinity_ppm < 500:
            notes.append("Low salinity - freshwater or desert influence")
        else:
            notes.append("Moderate salinity - typical coastal conditions")

        if sample.moisture_percent > 20:
            notes.append("High moisture retention")
        elif sample.moisture_percent < 5:
            notes.append("Very dry sample")

        return "; ".join(notes)

    def _get_regional_characteristics(self, region: BeachRegion) -> str:
        """Provide regional characteristics."""
        characteristics = {
            BeachRegion.TROPICAL: "Coral reefs, shell fragments, warm water deposits",
            BeachRegion.TEMPERATE: "Mixed minerals, quartz dominant, seasonal variation",
            BeachRegion.ARCTIC: "Ice-transported minerals, sparse composition",
            BeachRegion.DESERT: "Quartz dominant, well-sorted, minimal shell content",
            BeachRegion.VOLCANIC: "Black sand, magnetite, basalt fragments"
        }
        return characteristics.get(region, "Unknown region")

    def compare_samples(self, sample1_idx: int, sample2_idx: int) -> Dict:
        """Compare two sand samples."""
        if sample1_idx >= len(self.samples) or sample2_idx >= len(self.samples):
            return {"error": "Invalid sample index"}

        s1 = self.samples[sample1_idx]
        s2 = self.samples[sample2_idx]

        comparison = {
            "sample1": s1.beach_name,
            "sample2": s2.beach_name,
            "grain_size_difference_mm": abs(s1.average_grain_size_mm - s2.average_grain_size_mm),
            "salinity_difference_ppm": abs(s1.salinity_ppm - s2.salinity_ppm),
            "moisture_difference_percent": abs(s1.moisture_percent - s2.moisture_percent),
            "color_match": s1.dominant_color == s2.dominant_color,
            "origin_match": s1.origin == s2.origin,
            "region_match": s1.region == s2.region,
            "similarity_score": self._calculate_similarity_score(s1, s2)
        }
        return comparison

    def _calculate_similarity_score(self, s1: BeachSandSample, s2: BeachSandSample) -> float:
        """Calculate similarity score between two samples (0-100)."""
        score = 0.0
        max_score = 0.0

        # Color match
        if s1.dominant_color == s2.dominant_color:
            score += 20
        max_score += 20

        # Origin match
        if s1.origin == s2.origin:
            score += 20
        max_score += 20

        # Region match
        if s1.region == s2.region:
            score += 15
        max_score += 15

        # Grain size similarity
        size_diff = abs(s1.average_grain_size_mm - s2.average_grain_size_mm)
        if size_diff < 0.1:
            score += 20
        elif size_diff < 0.3:
            score += 10
        max_score += 20

        # Salinity similarity
        salinity_diff = abs(s1.salinity_ppm - s2.salinity_ppm)
        if salinity_diff < 500:
            score += 15
        elif salinity_diff < 1000:
            score += 7
        max_score += 15

        # Moisture similarity
        moisture_diff = abs(s1.moisture_percent - s2.moisture_percent)
        if moisture_diff < 5:
            score += 10
        elif moisture_diff < 10:
            score += 5
        max_score += 10

        return round((score / max_score * 100) if max_score > 0 else 0, 2)

    def generate_report(self) -> Dict:
        """Generate comprehensive report for all samples."""
        if not self.samples:
            return {"error": "No samples to analyze"}

        report = {
            "report_generated": datetime.now().isoformat(),
            "total_samples": len(self.samples),
            "samples": [],
            "summary": self._generate_summary()
        }

        for sample in self.samples:
            analysis = self.analyze_sample(sample)
            report["samples"].append(analysis)

        return report

    def _generate_summary(self) -> Dict:
        """Generate summary statistics across all samples."""
        if not self.samples:
            return {}

        avg_grain_size = sum(s.average_grain_size_mm for s in self.samples) / len(self.samples)
        avg_salinity = sum(s.salinity_ppm for s in self.samples) / len(self.samples)
        avg_moisture = sum(s.moisture_percent for s in self.samples) / len(self.samples)

        color_counts = {}
        origin_counts = {}
        region_counts = {}

        for sample in self.samples:
            color_key = sample.dominant_color.value
            color_counts[color_key] = color_counts.get(color_key, 0) + 1

            origin_key = sample.origin.value
            origin_counts[origin_key] = origin_counts.get(origin_key, 0) + 1

            region_key = sample.region.value
            region_counts[region_key] = region_counts.get(region_key, 0) + 1

        return {
            "average_grain_size_mm": round(avg_grain_size, 3),
            "average_salinity_ppm": round(avg_salinity, 1),
            "average_moisture_percent": round(avg_moisture, 2),
            "most_common_color": max(color_counts, key=color_counts.get) if color_counts else None,
            "most_common_origin": max(origin_counts, key=origin_counts.get) if origin_counts else None,
            "most_common_region": max(region_counts, key=region_counts.get) if region_counts else None,
            "color_distribution": color_counts,
            "origin_distribution": origin_counts,
            "region_distribution": region_counts
        }

    def export_json(self, filename: str) -> bool:
        """Export analysis results to JSON file."""
        try:
            report = self.generate_report()
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}", file=sys.stderr)
            return False


def create_sample_data() -> List[BeachSandSample]:
    """Create sample beach sand data for demonstration."""
    samples = []

    # Sample 1: Hawaii (volcanic beach)
    grains1 = [
        SandGrain(0.75, SandColor.BLACK, "angular", "opaque", "basalt"),
        SandGrain(0.85, SandColor.BLACK, "angular", "opaque", "magnetite"),
        SandGrain(0.65, SandColor.GRAY, "angular", "opaque", "volcanic"),
    ]
    sample1 = BeachSandSample(
        beach_name="Punalu'u Beach",
        location="Hawaii, USA",
        coordinates=(19.3651, -155.0915),
        region=BeachRegion.VOLCANIC,
        collection_date="2024-01-15",
        grains=grains1,
        average_grain_size_mm=0.75,
        dominant_color=SandColor.BLACK,
        origin=SandOrigin.VOLCANIC,
        salinity_ppm=3500,