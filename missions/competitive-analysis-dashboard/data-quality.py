#!/usr/bin/env python3
# Task: Review data quality and coverage | Mission: Competitive Analysis Dashboard
"""
Data quality validation for competitive analysis dataset.
Checks completeness, freshness, consistency, and coverage of competitor data.

Install: pip install (stdlib only)
Usage:   python data-quality.py
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Any

QUALITY_RULES = [
    {"name":"rating_in_range","field":"overall_rating","check":lambda x: 0<=x<=5,"msg":"Rating must be 0-5"},
    {"name":"review_count_positive","field":"review_count","check":lambda x: x>=0,"msg":"Review count must be >=0"},
    {"name":"name_not_empty","field":"name","check":lambda x: bool(x and x.strip()),"msg":"Name must not be empty"},
    {"name":"website_format","field":"website","check":lambda x: x.startswith("http"),"msg":"Website must start with http"},
]

def check_freshness(captured_at_str:str, max_age_hours:int=48) -> tuple[bool,str]:
    try:
        dt=datetime.fromisoformat(captured_at_str)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        age=(datetime.now(timezone.utc)-dt).total_seconds()/3600
        if age>max_age_hours: return False,f"Data is {age:.1f}h old (max {max_age_hours}h)"
        return True,f"Fresh ({age:.1f}h old)"
    except: return False,"Invalid timestamp"

def check_completeness(record:dict, required_fields:list) -> tuple[float,list]:
    missing=[f for f in required_fields if not record.get(f)]
    pct=(len(required_fields)-len(missing))/len(required_fields)*100 if required_fields else 100
    return pct,missing

def run_quality_report(dataset:list[dict], entity_type:str) -> dict:
    total=len(dataset); errors=[]; warnings=[]; passed=0
    required_by_type={
        "competitor":["id","name","website","primary_category"],
        "review":["competitor_id","platform","overall_rating","review_count"],
        "pricing":["competitor_id","tier_name"],
    }
    required=required_by_type.get(entity_type,[])
    for i,record in enumerate(dataset):
        record_errors=[]; record_warnings=[]
        completeness,missing=check_completeness(record,required)
        if missing: record_errors.append(f"Missing fields: {missing}")
        for rule in QUALITY_RULES:
            val=record.get(rule["field"])
            if val is not None:
                try:
                    if not rule["check"](val): record_errors.append(f"{rule['name']}: {rule['msg']}")
                except: record_warnings.append(f"Could not check {rule['name']}")
        if "captured_at" in record:
            fresh,msg=check_freshness(record["captured_at"])
            if not fresh: record_warnings.append(msg)
        if not record_errors: passed+=1
        errors.extend(f"Record {i}: {e}" for e in record_errors)
        warnings.extend(f"Record {i}: {w}" for w in record_warnings)
    return {"entity_type":entity_type,"total_records":total,"passed":passed,
            "failed":total-passed,"pass_rate":round(passed/total*100,1) if total else 0,
            "errors":errors[:20],"warnings":warnings[:20]}

def coverage_report(competitors:list, review_map:dict, pricing_map:dict) -> dict:
    no_reviews=[c["name"] for c in competitors if c["id"] not in review_map]
    no_pricing=[c["name"] for c in competitors if c["id"] not in pricing_map]
    return {"total_competitors":len(competitors),
            "with_reviews":len(competitors)-len(no_reviews),"without_reviews":no_reviews,
            "with_pricing":len(competitors)-len(no_pricing),"without_pricing":no_pricing,
            "coverage_pct":round((1-len(no_reviews)/len(competitors))*100,1) if competitors else 0}

if __name__=="__main__":
    competitors=[
        {"id":"c1","name":"Datadog","website":"https://datadoghq.com","primary_category":"observability","captured_at":datetime.now(timezone.utc).isoformat()},
        {"id":"c2","name":"","website":"not-a-url","primary_category":"","captured_at":"2026-01-01T00:00:00Z"},
    ]
    reviews=[
        {"competitor_id":"c1","platform":"g2","overall_rating":4.3,"review_count":2450,"captured_at":datetime.now(timezone.utc).isoformat()},
        {"competitor_id":"c1","platform":"g2","overall_rating":6.0,"review_count":-1,"captured_at":datetime.now(timezone.utc).isoformat()},
    ]
    print("=== Data Quality Report ===")
    for entity,data in [("competitor",competitors),("review",reviews)]:
        r=run_quality_report(data,entity)
        print(f"\n{entity.upper()}: {r['pass_rate']}% pass rate ({r['passed']}/{r['total_records']})")
        if r["errors"]: print("  Errors:",r["errors"])
        if r["warnings"]: print("  Warnings:",r["warnings"])
    review_map={"c1": True}; pricing_map={}
    cov=coverage_report(competitors,review_map,pricing_map)
    print(f"\nCoverage: {cov['coverage_pct']}% have reviews")
    if cov["without_pricing"]: print(f"No pricing data: {cov['without_pricing']}")