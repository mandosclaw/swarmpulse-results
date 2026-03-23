#!/usr/bin/env python3
# Task: Implement frontend dashboard | Mission: Competitive Analysis Dashboard
"""
FastAPI REST backend for competitive analysis dashboard.

Install: pip install fastapi uvicorn
Usage:   uvicorn frontend-dashboard:app --reload --port 8000
         Visit: http://localhost:8000/docs
"""
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

app = FastAPI(title="Competitive Analysis API", version="1.0.0")

COMPETITORS = {
    "comp_dd": {"id":"comp_dd","name":"Datadog","website":"https://datadoghq.com","category":"observability"},
    "comp_nr": {"id":"comp_nr","name":"New Relic","website":"https://newrelic.com","category":"observability"},
    "comp_sp": {"id":"comp_sp","name":"Splunk","website":"https://splunk.com","category":"SIEM"},
}
REVIEWS = [
    {"competitor_id":"comp_dd","platform":"g2","rating":4.3,"count":2450},
    {"competitor_id":"comp_nr","platform":"g2","rating":4.1,"count":890},
    {"competitor_id":"comp_sp","platform":"g2","rating":3.9,"count":1200},
]

@app.get("/")
def root():
    return {"status":"ok","service":"competitive-analysis-api","version":"1.0.0"}

@app.get("/competitors")
def list_competitors(category: Optional[str]=Query(None)):
    comps=list(COMPETITORS.values())
    if category: comps=[c for c in comps if category.lower() in c["category"].lower()]
    return {"count":len(comps),"competitors":comps}

@app.get("/competitors/{competitor_id}")
def get_competitor(competitor_id:str):
    c=COMPETITORS.get(competitor_id)
    if not c: raise HTTPException(404,f"Not found: {competitor_id}")
    reviews=[r for r in REVIEWS if r["competitor_id"]==competitor_id]
    return {"competitor":c,"reviews":reviews}

@app.get("/leaderboard")
def leaderboard():
    ranked=sorted(REVIEWS,key=lambda x:x["rating"],reverse=True)
    return {"leaderboard":[{"rank":i+1,"name":COMPETITORS.get(r["competitor_id"],{}).get("name"),"rating":r["rating"],"reviews":r["count"]} for i,r in enumerate(ranked)]}

@app.get("/summary")
def summary():
    avg=sum(r["rating"] for r in REVIEWS)/len(REVIEWS)
    return {"total_competitors":len(COMPETITORS),"avg_rating":round(avg,2),"total_reviews":sum(r["count"] for r in REVIEWS)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
