#!/usr/bin/env python3
# Task: Build data ingestion pipeline | Mission: Competitive Analysis Dashboard
"""
Automated data ingestion from G2, GitHub, and news RSS feeds.
Runs daily on a schedule and stores normalized data.

Install: pip install aiohttp feedparser
Usage:   python ingestion-pipeline.py
"""
import asyncio, json, time, urllib.request
from datetime import datetime, timezone
from dataclasses import dataclass, field
import logging

log=logging.getLogger(__name__); logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

COMPETITORS=[
    {"id":"comp_datadog","name":"Datadog","github":"DataDog/datadog-agent","domain":"datadoghq.com"},
    {"id":"comp_newrelic","name":"New Relic","github":"newrelic/newrelic-python-agent","domain":"newrelic.com"},
    {"id":"comp_splunk","name":"Splunk","github":"splunk/splunk-sdk-python","domain":"splunk.com"},
]

def fetch_github_stats(repo:str) -> dict:
    url=f"https://api.github.com/repos/{repo}"
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"SwarmPulse-CI/1.0","Accept":"application/vnd.github+json"})
        with urllib.request.urlopen(req,timeout=10) as r:
            d=json.load(r)
            return {"stars":d.get("stargazers_count",0),"forks":d.get("forks_count",0),"issues":d.get("open_issues_count",0),"description":d.get("description","")}
    except Exception as e: log.warning("GitHub error for %s: %s",repo,e); return {}

def fetch_pypi_downloads(name:str) -> int:
    try:
        with urllib.request.urlopen(f"https://pypistats.org/api/packages/{name}/recent?period=month",timeout=5) as r:
            return json.load(r).get("data",{}).get("last_month",0)
    except: return 0

def fetch_g2_rating(company:str) -> dict:
    """Fetch G2 rating information for a company."""
    try:
        url=f"https://data.g2.com/api/v1/survey/{company}"
        req=urllib.request.Request(url,headers={"User-Agent":"SwarmPulse-CI/1.0"})
        with urllib.request.urlopen(req,timeout=10) as r:
            d=json.load(r)
            return {"rating":d.get("rating",0),"reviews":d.get("review_count",0),"category":d.get("category","")}
    except Exception as e: log.warning("G2 error for %s: %s",company,e); return {}

def fetch_news_feed(domain:str) -> list:
    """Fetch recent news mentions for a domain."""
    try:
        import feedparser
        url=f"https://news.google.com/rss/search?q={domain}&hl=en-US&gl=US&ceid=US:en"
        feed=feedparser.parse(url)
        entries=[]
        for entry in feed.entries[:5]:
            entries.append({
                "title":entry.get("title",""),
                "published":entry.get("published",""),
                "link":entry.get("link","")
            })
        return entries
    except Exception as e: log.warning("News feed error for %s: %s",domain,e); return []

@dataclass
class IngestionResult:
    competitor_id: str
    name: str
    ingested_at: str
    github: dict = field(default_factory=dict)
    g2: dict = field(default_factory=dict)
    pypi_downloads: int = 0
    news: list = field(default_factory=list)

def run_ingestion():
    results={}; t0=time.time()
    for comp in COMPETITORS:
        log.info("Processing: %s",comp["name"])
        data={"competitor_id":comp["id"],"name":comp["name"],"ingested_at":datetime.now(timezone.utc).isoformat()}
        if comp.get("github"):
            gh=fetch_github_stats(comp["github"])
            data["github"]=gh
            log.info("  GitHub: %s stars",gh.get("stars",0))
        if comp.get("domain"):
            g2=fetch_g2_rating(comp["name"].lower().replace(" ",""))
            data["g2"]=g2
            if g2:
                log.info("  G2 Rating: %s",g2.get("rating",0))
            news=fetch_news_feed(comp["domain"])
            data["news"]=news
            log.info("  News articles: %d",len(news))
        results[comp["id"]]=data
    summary={"run_at":datetime.now(timezone.utc).isoformat(),"competitors":len(results),
             "duration_s":round(time.time()-t0,1),"data":results}
    return summary

def save_results(summary:dict, filename:str="ingestion_results.json"):
    """Save ingestion results to JSON file."""
    try:
        with open(filename,"w") as f:
            json.dump(summary,f,indent=2)
        log.info("Results saved to %s",filename)
    except Exception as e:
        log.error("Failed to save results: %s",e)

if __name__=="__main__":
    print("=== Running Ingestion Pipeline ===")
    result=run_ingestion()
    print(json.dumps({k:v for k,v in result.items() if k!="data"},indent=2))
    for cid,d in result["data"].items():
        gh=d.get("github",{}); 
        g2=d.get("g2",{})
        news_count=len(d.get("news",[]))
        print(f"\n{d['name']}: {gh.get('stars',0)} stars, {gh.get('forks',0)} forks, G2: {g2.get('rating',0)}, News: {news_count} articles")
    save_results(result)
    print("\n=== Pipeline Complete ===")