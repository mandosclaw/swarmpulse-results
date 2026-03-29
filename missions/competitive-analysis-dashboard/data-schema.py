#!/usr/bin/env python3
# Task: Define data sources and schema | Mission: Competitive Analysis Dashboard
"""
Unified data schema for competitive intelligence.
Normalizes G2, Capterra, GitHub, LinkedIn, news feed data into competitor profiles.

Install: pip install (stdlib only)
Usage:   python data-schema.py
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json

@dataclass
class CompetitorProfile:
    id: str
    name: str
    website: str
    founded_year: Optional[int]=None
    employee_count: Optional[int]=None
    funding_total_usd: Optional[int]=None
    primary_category: str=""
    created_at: datetime=field(default_factory=datetime.now)

@dataclass
class ReviewDataPoint:
    competitor_id: str
    platform: str
    overall_rating: float
    ease_of_use: Optional[float]=None
    customer_support: Optional[float]=None
    review_count: int=0
    captured_at: datetime=field(default_factory=datetime.now)

@dataclass
class PricingTier:
    competitor_id: str
    tier_name: str
    monthly_price_usd: Optional[float]=None
    annual_price_usd: Optional[float]=None
    max_users: Optional[int]=None
    key_features: list=field(default_factory=list)
    is_free_tier: bool=False

@dataclass
class FeatureMatrix:
    competitor_id: str
    feature_name: str
    available: bool
    maturity: str="unknown"
    notes: str=""

@dataclass
class SocialMetrics:
    competitor_id: str
    platform: str
    followers: int=0
    weekly_growth_pct: float=0.0
    github_stars: int=0
    github_forks: int=0

@dataclass
class NewsItem:
    competitor_id: str
    headline: str
    url: str
    source: str
    sentiment: str="neutral"
    category: str="general"

SCHEMA_VERSION = "1.0.0"

def sample_data():
    competitors=[
        CompetitorProfile(id="comp_dd",name="Datadog",website="https://datadoghq.com",
            founded_year=2010,employee_count=5000,funding_total_usd=340_000_000,primary_category="observability"),
        CompetitorProfile(id="comp_nr",name="New Relic",website="https://newrelic.com",
            founded_year=2008,employee_count=2200,primary_category="observability"),
    ]
    reviews=[
        ReviewDataPoint(competitor_id="comp_dd",platform="g2",overall_rating=4.3,ease_of_use=4.1,review_count=2450),
        ReviewDataPoint(competitor_id="comp_nr",platform="g2",overall_rating=4.1,ease_of_use=3.9,review_count=890),
    ]
    pricing=[
        PricingTier(competitor_id="comp_dd",tier_name="Infrastructure",monthly_price_usd=15.0,key_features=["metrics","dashboards","alerts"]),
        PricingTier(competitor_id="comp_dd",tier_name="Free",monthly_price_usd=0,is_free_tier=True,key_features=["5 hosts","1 day retention"]),
    ]
    features=[
        FeatureMatrix(competitor_id="comp_dd",feature_name="Real-time Monitoring",available=True,maturity="production"),
        FeatureMatrix(competitor_id="comp_nr",feature_name="Real-time Monitoring",available=True,maturity="production"),
    ]
    social=[
        SocialMetrics(competitor_id="comp_dd",platform="github",github_stars=8500,github_forks=1200),
        SocialMetrics(competitor_id="comp_nr",platform="linkedin",followers=125000,weekly_growth_pct=2.3),
    ]
    news=[
        NewsItem(competitor_id="comp_dd",headline="Datadog expands observability platform",url="https://example.com/1",source="TechCrunch",sentiment="positive",category="product"),
        NewsItem(competitor_id="comp_nr",headline="New Relic reports Q3 earnings",url="https://example.com/2",source="Reuters",sentiment="neutral",category="finance"),
    ]
    return {
        "schema_version":SCHEMA_VERSION,
        "competitors":len(competitors),
        "reviews":len(reviews),
        "pricing":len(pricing),
        "features":len(features),
        "social_metrics":len(social),
        "news_items":len(news),
    }

if __name__=="__main__":
    print("=== Competitive Analysis Schema ===")
    print(json.dumps(sample_data(),indent=2))
    print(f"\nSchema entities: CompetitorProfile, ReviewDataPoint, PricingTier, FeatureMatrix, SocialMetrics, NewsItem")