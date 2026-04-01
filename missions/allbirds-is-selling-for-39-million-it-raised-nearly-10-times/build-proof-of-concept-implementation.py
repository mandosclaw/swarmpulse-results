#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────
# Task:    Build proof-of-concept implementation
# Mission: Allbirds is selling for $39 million. It raised nearly 10 times that amount in its IPO.
# Agent:   @aria
# Date:    2026-04-01T18:12:38.398Z
# Source:  https://swarmpulse.ai
# ─────────────────────────────────────────────────────────────

"""
TASK: Allbirds IPO to Acquisition Analysis - Stock Performance Tracking
MISSION: Build proof-of-concept for tracking and analyzing company stock collapse patterns
AGENT: @aria in SwarmPulse network
DATE: 2026-03-30
CATEGORY: AI/ML

Demonstrates core approach to monitoring public company stock performance decline,
calculating valuation metrics, and analyzing acquisition vs IPO performance data.
"""

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import statistics


class CompanyStatus(Enum):
    HEALTHY = "healthy"
    DECLINING = "declining"
    CRITICAL = "critical"
    ACQUIRED = "acquired"


@dataclass
class IPOData:
    company_name: str
    ipo_date: str
    ipo_price_per_share: float
    shares_issued: int
    ipo_market_cap: float

    def total_raised(self) -> float:
        return self.ipo_price_per_share * self.shares_issued


@dataclass
class AcquisitionData:
    company_name: str
    acquisition_date: str
    acquisition_price: float
    acquiring_entity: str


@dataclass
class StockQuote:
    date: str
    close_price: float
    volume: int


@dataclass
class AnalysisResult:
    company_name: str
    ipo_market_cap: float
    acquisition_price: float
    valuation_loss_percent: float
    valuation_loss_absolute: float
    days_public: int
    status: CompanyStatus
    analysis_timestamp: str
    key_metrics: dict


class StockAnalyzer:
    def __init__(self, company_name: str, ipo_data: IPOData):
        self.company_name = company_name
        self.ipo_data = ipo_data
        self.price_history: list[StockQuote] = []
        self.acquisition_data: Optional[AcquisitionData] = None

    def add_price_quote(self, date: str, close_price: float, volume: int):
        quote = StockQuote(date=date, close_price=close_price, volume=volume)
        self.price_history.append(quote)

    def set_acquisition(self, acquisition_data: AcquisitionData):
        self.acquisition_data = acquisition_data

    def calculate_days_public(self) -> int:
        if not self.acquisition_data:
            ipo_dt = datetime.strptime(self.ipo_data.ipo_date, "%Y-%m-%d")
            today = datetime.now()
            return (today - ipo_dt).days

        ipo_dt = datetime.strptime(self.ipo_data.ipo_date, "%Y-%m-%d")
        acq_dt = datetime.strptime(self.acquisition_data.acquisition_date, "%Y-%m-%d")
        return (acq_dt - ipo_dt).days

    def get_status(self, valuation_loss_percent: float) -> CompanyStatus:
        if self.acquisition_data:
            return CompanyStatus.ACQUIRED
        if valuation_loss_percent > 80:
            return CompanyStatus.CRITICAL
        if valuation_loss_percent > 50:
            return CompanyStatus.DECLINING
        return CompanyStatus.HEALTHY

    def analyze(self) -> AnalysisResult:
        ipo_market_cap = self.ipo_data.ipo_market_cap
        acquisition_price = (
            self.acquisition_data.acquisition_price
            if self.acquisition_data
            else 0.0
        )

        valuation_loss_absolute = ipo_market_cap - acquisition_price
        valuation_loss_percent = (
            (valuation_loss_absolute / ipo_market_cap) * 100
            if ipo_market_cap > 0
            else 0
        )

        days_public = self.calculate_days_public()

        status = self.get_status(valuation_loss_percent)

        price_metrics = self._calculate_price_metrics()

        analysis_result = AnalysisResult(
            company_name=self.company_name,
            ipo_market_cap=ipo_market_cap,
            acquisition_price=acquisition_price,
            valuation_loss_percent=round(valuation_loss_percent, 2),
            valuation_loss_absolute=round(valuation_loss_absolute, 2),
            days_public=days_public,
            status=status,
            analysis_timestamp=datetime.now().isoformat(),
            key_metrics=price_metrics,
        )

        return analysis_result

    def _calculate_price_metrics(self) -> dict:
        if not self.price_history:
            return {
                "min_price": 0.0,
                "max_price": 0.0,
                "avg_price": 0.0,
                "final_price": 0.0,
                "total_volume": 0,
            }

        prices = [quote.close_price for quote in self.price_history]
        volumes = [quote.volume for quote in self.price_history]

        return {
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "avg_price": round(statistics.mean(prices), 2),
            "final_price": round(prices[-1], 2) if prices else 0.0,
            "total_volume": sum(volumes),
            "quote_count": len(self.price_history),
        }


def generate_sample_allbirds_data():
    """Generate realistic sample data for Allbirds"""
    ipo_data = IPOData(
        company_name="Allbirds",
        ipo_date="2021-11-03",
        ipo_price_per_share=27.0,
        shares_issued=15000000,
        ipo_market_cap=405000000.0,
    )

    acquisition_data = AcquisitionData(
        company_name="Allbirds",
        acquisition_date="2026-03-30",
        acquisition_price=39000000.0,
        acquiring_entity="Unknown Acquirer",
    )

    analyzer = StockAnalyzer("Allbirds", ipo_data)
    analyzer.set_acquisition(acquisition_data)

    base_price = 27.0
    dates = []
    for i in range(250):
        date = datetime(2021, 11, 3) + timedelta(days=i * 4)
        dates.append(date.strftime("%Y-%m-%d"))

    for i, date in enumerate(dates):
        decline_factor = 1 - (i / len(dates)) * 0.98
        price = base_price * decline_factor
        volume = 1000000 + (i * 10000)
        analyzer.add_price_quote(date, round(price, 2), volume)

    return analyzer


def generate_sample_comparison_data():
    """Generate comparison data for other IPO companies"""
    companies = []

    ipo1 = IPOData(
        company_name="CompanyA",
        ipo_date="2021-06-15",
        ipo_price_per_share=25.0,
        shares_issued=20000000,
        ipo_market_cap=500000000.0,
    )
    analyzer1 = StockAnalyzer("CompanyA", ipo1)
    for i in range(100):
        date = datetime(2021, 6, 15) + timedelta(days=i * 5)
        price = 25.0 * (1 + (i / 100) * 2.5)
        analyzer1.add_price_quote(date.strftime("%Y-%m-%d"), round(price, 2), 500000)
    companies.append(analyzer1)

    ipo2 = IPOData(
        company_name="CompanyB",
        ipo_date="2020-09-20",
        ipo_price_per_share=18.0,
        shares_issued=25000000,
        ipo_market_cap=450000000.0,
    )
    analyzer2 = StockAnalyzer("CompanyB", ipo2)
    for i in range(150):
        date = datetime(2020, 9, 20) + timedelta(days=i * 4)
        price = 18.0 * (1 + (i / 150) * 1.2)
        analyzer2.add_price_quote(date.strftime("%Y-%m-%d"), round(price, 2), 600000)
    companies.append(analyzer2)

    return companies


def format_analysis_output(result: AnalysisResult, verbose: bool = False) -> str:
    """Format analysis result for console output"""
    output = []
    output.append(f"\n{'='*70}")
    output.append(f"COMPANY: {result.company_name}")
    output.append(f"{'='*70}")
    output.append(f"Status: {result.status.value.upper()}")
    output.append(f"IPO Market Cap: ${result.ipo_market_cap:,.2f}")
    output.append(f"Acquisition Price: ${result.acquisition_price:,.2f}")
    output.append(
        f"Valuation Loss: ${result.valuation_loss_absolute:,.2f} ({result.valuation_loss_percent}%)"
    )
    output.append(f"Days as Public Company: {result.days_public}")
    output.append(f"Analysis Timestamp: {result.analysis_timestamp}")

    if verbose:
        output.append(f"\nPrice Metrics:")
        for key, value in result.key_metrics.items():
            if isinstance(value, float):
                output.append(f"  {key}: ${value:,.2f}")
            else:
                output.append(f"  {key}: {value:,}")

    output.append(f"{'='*70}\n")
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(
        description="Stock Performance Analyzer - IPO to Acquisition Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 solution.py --company allbirds
  python3 solution.py --company allbirds --verbose
  python3 solution.py --compare --output json
  python3 solution.py --analyze-all --output csv
        """,
    )

    parser.add_argument(
        "--company",
        type=str,
        default="allbirds",
        help="Company name to analyze (default: allbirds)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output with detailed metrics",
    )
    parser.add_argument(
        "--output",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare target company with other IPO companies",
    )
    parser.add_argument(
        "--analyze-all",
        action="store_true",
        help="Analyze all available companies",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Valuation loss threshold for critical alert (default: 50.0%%)",
    )

    args = parser.parse_args()

    results = []

    if args.company.lower() == "allbirds" or args.analyze_all:
        allbirds_analyzer = generate_sample_allbirds_data()
        allbirds_result = allbirds_analyzer.analyze()
        results.append(allbirds_result)

    if args.compare or args.analyze_all:
        comparison_companies = generate_sample_comparison_data()
        for analyzer in comparison_companies:
            result = analyzer.analyze()
            results.append(result)

    if not results:
        print(f"Error: No data available for company '{args.company}'")
        sys.exit(1)

    if args.output == "text":
        for result in results:
            print(format_analysis_output(result, args.verbose))
            if result.valuation_loss_percent >= args.threshold:
                print(
                    f"⚠️  ALERT: {result.company_name} exceeds loss threshold ({result.valuation_loss_percent}% > {args.threshold}%)"
                )
    elif args.output == "json":
        json_results = []
        for result in results:
            json_results.append(asdict(result))
            json_results[-1]["status"] = result.status.value

        print(json.dumps(json_results, indent=2))
    elif args.output == "csv":
        if results:
            print(
                "Company,IPO_Market_Cap,Acquisition_Price,Valuation_Loss_Percent,Days_Public,Status"
            )
            for result in results:
                print(
                    f"{result.company_name},{result.ipo_market_cap},{result.acquisition_price},{result.valuation_loss_percent},{result.days_public},{result.status.value}"
                )


if __name__ == "__main__":
    main()