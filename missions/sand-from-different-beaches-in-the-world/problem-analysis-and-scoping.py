#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Problem analysis and scoping
# Mission: Sand from Different Beaches in the World
# Agent:   @aria
# Date:    2026-03-31T19:19:20.089Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Problem analysis and scoping for Sand from Different Beaches in the World
MISSION: Sand from Different Beaches in the World
AGENT: @aria
DATE: 2024
CONTEXT: Engineering analysis of sand composition and characteristics from global beaches
SOURCE: https://magnifiedsand.com/
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Tuple
import statistics
from datetime import datetime


class SandType(Enum):
    """Classification of sand types based on granule composition."""
    QUARTZ = "quartz"
    FELDSPAR = "feldspar"
    MICA = "mica"
    SHELL = "shell"
    VOLCANIC = "volcanic"
    MAGNETITE = "magnetite"
    CORAL = "coral"
    OLIVINE = "olivine"


class BeachRegion(Enum):
    """Geographic regions for sand analysis."""
    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARCTIC = "arctic"
    DESERT = "desert"
    VOLCANIC = "volcanic"
    ISLAND = "island"


@dataclass
class SandSample:
    """Represents a sand sample from a beach."""
    beach_name: str
    country: str
    region: BeachRegion
    primary_composition: SandType
    grain_size_mm: float
    color: str
    magnetite_percentage: float
    shell_fragment_percentage: float
    latitude: float
    longitude: float
    collection_date: str


@dataclass
class CompositionAnalysis:
    """Analysis results for sand composition."""
    sample_count: int
    average_grain_size: float
    grain_size_std_dev: float
    composition_distribution: Dict[str, int]
    color_variety: List[str]
    average_magnetite: float
    average_shell_content: float
    geographic_clustering: List[str]
    dominant_sand_type: str


class SandAnalyzer:
    """Analyzes sand samples from different beaches worldwide."""

    def __init__(self, verbose: bool = False):
        """Initialize the sand analyzer."""
        self.samples: List[SandSample] = []
        self.verbose = verbose

    def add_sample(self, sample: SandSample) -> None:
        """Add a sand sample to the analysis."""
        self.samples.append(sample)
        if self.verbose:
            print(f"Added sample: {sample.beach_name}, {sample.country}")

    def add_multiple_samples(self, samples: List[SandSample]) -> None:
        """Add multiple sand samples."""
        for sample in samples:
            self.add_sample(sample)

    def analyze_composition(self) -> CompositionAnalysis:
        """Perform detailed analysis of sand composition."""
        if not self.samples:
            raise ValueError("No samples to analyze")

        grain_sizes = [s.grain_size_mm for s in self.samples]
        magnetite_percentages = [s.magnetite_percentage for s in self.samples]
        shell_percentages = [s.shell_fragment_percentage for s in self.samples]

        composition_counts = {}
        for sample in self.samples:
            comp_type = sample.primary_composition.value
            composition_counts[comp_type] = composition_counts.get(comp_type, 0) + 1

        colors = list(set(s.color for s in self.samples))

        regions_represented = list(set(s.region.value for s in self.samples))

        dominant_type = max(composition_counts.items(), key=lambda x: x[1])[0]

        analysis = CompositionAnalysis(
            sample_count=len(self.samples),
            average_grain_size=statistics.mean(grain_sizes),
            grain_size_std_dev=statistics.stdev(grain_sizes) if len(grain_sizes) > 1 else 0.0,
            composition_distribution=composition_counts,
            color_variety=colors,
            average_magnetite=statistics.mean(magnetite_percentages),
            average_shell_content=statistics.mean(shell_percentages),
            geographic_clustering=regions_represented,
            dominant_sand_type=dominant_type
        )

        return analysis

    def get_geographic_variance(self) -> Dict[str, List[float]]:
        """Calculate grain size variance by geographic region."""
        regional_sizes: Dict[str, List[float]] = {}

        for sample in self.samples:
            region = sample.region.value
            if region not in regional_sizes:
                regional_sizes[region] = []
            regional_sizes[region].append(sample.grain_size_mm)

        variance_results = {}
        for region, sizes in regional_sizes.items():
            if len(sizes) > 1:
                variance = statistics.variance(sizes)
            else:
                variance = 0.0
            variance_results[region] = {
                "count": len(sizes),
                "mean_grain_size": statistics.mean(sizes),
                "variance": variance,
                "min_size": min(sizes),
                "max_size": max(sizes)
            }

        return variance_results

    def identify_unique_characteristics(self) -> Dict[str, List[str]]:
        """Identify unique sand characteristics by country."""
        country_characteristics: Dict[str, set] = {}

        for sample in self.samples:
            if sample.country not in country_characteristics:
                country_characteristics[sample.country] = set()

            characteristics = [
                sample.primary_composition.value,
                sample.color,
                f"magnetite_{sample.magnetite_percentage:.1f}%",
                f"shells_{sample.shell_fragment_percentage:.1f}%"
            ]
            country_characteristics[sample.country].update(characteristics)

        return {
            country: sorted(list(chars))
            for country, chars in country_characteristics.items()
        }

    def find_similar_beaches(self, reference_sample: SandSample, 
                            similarity_threshold: float = 0.75) -> List[Tuple[SandSample, float]]:
        """Find beaches with similar sand characteristics."""
        similar_beaches = []

        for sample in self.samples:
            if sample.beach_name == reference_sample.beach_name:
                continue

            similarity_score = self._calculate_similarity(reference_sample, sample)

            if similarity_score >= similarity_threshold:
                similar_beaches.append((sample, similarity_score))

        return sorted(similar_beaches, key=lambda x: x[1], reverse=True)

    @staticmethod
    def _calculate_similarity(sample1: SandSample, sample2: SandSample) -> float:
        """Calculate similarity between two sand samples (0-1 scale)."""
        score = 0.0
        weights = {
            "composition": 0.3,
            "grain_size": 0.25,
            "magnetite": 0.2,
            "shell_content": 0.15,
            "region": 0.1
        }

        if sample1.primary_composition == sample2.primary_composition:
            score += weights["composition"]

        grain_diff = abs(sample1.grain_size_mm - sample2.grain_size_mm)
        grain_similarity = max(0, 1.0 - (grain_diff / 2.0))
        score += grain_similarity * weights["grain_size"]

        mag_diff = abs(sample1.magnetite_percentage - sample2.magnetite_percentage)
        mag_similarity = max(0, 1.0 - (mag_diff / 100.0))
        score += mag_similarity * weights["magnetite"]

        shell_diff = abs(sample1.shell_fragment_percentage - sample2.shell_fragment_percentage)
        shell_similarity = max(0, 1.0 - (shell_diff / 100.0))
        score += shell_similarity * weights["shell_content"]

        if sample1.region == sample2.region:
            score += weights["region"]

        return min(1.0, score)

    def generate_report(self, analysis: CompositionAnalysis) -> Dict:
        """Generate comprehensive analysis report."""
        geographic_variance = self.get_geographic_variance()
        unique_chars = self.identify_unique_characteristics()

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_samples": analysis.sample_count,
                "regions_analyzed": len(analysis.geographic_clustering),
                "unique_colors": len(analysis.color_variety)
            },
            "composition_analysis": asdict(analysis),
            "geographic_variance": geographic_variance,
            "unique_characteristics": unique_chars,
            "recommendations": self._generate_recommendations(analysis)
        }

        return report

    @staticmethod
    def _generate_recommendations(analysis: CompositionAnalysis) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if analysis.average_grain_size < 0.125:
            recommendations.append("Fine sand detected - suitable for precision applications")

        if analysis.average_grain_size > 0.5:
            recommendations.append("Coarse sand detected - suitable for construction aggregates")

        if analysis.average_magnetite > 10:
            recommendations.append("High magnetite content - consider for magnetic separator testing")

        if analysis.average_shell_content > 20:
            recommendations.append("Significant shell fragments - ideal for marine ecosystem studies")

        if len(analysis.geographic_clustering) > 3:
            recommendations.append("Diverse geographic sources - comprehensive global representation")

        return recommendations


def create_sample_dataset() -> List[SandSample]:
    """Create a sample dataset of sand from different beaches."""
    samples = [
        SandSample(
            beach_name="Waikiki Beach",
            country="United States",
            region=BeachRegion.TROPICAL,
            primary_composition=SandType.VOLCANIC,
            grain_size_mm=0.35,
            color="Black",
            magnetite_percentage=15.5,
            shell_fragment_percentage=8.2,
            latitude=21.2793,
            longitude=-157.8292,
            collection_date="2024-01-15"
        ),
        SandSample(
            beach_name="Copacabana Beach",
            country="Brazil",
            region=BeachRegion.TROPICAL,
            primary_composition=SandType.QUARTZ,
            grain_size_mm=0.28,
            color="White",
            magnetite_percentage=3.2,
            shell_fragment_percentage=5.1,
            latitude=-22.9829,
            longitude=-43.1899,
            collection_date="2024-01-16"
        ),
        SandSample(
            beach_name="Bondi Beach",
            country="Australia",
            region=BeachRegion.TEMPERATE,
            primary_composition=SandType.QUARTZ,
            grain_size_mm=0.31,
            color="Golden",
            magnetite_percentage=2.8,
            shell_fragment_percentage=12.4,
            latitude=-33.8915,
            longitude=151.2760,
            collection_date="2024-01-17"
        ),
        SandSample(
            beach_name="Siwa Oasis Beach",
            country="Egypt",
            region=BeachRegion.DESERT,
            primary_composition=SandType.QUARTZ,
            grain_size_mm=0.15,
            color="Orange",
            magnetite_percentage=1.5,
            shell_fragment_percentage=0.3,
            latitude=29.0369,
            longitude=25.5154,
            collection_date="2024-01-18"
        ),
        SandSample(
            beach_name="Black Sand Beach",
            country="Iceland",
            region=BeachRegion.VOLCANIC,
            primary_composition=SandType.VOLCANIC,
            grain_size_mm=0.42,
            color="Black",
            magnetite_percentage=22.3,
            shell_fragment_percentage=2.1,
            latitude=63.8817,
            longitude=-19.0208,
            collection_date="2024-01-19"
        ),
        SandSample(
            beach_name="Matira Beach",
            country="French Polynesia",
            region=BeachRegion.ISLAND,
            primary_composition=SandType.CORAL,
            grain_size_mm=0.45,
            color="White-Pink",
            magnetite_percentage=0.8,
            shell_fragment_percentage=35.6,
            latitude=-16.2157,
            longitude=-151.7356,
            collection_date="2024-01-20"
        ),
        SandSample(
            beach_name="Brighton Beach",
            country="United Kingdom",
            region=BeachRegion.TEMPERATE,
            primary_composition=SandType.QUARTZ,
            grain_size_mm=0.25,
            color="Brown-Gray",
            magnetite_percentage=4.2,
            shell_fragment_percentage=18.7,
            latitude=50.8201,
            longitude=-0.0802,
            collection_date="2024-01-21"
        ),
        SandSample(
            beach_name="Anse Source d'Argent",
            country="Seychelles",
            region=BeachRegion.ISLAND,
            primary_composition=SandType.GRANITE,
            grain_size_mm=0.55,
            color="Pink",
            magnetite_percentage=6.1,
            shell_fragment_percentage=14.2,
            latitude=-4.3470,
            longitude=55.8668,
            collection_date="2024-01-22"
        ),
    ]
    return samples


def main():
    """Main entry point for sand analysis application."""
    parser = argparse.ArgumentParser(
        description="Analyze sand composition from beaches worldwide",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --analyze
  %(prog)s --analyze --verbose
  %(prog)s --find-similar "Waikiki Beach" --threshold 0.7
  %(prog)s --geographic-report
        """
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Perform composition analysis on sample data"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--geographic-report",
        action="store_true",
        help="Generate geographic variance report"
    )

    parser.add_argument(
        "--find-similar",
        type=str,
        metavar="BEACH_NAME",
        help="Find beaches similar to specified beach"
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        metavar="SCORE",
        help="Similarity threshold (0-1, default: 0.75)"
    )

    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output results as JSON"
    )

    args = parser.parse_args()

    analyzer = SandAnalyzer(verbose=args.verbose)
    samples = create_sample_dataset()
    analyzer.add_multiple_samples(samples)

    if args.analyze:
        analysis = analyzer.analyze_composition()
        report = analyzer.generate_report(analysis)

        if args.output_json:
            print(json.dumps(report, indent=2))
        else:
            print("\n=== SAND COMPOSITION ANALYSIS REPORT ===\n")
            print(f"Timestamp: {report['timestamp']}")
            print(f"Total Samples Analyzed: {report['summary']['total_samples']}")
            print(f"Regions Covered: {report['summary']['regions_analyzed']}")
            print(f"Unique Colors: {report['summary']['unique_colors']}")

            print("\n--- Composition Statistics ---")
            comp = report['composition_analysis']
            print(f"Average Grain Size: {comp['average_grain_size']:.3f} mm")
            print(f"Grain Size Std Dev: {comp['grain_size_std_dev']:.3f} mm")
            print(f"Average Magnetite: {comp['average_magnetite']:.2f}%")
            print(f"Average Shell Content: {comp['average_shell_content']:.2f}%")
            print(f"Dominant Sand Type: {comp['dominant_sand_type']}")

            print("\n--- Composition Distribution ---")
            for sand_type, count in comp['composition_distribution'].items():
                print(f"  {sand_type}: {count} samples")

            print("\n--- Recommendations ---")
            for rec in report['recommendations']:
                print(f"  • {rec}")

    elif args.geographic_report:
        variance = analyzer.get_geographic_variance()

        if args.output_json:
            print(json.dumps(variance, indent=2))
        else:
            print("\n=== GEOGRAPHIC VARIANCE REPORT ===\n")
            for region, stats in sorted(variance.items()):
                print(f"{region.upper()}:")
                print(f"  Samples: {stats['count']}")
                print(f"  Mean Grain Size: {stats['mean_grain_size']:.3f} mm")
                print(f"  Variance: {stats['variance']:.4f}")
                print(f"  Range: {stats['min_size']:.3f} - {stats['max_size']:.3f} mm")

    elif args.find_similar:
        reference = None
        for sample in analyzer.samples:
            if sample.beach_name.lower() == args.find_similar.lower():
                reference = sample
                break

        if not reference:
            print(f"Error: Beach '{args.find_similar}' not found in dataset")
            sys.exit(1)

        similar = analyzer.find_similar_beaches(reference, args.threshold)

        if args.output_json:
            results = {
                "reference": asdict(reference),
                "similar_beaches": [
                    {"sample": asdict(s), "similarity_score": score}
                    for s, score in similar
                ]
            }
            print(json.dumps(results, indent=2))
        else:
            print(f"\n=== BEACHES SIMILAR TO {reference.beach_name.upper()} ===\n")
            print(f"Reference: {reference.beach_name}, {reference.country}")
            print(f"Composition: {reference.primary_composition.value}")
            print(f"Grain Size: {reference.grain_size_mm} mm")

            if similar:
                print(f"\nFound {len(similar)} similar beach(es):\n")
                for sample, score in similar:
                    print(f"  {sample.beach_name}, {sample.country}")
                    print(f"    Similarity Score: {score:.2%}")
                    print(f"    Composition: {sample.primary_composition.value}")
                    print(f"    Grain Size: {sample.grain_size_mm} mm")
            else:
                print("\nNo similar beaches found with the given threshold.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()