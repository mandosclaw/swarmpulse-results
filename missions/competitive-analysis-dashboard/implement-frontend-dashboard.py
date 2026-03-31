#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Implement frontend dashboard
# Mission: Competitive Analysis Dashboard
# Agent:   @sue
# Date:    2026-03-31T19:14:10.958Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
Task: Implement frontend dashboard
Mission: Competitive Analysis Dashboard
Agent: @sue
Date: 2024-01-15

This module provides a complete backend Python service that generates
a competitive analysis dashboard by aggregating public competitor data,
visualizing trends, and producing weekly digest reports.
"""

import json
import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
import random
from collections import defaultdict


class CompetitorDataAggregator:
    """Aggregates public competitor data from various sources."""
    
    def __init__(self):
        self.competitors = {}
        self.market_data = defaultdict(list)
        self.trends = defaultdict(list)
    
    def add_competitor(self, name: str, industry: str, market_cap: float,
                      growth_rate: float, employees: int) -> None:
        """Add a competitor to the tracking system."""
        self.competitors[name] = {
            'name': name,
            'industry': industry,
            'market_cap': market_cap,
            'growth_rate': growth_rate,
            'employees': employees,
            'added_date': datetime.now().isoformat()
        }
    
    def add_market_data_point(self, competitor: str, metric: str, 
                             value: float, date: str = None) -> None:
        """Add a market data point for a competitor."""
        if date is None:
            date = datetime.now().isoformat()
        
        key = f"{competitor}:{metric}"
        self.market_data[key].append({
            'date': date,
            'value': value,
            'competitor': competitor,
            'metric': metric
        })
    
    def get_competitor(self, name: str) -> Dict[str, Any]:
        """Retrieve competitor information."""
        return self.competitors.get(name, {})
    
    def get_all_competitors(self) -> List[Dict[str, Any]]:
        """Get all tracked competitors."""
        return list(self.competitors.values())
    
    def get_market_data(self, competitor: str = None, 
                       metric: str = None) -> List[Dict[str, Any]]:
        """Retrieve market data with optional filtering."""
        results = []
        for key, data_points in self.market_data.items():
            comp, met = key.split(':')
            
            if competitor and comp != competitor:
                continue
            if metric and met != metric:
                continue
            
            results.extend(data_points)
        
        return sorted(results, key=lambda x: x['date'])


class TrendAnalyzer:
    """Analyzes trends in competitor data."""
    
    @staticmethod
    def calculate_trend(data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate trend direction and magnitude."""
        if len(data_points) < 2:
            return {
                'trend': 'insufficient_data',
                'direction': None,
                'magnitude': 0,
                'forecast': None
            }
        
        sorted_data = sorted(data_points, key=lambda x: x['date'])
        values = [p['value'] for p in sorted_data]
        
        change = values[-1] - values[0]
        percent_change = (change / values[0] * 100) if values[0] != 0 else 0
        
        direction = 'up' if change > 0 else 'down' if change < 0 else 'stable'
        
        avg_value = sum(values) / len(values)
        forecast = values[-1] + (change / (len(values) - 1)) if len(values) > 1 else values[-1]
        
        return {
            'trend': direction,
            'direction': 'positive' if change > 0 else 'negative' if change < 0 else 'neutral',
            'magnitude': abs(percent_change),
            'forecast': forecast,
            'current_value': values[-1],
            'previous_value': values[0],
            'data_points': len(values)
        }
    
    @staticmethod
    def identify_anomalies(data_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify anomalies in the data."""
        if len(data_points) < 3:
            return []
        
        values = [p['value'] for p in sorted(data_points, key=lambda x: x['date'])]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        anomalies = []
        threshold = 2.0
        
        sorted_data = sorted(data_points, key=lambda x: x['date'])
        for i, point in enumerate(sorted_data):
            if abs(point['value'] - mean) > threshold * std_dev:
                anomalies.append({
                    'date': point['date'],
                    'value': point['value'],
                    'deviation': abs(point['value'] - mean) / std_dev if std_dev > 0 else 0,
                    'type': 'spike' if point['value'] > mean else 'dip'
                })
        
        return anomalies


class WeeklyDigestGenerator:
    """Generates weekly digest reports."""
    
    @staticmethod
    def generate_digest(aggregator: CompetitorDataAggregator,
                       analyzer: TrendAnalyzer) -> Dict[str, Any]:
        """Generate a comprehensive weekly digest."""
        week_ago = datetime.now() - timedelta(days=7)
        week_ago_iso = week_ago.isoformat()
        
        digest = {
            'report_date': datetime.now().isoformat(),
            'period': 'weekly',
            'week_start': week_ago_iso,
            'summary': {
                'total_competitors': len(aggregator.get_all_competitors()),
                'metrics_tracked': len(aggregator.market_data),
                'anomalies_detected': 0
            },
            'competitor_summaries': [],
            'top_trends': [],
            'recommendations': []
        }
        
        all_anomalies = []
        
        for competitor in aggregator.get_all_competitors():
            comp_data = aggregator.get_market_data(competitor=competitor['name'])
            recent_data = [d for d in comp_data if d['date'] >= week_ago_iso]
            
            if not recent_data:
                continue
            
            metrics_by_type = defaultdict(list)
            for point in recent_data:
                metrics_by_type[point['metric']].append(point)
            
            comp_summary = {
                'competitor': competitor['name'],
                'metrics': {}
            }
            
            for metric, points in metrics_by_type.items():
                trend = analyzer.calculate_trend(points)
                anomalies = analyzer.identify_anomalies(points)
                
                comp_summary['metrics'][metric] = trend
                all_anomalies.extend(anomalies)
            
            digest['competitor_summaries'].append(comp_summary)
        
        digest['summary']['anomalies_detected'] = len(all_anomalies)
        
        trends_by_magnitude = []
        for summary in digest['competitor_summaries']:
            for metric, trend_data in summary['metrics'].items():
                trends_by_magnitude.append({
                    'competitor': summary['competitor'],
                    'metric': metric,
                    'magnitude': trend_data['magnitude'],
                    'direction': trend_data['direction'],
                    'forecast': trend_data['forecast']
                })
        
        digest['top_trends'] = sorted(
            trends_by_magnitude,
            key=lambda x: x['magnitude'],
            reverse=True
        )[:5]
        
        digest['anomalies'] = all_anomalies[:10]
        
        if digest['top_trends']:
            for trend in digest['top_trends'][:3]:
                if trend['direction'] == 'positive':
                    digest['recommendations'].append(
                        f"Monitor {trend['competitor']}'s growth in {trend['metric']} - "
                        f"showing {trend['magnitude']:.1f}% increase"
                    )
                else:
                    digest['recommendations'].append(
                        f"Investigate {trend['competitor']}'s decline in {trend['metric']} - "
                        f"showing {trend['magnitude']:.1f}% decrease"
                    )
        
        return digest


class DashboardAPIServer:
    """API server for the competitive analysis dashboard."""
    
    def __init__(self, aggregator: CompetitorDataAggregator,
                 analyzer: TrendAnalyzer,
                 digest_gen: WeeklyDigestGenerator):
        self.aggregator = aggregator
        self.analyzer = analyzer
        self.digest_gen = digest_gen
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        competitors = self.aggregator.get_all_competitors()
        all_market_data = self.aggregator.get_market_data()
        
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'competitors': competitors,
            'market_overview': {
                'total_competitors': len(competitors),
                'total_data_points': len(all_market_data),
                'industries': list(set(c['industry'] for c in competitors))
            },
            'metrics_summary': {}
        }
        
        metrics_by_type = defaultdict(list)
        for point in all_market_data:
            metrics_by_type[point['metric']].append(point)
        
        for metric, points in metrics_by_type.items():
            trend = self.analyzer.calculate_trend(points)
            dashboard['metrics_summary'][metric] = trend
        
        return dashboard
    
    def get_competitor_details(self, competitor_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific competitor."""
        competitor = self.aggregator.get_competitor(competitor_name)
        if not competitor:
            return {'error': 'Competitor not found'}
        
        market_data = self.aggregator.get_market_data(competitor=competitor_name)
        
        metrics_by_type = defaultdict(list)
        for point in market_data:
            metrics_by_type[point['metric']].append(point)
        
        details = {
            'competitor': competitor,
            'metrics': {}
        }
        
        for metric, points in metrics_by_type.items():
            trend = self.analyzer.calculate_trend(points)
            anomalies = self.analyzer.identify_anomalies(points)
            
            details['metrics'][metric] = {
                'trend': trend,
                'recent_data': points[-10:],
                'anomalies': anomalies
            }
        
        return details
    
    def get_weekly_digest(self) -> Dict[str, Any]:
        """Get the weekly digest report."""
        return self.digest_gen.generate_digest(self.aggregator, self.analyzer)
    
    def get_comparative_analysis(self, competitors: List[str] = None,
                               metric: str = None) -> Dict[str, Any]:
        """Compare multiple competitors on specific metrics."""
        if not competitors:
            competitors = [c['name'] for c in self.aggregator.get_all_competitors()]
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'competitors_compared': competitors,
            'comparisons': {}
        }
        
        for competitor in competitors:
            comp_data = self.aggregator.get_market_data(competitor=competitor)
            
            if metric:
                comp_data = [d for d in comp_data if d['metric'] == metric]
            
            if comp_data:
                metrics_by_type = defaultdict(list)
                for point in comp_data:
                    metrics_by_type[point['metric']].append(point)
                
                for met, points in metrics_by_type.items():
                    key = f"{competitor}:{met}"
                    analysis['comparisons'][key] = self.analyzer.calculate_trend(points)
        
        return analysis


def generate_sample_data(aggregator: CompetitorDataAggregator) -> None:
    """Generate realistic sample competitor data."""
    competitors = [
        ('TechCorp', 'Technology', 500_000_000, 0.15, 5000),
        ('InnovateLabs', 'Technology', 350_000_000, 0.22, 3500),
        ('DataSystems', 'Technology', 200_000_000, 0.18, 2000),
        ('CloudFirst', 'Cloud Services', 450_000_000, 0.20, 4500),
        ('AI Solutions', 'Artificial Intelligence', 150_000_000, 0.35, 1200),
    ]
    
    for name, industry, market_cap, growth, employees in competitors:
        aggregator.add_competitor(name, industry, market_cap, growth, employees)
    
    base_date = datetime.now() - timedelta(days=30)
    metrics = ['revenue', 'market_cap', 'employee_count', 'customer_satisfaction']
    
    for competitor_name, _, _, _, _ in competitors:
        for metric in metrics:
            base_value = random.uniform(100, 1000)
            trend = random.uniform(-0.02, 0.05)
            
            for i in range(31):
                current_date = (base_date + timedelta(days=i)).isoformat()
                value = base_value * ((1 + trend) ** i) + random.uniform(-10, 10)
                aggregator.add_market_data_point(competitor_name, metric, value, current_date)


def main():
    """Main entry point with CLI interface."""
    parser = argparse.ArgumentParser(
        description='Competitive Analysis Dashboard Backend Service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python solution.py --generate-sample
  python solution.py --dashboard
  python solution.py --digest
  python solution.py --compare TechCorp InnovateLabs --metric revenue
  python solution.py --details TechCorp
        '''
    )
    
    parser.add_argument('--generate-sample', action='store_true',
                       help='Generate sample competitor data')
    parser.add_argument('--dashboard', action='store_true',
                       help='Display complete dashboard data')
    parser.add_argument('--digest', action='store_true',
                       help='Generate and display weekly digest')
    parser.add_argument('--details', type=str, metavar='COMPETITOR',
                       help='Show detailed analysis for a competitor')
    parser.add_argument('--compare', nargs='+', metavar='COMPETITOR',
                       help='Compare multiple competitors')
    parser.add_argument('--metric', type=str,
                       help='Filter by specific metric')
    parser.add_argument('--output-format', choices=['json', 'pretty'],
                       default='pretty',
                       help='Output format (default: pretty)')
    parser.add_argument('--add-competitor', type=str, nargs=5,
                       metavar=('NAME', 'INDUSTRY', 'MARKET_CAP', 'GROWTH_RATE', 'EMPLOYEES'),
                       help='Add a new competitor')
    parser.add_argument('--add-data-point', type=str, nargs=4,
                       metavar=('COMPETITOR', 'METRIC', 'VALUE', 'DATE'),
                       help='Add a market data point')
    
    args = parser.parse_args()
    
    aggregator = CompetitorDataAggregator()
    analyzer = TrendAnalyzer()
    digest_gen = WeeklyDigestGenerator()
    api_server = DashboardAPIServer(aggregator, analyzer, digest_gen)
    
    if args.generate_sample:
        generate_sample_data(aggregator)
        print("Sample data generated successfully.")
        return
    
    if args.add_competitor:
        name, industry, market_cap, growth_rate, employees = args.add_competitor
        aggregator.add_competitor(
            name, industry, float(market_cap),
            float(growth_rate), int(employees)
        )
        print(f"Added competitor: {name}")
        return
    
    if args.add_data_point:
        competitor, metric, value, date = args.add_data_point
        aggregator.add_market_data_point(competitor, metric, float(value), date)
        print(f"Added data point for {competitor} - {metric}")
        return
    
    if not any([args.dashboard, args.digest, args.details, args.compare]):
        generate_sample_data(aggregator)
    
    if args.dashboard:
        data = api_server.get_dashboard_data()
        output = json.dumps(data, indent=2) if args.output_format == 'json' else format_pretty(data)
        print(output)
        return
    
    if args.digest:
        digest = api_server.get_weekly_digest()
        output = json.dumps(digest, indent=2) if args.output_format == 'json' else format_pretty(digest)
        print(output)
        return
    
    if args.details:
        details = api_server.get_competitor_details(args.details)
        output = json.dumps(details, indent=2) if args.output_format == 'json' else format_pretty(details)
        print(output)
        return
    
    if args.compare:
        analysis = api_server.get_comparative_analysis(args.compare, args.metric)
        output = json.dumps(analysis, indent=2) if args.output_format == 'json' else format_pretty(analysis)
        print(output)
        return


def format_pretty(data: Dict[str, Any]) -> str:
    """Format data for pretty printing."""
    def format_value(value: Any, indent: int = 0) -> str:
        prefix = "  " * indent
        
        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            for k, v in value.items():
                formatted = format_value(v, indent + 1)
                lines.append(f"{prefix}  {k}: {formatted},")
            lines.append(f"{prefix}}}")
            return "\n".join(lines)
        
        elif isinstance(value, list):
            if not value:
                return "[]"
            if len(value) <= 3 and all(isinstance(v, (str, int, float, bool)) for v in value):
                return f"[{', '.join(str(v) for v in value)}]"
            lines = ["["]
            for item in value[:10]:
                formatted = format_value(item, indent + 1)
                lines.append(f"{prefix}  {formatted},")
            if len(value) > 10:
                lines.append(f"{prefix}  ... ({len(value) - 10} more items)")
            lines.append(f"{prefix}]")
            return "\n".join(lines)
        
        elif isinstance(value, float):
            return f"{value:.2f}"
        else:
            return str(value)
    
    return format_value(data)


if __name__ == '__main__':
    main()